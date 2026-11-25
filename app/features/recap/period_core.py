"""A period of days (D-103): read at once, summarised, filled day by day and sent by rule.

Built on the day (`recap_core`): each day keeps its own facts, drafts and Kimai entries. Weekends and
days off are read and shown, never filled.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from app.core.utils.actor import current_actor
from app.features.recap import facts_core, recap_core
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
        except RecapError as exc:
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
        except (RecapError, ValueError) as exc:
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
            kept = by_repo.setdefault(repo["name"], {"repo": repo["repo"], "items": [], "commits": []})
            kept["items"] += repo["items"]
            kept["commits"] += [{**c, "day": row["day"]} for c in repo["commits"]]
    for kept in sorted(by_repo.values(), key=lambda r: -len(r["commits"])):
        lines += ["", f"## {kept['repo']}"]
        for item in kept["items"]:
            lines.append(f"- {KINDS[item['kind']]}: [#{item['number']}]({item['url']}) {item['title']}")
        for commit in kept["commits"]:
            branch = f" ({commit['branch']})" if commit["branch"] else ""
            lines.append(f"- {date.fromisoformat(commit['day']):%d %b} {linked(commit)}{branch}")
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
        "rules": sorted(rules.values(), key=lambda r: r["target"]),
        "summary": write_summary(first, last, [r for r in rows if r["read"]]),
    }
