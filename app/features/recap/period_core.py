"""A period of days (D-103): read at once, summarised, filled day by day and sent by rule.

Built on the day (`recap_core`): each day keeps its own facts, drafts and Kimai entries. Weekends and
days off are read and shown, never filled.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from app.core.utils.actor import current_actor
from app.core.utils.settings import get_setting
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


def propose_period(first: date, last: date) -> dict[str, list[str]]:
    """Drafts for each working day with work and no entry yet; why the other days were left."""
    made: list[str] = []
    left: list[str] = []
    for day in days(first, last):
        found = recap_core.get_day(day)
        if recap_core.day_off(day) or found is None or recap_core.entries(day):
            continue
        try:
            recap_core.propose(day)
        except (RecapError, kimai.KimaiError) as exc:
            left.append(f"{day:%a %d %b}: {exc}")
        else:
            made.append(day.isoformat())
    return {"made": made, "left": left}


def send_period(first: date, last: date, rule_ids: list[uuid.UUID]) -> int:
    """Send the drafts of the period whose rule is chosen, day by day; the number sent. A day that
    fails stops the rest; the days before it stay sent."""
    if current_actor() != "user":
        raise RecapError("Only the owner sends time entries.")
    chosen = set(rule_ids)
    sent = 0
    for day in days(first, last):
        drafts = [e.id for e in recap_core.entries(day) if e.sent_at is None and e.target_id in chosen]
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


def describe_period(first: date, last: date) -> dict[str, Any]:
    rows, rules = [], {}
    for day in days(first, last):
        found = recap_core.get_day(day)
        listed = [recap_core.describe_entry(e) for e in recap_core.entries(day)]
        facts = found.facts if found and found.read_at else None
        for entry in listed:
            names = {k: entry[k] for k in ("target", "project", "activity")}
            rule = rules.setdefault(
                entry["target_id"], {"id": entry["target_id"], **names, "draft": 0, "sent": 0}
            )
            rule["sent" if entry["sent"] else "draft"] += entry["minutes"]
        rows.append(
            {
                "day": day.isoformat(),
                "off": recap_core.day_off(day),
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
    there = []
    if kimai.configured():
        for start in span[::7]:
            there += kimai.entries(start, min(start + timedelta(days=6), span[-1]))
    cells = []
    for row in found["days"]:
        day = date.fromisoformat(row["day"])
        mine = [e for e in row["entries"] if not e["sent"]]
        blocks = [
            _block(k["begin"], k["end"], f"{k['project_name']}, {k['activity_name']}")
            for k in there
            if k["begin"].date() == day
        ]
        for entry in mine:
            begin = datetime.fromisoformat(f"{row['day']}T{entry['begin']}")
            end = begin + timedelta(minutes=entry["minutes"])
            blocks.append(
                {
                    **_block(begin, end, entry["target"]),
                    "rule": entry["target_id"],
                    "description": entry["description"],
                }
            )
        blocks.sort(key=lambda b: b["begin"])
        cells.append(
            {
                "day": row["day"],
                "off": row["off"],
                "blocks": blocks,
                "minutes": sum(b["minutes"] for b in blocks),
                "problems": _problems(row, mine, blocks),
            }
        )
    padded = [None] * (span[0].isoweekday() - 1) + cells
    padded += [None] * (-len(padded) % 7)
    return [padded[n : n + 7] for n in range(0, len(padded), 7)]


def _block(begin: datetime, end: datetime | None, name: str) -> dict[str, Any]:
    """One entry of the preview; `rule` is empty for what Kimai holds."""
    return {
        "begin": f"{begin:%H:%M}",
        "end": f"{end:%H:%M}" if end else "",
        "minutes": round((end - begin).total_seconds() / 60) if end else 0,
        "name": name,
        "rule": "",
        "description": "",
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
