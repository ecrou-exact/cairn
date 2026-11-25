"""A period of days (D-103): read at once, summarised, filled day by day and sent by rule.

Built on the day (`recap_core`): each day keeps its own facts, drafts and Kimai entries. Weekends and
days off are read and shown, never filled.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.planning import Project
from app.core.db_class.recap import DayEntry, WorkTarget
from app.core.extensions import db
from app.core.schema.recap import EntryUpdate
from app.core.utils.actor import current_actor
from app.core.utils.history import batch
from app.core.utils.settings import get_setting, set_setting
from app.features.projects import place_core
from app.features.recap import facts_core, kimai, recap_core
from app.features.recap.recap_core import KINDS, RecapError, linked

MAX_DAYS = 62


def days(first: date, last: date) -> list[date]:
    if last < first:
        raise RecapError("The period ends before it starts.")
    if last > date.today():
        raise RecapError("The period ends after today.")
    if (last - first).days >= MAX_DAYS:
        raise RecapError(f"A period is {MAX_DAYS} days at most.")
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def read_period(first: date, last: date) -> int:
    """Read git and GitHub once for the period and keep each day's facts; the number of days read."""
    span = days(first, last)
    for day, facts in facts_core.gather_span(span[0], span[-1]).items():
        recap_core.store_day(day, facts)
    return len(span)


def choices() -> list[dict[str, Any]]:
    """Cairn's projects with a repository: its names, the rules that take it, whether it is looked at
    (nothing chosen yet: those with a rule)."""
    chosen, rules = set(get_setting("recap.repos")), recap_core.targets()
    found = []
    query = select(Project).where(Project.deleted_at.is_(None)).order_by(Project.name)
    for project in db.session.scalars(query):
        names = _repos_of(project)
        taken = [t.label for t in rules if names & set(t.repos)]
        if names:
            on = bool(names & chosen) if chosen else bool(taken)
            row = {"slug": project.slug, "name": project.name, "color": project.color}
            found.append({**row, "repos": sorted(names), "rules": taken, "chosen": on and bool(taken)})
    return found


def _repos_of(project: Project) -> set[str]:
    names = {facts_core.short(project.github_repo)} if project.github_repo else set()
    git = place_core.git_of(Path(project.local_path).expanduser()) if project.local_path else None
    if git:
        names.add(facts_core.short(place_core.origin(git[2]) or git[0].name))
    return names


def try_period(first: date, last: date, slugs: list[str]) -> int:
    """Look at these projects only and read the period; the number of days read. No entry is made."""
    span = days(first, last)
    known = {row["slug"]: row for row in choices() if row["rules"]}
    if unknown := [slug for slug in slugs if slug not in known]:
        raise RecapError(f"No such project with a rule: {', '.join(unknown)}.")
    set_setting("recap.repos", sorted({name for slug in slugs for name in known[slug]["repos"]}))
    return read_period(span[0], span[-1])


def propose_period(first: date, last: date) -> dict[str, list[str]]:
    """Drafts for each working day with work and no entry yet; a day that has entries is brought up to
    its facts (D-105). Why the other days were left."""
    made: list[str] = []
    updated: list[str] = []
    left: list[str] = []
    for day in days(first, last):
        found = recap_core.get_day(day)
        if recap_core.day_off(day) or found is None:
            continue
        there = bool(recap_core.entries(day))
        try:
            changed = recap_core.refresh(day) if there else recap_core.propose(day)
        except (RecapError, kimai.KimaiError) as exc:
            left.append(f"{day:%a %d %b}: {exc}")
        else:
            if changed:
                (updated if there else made).append(day.isoformat())
    return {"made": made, "updated": updated, "left": left}


def edit_trial(day: date, target_id: uuid.UUID, data: EntryUpdate) -> DayEntry:
    """Change an entry of the try: the day's drafts are made, then this one takes the owner's words."""
    with batch():
        made = recap_core.propose(day)
        entry = next((e for e in made if e.target_id == target_id), None)
        if entry is None:
            raise RecapError("The try has changed: look at it again.")
        return recap_core.update_entry(entry.id, data)


def send_period(first: date, last: date, rule_ids: list[uuid.UUID]) -> int:
    """Send the drafts of the period whose rule is chosen, day by day; the number sent. A day that
    fails stops the rest; the days before it stay sent."""
    if current_actor() != "user":
        raise RecapError("Only the owner sends time entries.")
    chosen = set(rule_ids)
    sent = 0
    for day in days(first, last):
        drafts = [e.id for e in recap_core.entries(day) if recap_core.waiting(e) and e.target_id in chosen]
        if not drafts:
            continue
        try:
            sent += len(recap_core.send(day, drafts))
        except (RecapError, kimai.KimaiError) as exc:
            raise RecapError(f"{day:%a %d %b}: {exc} ({sent} sent before.)") from exc
    if not sent:
        raise RecapError("No draft of these rules in the period.")
    return sent


# -- the summary --------------------------------------------------------------------------------


def write_summary(first: date, last: date, rows: list[dict[str, Any]]) -> str:
    """The work of the period by repository: pull requests, issues, then commits with their links."""
    lines = [f"# {first:%d %B %Y} to {last:%d %B %Y}"]
    by_repo: dict[str, dict[str, Any]] = {}
    for row in rows:
        for repo in row["facts"]["repos"]:
            kept = by_repo.setdefault(
                repo["name"], {"repo": repo["repo"], "items": [], "days": [], "count": 0}
            )
            kept["items"] += repo["items"]
            named, more = recap_core.brief(repo["commits"])
            kept["days"].append((date.fromisoformat(row["day"]), named, more))
            kept["count"] += len(repo["commits"])
    for kept in sorted(by_repo.values(), key=lambda r: -r["count"]):
        lines += ["", f"## {kept['repo']}"]
        for item in kept["items"]:
            lines.append(f"- {KINDS[item['kind']]}: [#{item['number']}]({item['url']}) {item['title']}")
        for day, named, more in kept["days"]:
            for commit in named:
                branch = f" ({commit['branch']})" if commit["branch"] else ""
                lines.append(f"- {day:%d %b} {linked(commit)}{branch}")
            if more:
                lines.append(f"- {day:%d %b} and {more} more commit{'' if more == 1 else 's'}")
    if not by_repo:
        lines += ["", "Nothing found for this period."]
    return "\n".join(lines) + "\n"


def _rule_row(target_id: str) -> dict[str, Any]:
    """A rule with the minutes of its entries, and how many entries in Kimai are to be updated."""
    target = db.session.get(WorkTarget, uuid.UUID(target_id))
    names = {"target": target.label, "project": target.project_label, "activity": target.activity_label}
    return {"id": target_id, **names, "draft": 0, "sent": 0, "trial": 0, "update": 0}


def describe_period(first: date, last: date) -> dict[str, Any]:
    rows, rules = [], {}
    for day in days(first, last):
        found = recap_core.get_day(day)
        listed = [recap_core.describe_entry(e) for e in recap_core.entries(day)]
        off = recap_core.day_off(day)
        facts = recap_core.visible(found.facts) if found and found.read_at else None
        if facts and off:  # a day off is not looked at (D-104)
            facts = {**facts, "repos": []}
        for entry in listed:
            rule = rules.setdefault(entry["target_id"], _rule_row(entry["target_id"]))
            rule["update"] += entry["update"]
            rule["sent" if entry["sent"] else "draft"] += entry["minutes"]
        rows.append(
            {
                "day": day.isoformat(),
                "off": off,
                "read": facts is not None,
                "facts": facts or {"repos": []},
                "unplaced": list(recap_core.plan(facts, recap_core.targets())[1]) if facts else [],
                "entries": listed,
            }
        )
    return {
        "first": first.isoformat(),
        "last": last.isoformat(),
        "days": rows,
        "github": all(row["facts"].get("github", True) for row in rows),
        "rules": sorted(rules.values(), key=lambda r: r["target"]),
        "summary": write_summary(first, last, [r for r in rows if r["read"]]),
    }


# -- the preview --------------------------------------------------------------------------------


def preview(found: dict[str, Any]) -> list[list[dict[str, Any] | None]]:
    """The period (from `describe_period`) as weeks from Monday, None outside it: each day's drafts
    beside what Kimai holds, and what to look at before sending."""
    span = days(date.fromisoformat(found["first"]), date.fromisoformat(found["last"]))
    there: list[dict[str, Any]] = []
    customers: dict[int, str] = {}
    totals = {rule["id"]: rule for rule in found["rules"]}
    if kimai.configured():
        customers = {p["id"]: p["customer"] for p in kimai.catalog()}
    if kimai.configured():
        for start in span[::7]:
            there += kimai.entries(start, min(start + timedelta(days=6), span[-1]))
    cells = []
    for row in found["days"]:
        day = date.fromisoformat(row["day"])
        held = [k for k in there if k["begin"].date() == day]
        mine, trial, texts, said = _trial(row, held)
        for entry in trial:
            rule = totals.setdefault(entry["target_id"], _rule_row(entry["target_id"]))
            rule["trial"] += entry["minutes"]
        for entry_id in texts:
            entry = next(e for e in row["entries"] if e["id"] == entry_id)
            if entry["sent"] and not entry["update"]:
                totals[entry["target_id"]]["update"] += 1
        sent = {e["kimai_id"]: e for e in row["entries"] if e["sent"]}
        blocks = []
        for k in held:
            own = sent.get(k["id"])
            new = texts.get(own["id"]) or (own["description"] if own["update"] else None) if own else None
            more = {
                "customer": customers.get(k["project"], ""),
                "project": k["project_name"],
                "project_id": k["project"],
                "activity": k["activity_name"],
                "activity_id": k["activity"],
                "description": new or k["description"],
                "tags": k.get("tags", []),
                "state": "update" if new else "kimai",
            }
            blocks.append(_block(row["day"], k["begin"], k["end"], more))
        for entry in mine + trial:
            begin = datetime.fromisoformat(f"{row['day']}T{entry['begin']}")
            more = {
                "id": entry.get("id", ""),
                "customer": customers.get(entry["kimai_project"], ""),
                "project": entry["project"],
                "project_id": entry["kimai_project"],
                "activity": entry["activity"],
                "activity_id": entry["kimai_activity"],
                "tags": entry["tags"],
                "rule": entry["target_id"],
                "state": "draft" if "id" in entry else "trial",
                "description": texts.get(entry.get("id"), entry["description"]),
            }
            blocks.append(_block(row["day"], begin, begin + timedelta(minutes=entry["minutes"]), more))
        blocks.sort(key=lambda b: b["begin"])
        cells.append(
            {
                "day": row["day"],
                "off": row["off"],
                "blocks": blocks,
                "minutes": sum(b["minutes"] for b in blocks),
                "problems": said + _problems(row, mine + trial, blocks),
            }
        )
    found["rules"] = sorted(totals.values(), key=lambda r: r["target"])
    padded = [None] * (span[0].isoweekday() - 1) + cells
    padded += [None] * (-len(padded) % 7)
    return [padded[n : n + 7] for n in range(0, len(padded), 7)]


def _trial(
    row: dict[str, Any], taken: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str], list[str]]:
    """For a day: its drafts kept, what would be proposed, the new words of entries, what to say."""
    mine = [e for e in row["entries"] if not e["sent"]]
    if not row["read"] or row["off"] or not row["facts"]["repos"]:
        return mine, [], {}, []
    texts, again, missing = recap_core.refreshes(date.fromisoformat(row["day"]), row["facts"])
    said = [f"no entry for {name}" for name in missing]
    if row["entries"] and not again:
        return mine, [], {str(entry_id): text for entry_id, text in texts.items()}, said
    try:
        wanted = recap_core.proposal(row["facts"], taken)
    except RecapError as exc:
        return mine, [], {}, [str(exc).rstrip(".").lower()]
    trial = []
    for data in wanted:
        entry = DayEntry(**data.model_dump())
        trial.append({**data.model_dump(), "target_id": str(data.target_id), **recap_core.placed(entry)})
    return [], trial, {}, []


def _block(day: str, begin: datetime, end: datetime | None, more: dict[str, Any]) -> dict[str, Any]:
    """One entry of the preview. `state`: what Kimai holds ("kimai"), holds with words to update
    ("update"), a draft of Cairn ("draft"), an attempt ("trial"). `rule` is empty for the first two."""
    return {
        "id": "",
        "day": day,
        "begin": f"{begin:%H:%M}",
        "end": f"{end:%H:%M}" if end else "",
        "minutes": round((end - begin).total_seconds() / 60) if end else 0,
        "rule": "",
        **more,
    }


def _problems(row: dict[str, Any], drafts: list[dict[str, Any]], blocks: list[dict[str, Any]]) -> list[str]:
    said = []
    until, held = "", False  # two entries of Kimai may overlap: only a draft can be changed here
    for block in blocks:
        if block["begin"] < until and (block["rule"] or held):
            said.append("entries overlap")
            break
        if (block["end"] or "24:00") > until:
            until, held = block["end"] or "24:00", bool(block["rule"])
    total, length = sum(b["minutes"] for b in blocks), get_setting("recap.day_minutes")
    if drafts and row["off"]:
        said.append(f"drafts on a {row['off']}")
    if drafts and total != length:
        said.append("more than a day" if total > length else "less than a day")
    if any(not e["description"].strip() for e in drafts):
        said.append("no description")
    if not row["off"]:
        if not row["read"]:
            said.append("not read")
        elif row["facts"]["repos"] and not blocks:
            said.append("work without time")
        elif not row["facts"]["repos"] and not blocks:
            said.append("no work found")
    return said
