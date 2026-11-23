"""The day summary and its time entries (D-078). Drafts stay in Cairn: only `send`, called by the
owner's own click, reaches Kimai, and it never writes over what is already there."""

from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timedelta
from textwrap import shorten
from typing import Any

from sqlalchemy import String, cast, func, or_, select

from app.core.db_class.base import utcnow
from app.core.db_class.recap import DayEntry, WorkDay, WorkTarget
from app.core.extensions import db
from app.core.schema.recap import EntryInput, EntryUpdate, RulesInput, TargetInput
from app.core.utils.actor import current_actor
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.recap import facts_core, kimai

STEP = 15  # minutes
SUBJECT = 120  # characters of a commit named in a description
SUBJECTS = 6  # commits named for each branch in a description
KINDS = {"pr_opened": "PR opened", "pr_merged": "PR merged", "issue_opened": "Issue opened"}
_sending = threading.Lock()


class RecapError(ValueError):
    pass


# -- where the work goes ------------------------------------------------------------------------


def targets(q: str = "") -> list[WorkTarget]:
    query = select(WorkTarget).where(WorkTarget.deleted_at.is_(None))
    if q.strip():
        like = f"%{q.strip().lower()}%"
        columns = (WorkTarget.label, WorkTarget.project_label, WorkTarget.activity_label, WorkTarget.guidance)
        in_repos = func.lower(cast(WorkTarget.repos, String)).like(like)
        query = query.where(or_(in_repos, *(func.lower(c).like(like) for c in columns)))
    return list(db.session.scalars(query.order_by(WorkTarget.label, WorkTarget.created_at)))


def get_target(target_id: uuid.UUID) -> WorkTarget:
    found = db.session.get(WorkTarget, target_id)
    if found is None or found.is_deleted:
        raise RecapError("This rule does not exist.")
    return found


def save_target(data: TargetInput, target_id: uuid.UUID | None = None) -> WorkTarget:
    project, activity = kimai.labels(data.kimai_project, data.kimai_activity)
    values = {**data.model_dump(), "project_label": project[:160], "activity_label": activity[:160]}
    with batch():
        target = get_target(target_id) if target_id else WorkTarget()
        diff = {k: [getattr(target, k), v] for k, v in values.items() if getattr(target, k) != v}
        for name, value in values.items():
            setattr(target, name, value)
        db.session.add(target)
        db.session.flush()
        log_action(
            "work_target.update" if target_id else "work_target.create",
            target_type="work_target",
            target_id=target.id,
            diff=diff,
        )
    return target


def delete_target(target_id: uuid.UUID) -> None:
    target = get_target(target_id)
    waiting = db.session.scalar(
        select(DayEntry.id).where(
            DayEntry.target_id == target.id, DayEntry.deleted_at.is_(None), DayEntry.sent_at.is_(None)
        )
    )
    if waiting:
        raise RecapError("Drafts still use this rule: move or remove them first.")
    with batch():
        target.deleted_at = utcnow()
        log_action("work_target.delete", target_type="work_target", target_id=target.id)


def _undo_delete_target(row) -> None:
    target = db.session.get(WorkTarget, uuid.UUID(row.target_id))
    if target is not None:
        target.deleted_at = None


register_undo("work_target.delete", _undo_delete_target)


def export_rules() -> dict[str, Any]:
    """The rules as a file: to keep, or to give to someone who uses the same Kimai."""
    return {"rules": [{n: getattr(t, n) for n in TargetInput.model_fields} for t in targets()]}


def import_rules(data: RulesInput) -> list[WorkTarget]:
    """Add the rules of a file, all or none; one with a known label replaces it."""
    known = {t.label.lower(): t.id for t in targets()}
    with batch():
        return [save_target(rule, known.get(rule.label.lower())) for rule in data.rules]


def target_for(repo: str, words: str, among: list[WorkTarget]) -> WorkTarget | None:
    """Where work goes: the repository's rule with a word of it, a rule of words alone, then the
    repository's default rule, then its only one or its first."""
    words = words.lower()
    here = [t for t in among if repo in t.repos]
    anywhere = [t for t in among if not t.repos]
    for target in (*here, *anywhere):
        if any(keyword in words for keyword in target.keywords):
            return target
    return next((t for t in here if t.is_default), here[0] if here else None)


# -- the day ------------------------------------------------------------------------------------


def get_day(day: date) -> WorkDay | None:
    return db.session.scalar(select(WorkDay).where(WorkDay.day == day))


def _checked(day: date) -> None:
    if day > date.today():
        raise RecapError("This day has not come yet.")


def read_day(day: date) -> WorkDay:
    """Read what was done; the summary follows unless the owner wrote in it."""
    _checked(day)
    facts = facts_core.gather(day)
    with batch():
        found = get_day(day) or WorkDay(day=day, summary_edited=False, summary_md="")
        found.facts, found.read_at = facts, utcnow()
        if not found.summary_edited:
            found.summary_md = write_summary(day, facts)
        db.session.add(found)
        db.session.flush()
        log_action("work_day.read", target_type="work_day", target_id=found.id, meta={"day": day.isoformat()})
    return found


def write_summary(day: date, facts: dict[str, Any]) -> str:
    lines = [f"# {day:%A %d %B %Y}"]
    for row in facts["repos"]:
        lines += ["", f"## {row['repo']}"]
        for task in row["tasks"]:
            lines.append(f"- Task done: {task['title']}")
        for item in row["items"]:
            lines.append(f"- {KINDS[item['kind']]}: [#{item['number']}]({item['url']}) {item['title']}")
        for branch, commits in _by_branch(row["commits"]).items():
            lines.append(f"- `{branch or 'default branch'}`: {_count(len(commits), 'commit')}")
            lines += [f"  - {commit['subject']}" for commit in commits]
        if row["asked"]:
            lines.append(f"- {_count(row['asked'], 'request')} to Claude")
    if not facts["repos"]:
        lines += ["", "Nothing found for this day."]
    return "\n".join(lines) + "\n"


def save_summary(day: date, text: str) -> WorkDay:
    with batch():
        found = get_day(day)
        if found is None:
            raise RecapError("Read the day first.")
        old, found.summary_md, found.summary_edited = found.summary_md, text, True
        log_action(
            "work_day.summary", target_type="work_day", target_id=found.id, diff={"summary_md": [old, text]}
        )
    return found


def _count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _by_branch(commits: list[dict]) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    for commit in commits:
        found.setdefault(commit["branch"], []).append(commit)
    return found


# -- time entries -------------------------------------------------------------------------------


def entries(day: date) -> list[DayEntry]:
    return list(
        db.session.scalars(
            select(DayEntry)
            .where(DayEntry.day == day, DayEntry.deleted_at.is_(None))
            .order_by(DayEntry.begin, DayEntry.created_at)
        )
    )


def get_entry(entry_id: uuid.UUID) -> DayEntry:
    found = db.session.get(DayEntry, entry_id)
    if found is None or found.is_deleted:
        raise RecapError("This time entry does not exist.")
    return found


def _minutes(clock: str) -> int:
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def _fits(begin: str, minutes: int) -> None:
    if _minutes(begin) + minutes > 24 * 60 - 1:
        raise RecapError("This entry would end the next day.")


def share(weights: list[int], total: int) -> list[int]:
    """`total` minutes by weight, in steps, at least one step each; the biggest takes the rest."""
    if not weights:
        return []
    whole = sum(weights)
    parts = [max(STEP, round(total * w / whole / STEP) * STEP) for w in weights]
    biggest = max(range(len(parts)), key=lambda i: parts[i])
    parts[biggest] = max(STEP, parts[biggest] + total - sum(parts))
    return parts


def describe_work(about: str, parts: list[dict[str, Any]]) -> str:
    """The description of an entry: what the work is, then each repository's branches and links."""
    lines = [about] if about else []
    for part in parts:
        for item in part["items"]:
            lines.append(
                f"{KINDS[item['kind']]} {part['name']}#{item['number']}: {item['title']} - {item['url']}"
            )
        for branch, commits in _by_branch(part["commits"]).items():
            subjects = list(dict.fromkeys(shorten(c["subject"], SUBJECT, placeholder="…") for c in commits))
            more = f"; and {len(subjects) - SUBJECTS} more" if len(subjects) > SUBJECTS else ""
            where = f"{part['name']} ({branch})" if branch else part["name"]
            last = f" - {commits[-1]['url']}" if commits[-1]["url"] else ""
            lines.append(f"{where}: {'; '.join(subjects[:SUBJECTS])}{more}{last}")
        lines += [f"Done: {task['title']}" for task in part["tasks"]]
    return "\n".join(lines)[:4000]


def plan(
    facts: dict[str, Any], among: list[WorkTarget]
) -> tuple[list[tuple[WorkTarget, int, str]], dict[str, int]]:
    """(rule, weight, description) for the day, and the weight of each repository with work no rule
    takes. The weight is the number of half hours with something done; ignored repositories have none."""
    ignored = {name.lower() for name in get_setting("recap.ignored")}
    grouped: dict[uuid.UUID, dict[str, Any]] = {}
    lost: dict[str, int] = {}

    def put(row: dict[str, Any], words: str, slots: set[str]) -> dict[str, Any] | None:
        target = target_for(row["name"], words, among)
        if target is None:
            lost[row["name"]] = max(1, len(row["slots"]))
            return None
        group = grouped.setdefault(target.id, {"target": target, "parts": {}, "slots": set()})
        group["slots"] |= slots
        return group["parts"].setdefault(
            row["name"], {"name": row["name"], "commits": [], "items": [], "tasks": []}
        )

    for row in facts["repos"]:
        if row["name"] in ignored:
            continue
        for kind in ("commits", "items", "tasks"):
            for value in row[kind]:
                words = " ".join((value.get("branch", ""), value.get("subject", ""), value.get("title", "")))
                slots = {facts_core.slot(datetime.fromisoformat(value["at"]))} if kind == "commits" else set()
                part = put(row, words, slots)
                if part is not None:
                    part[kind].append(value)
        # What is not a commit says nothing of the rule: it goes with most of the day's commits.
        worked = [g for g in grouped.values() if g["parts"].get(row["name"], {}).get("commits")]
        if worked:
            max(worked, key=lambda g: len(g["parts"][row["name"]]["commits"]))["slots"] |= set(row["slots"])
        else:
            put(row, "", set(row["slots"]))
    found = [
        (g["target"], max(1, len(g["slots"])), describe_work(g["target"].about, list(g["parts"].values())))
        for g in grouped.values()
    ]
    found.sort(key=lambda item: -item[1])
    return found, lost


def propose(day: date) -> list[DayEntry]:
    """Drafts for the day from its facts, in the time not taken in Kimai. Only on a day with no draft."""
    _checked(day)
    found = get_day(day)
    if found is None or found.read_at is None:
        raise RecapError("Read the day first.")
    if entries(day):
        raise RecapError("This day already has time entries: remove them to propose again.")
    planned, _ = plan(found.facts, targets())
    if not planned:
        raise RecapError("No rule takes the work of this day yet.")
    taken = kimai.entries(day) if kimai.configured() else []
    total = get_setting("recap.day_minutes") - sum(row["minutes"] for row in taken)
    if total < STEP:
        raise RecapError("Kimai already holds a full day.")
    clock = _minutes(get_setting("recap.day_start"))
    clock = max([clock, *(_minutes(f"{row['end']:%H:%M}") for row in taken if row["end"])])
    # The owner's rule: the whole day goes to the projects worked on, in equal parts, however long
    # each one took; work no rule places takes nothing (D-078).
    parts = share([1] * len(planned), total)
    made = []
    with batch():
        for (target, _, text), minutes in zip(planned, parts, strict=True):
            if clock + minutes > 24 * 60 - 1:
                raise RecapError(
                    "The day is too short for its entries after what Kimai holds: add them yourself."
                )
            begin = f"{clock // 60:02d}:{clock % 60:02d}"
            made.append(
                _make(day, EntryInput(target_id=target.id, begin=begin, minutes=minutes, description=text))
            )
            clock += minutes
    return made


def _make(day: date, data: EntryInput) -> DayEntry:
    entry = DayEntry(day=day, **data.model_dump())
    db.session.add(entry)
    db.session.flush()
    log_action("day_entry.create", target_type="day_entry", target_id=entry.id, diff=_diff({}, entry))
    return entry


def _diff(before: dict[str, Any], entry: DayEntry) -> dict[str, Any]:
    now = {
        "begin": entry.begin,
        "minutes": entry.minutes,
        "target_id": str(entry.target_id),
        "description": entry.description,
    }
    return {name: [before.get(name), value] for name, value in now.items() if before.get(name) != value}


def add_entry(day: date, data: EntryInput) -> DayEntry:
    _checked(day)
    get_target(data.target_id)
    _fits(data.begin, data.minutes)
    with batch():
        return _make(day, data)


def update_entry(entry_id: uuid.UUID, data: EntryUpdate) -> DayEntry:
    entry = get_entry(entry_id)
    if entry.sent_at is not None:
        raise RecapError("This entry is in Kimai: change it there.")
    if data.target_id is not None:
        get_target(data.target_id)
    values = data.model_dump(exclude_none=True)
    _fits(values.get("begin", entry.begin), values.get("minutes", entry.minutes))
    before = {name: pair[1] for name, pair in _diff({}, entry).items()}
    with batch():
        for name, value in values.items():
            setattr(entry, name, value)
        log_action("day_entry.update", target_type="day_entry", target_id=entry.id, diff=_diff(before, entry))
    return entry


def delete_entry(entry_id: uuid.UUID) -> DayEntry:
    """Take the line off Cairn; an entry already in Kimai stays in Kimai."""
    entry = get_entry(entry_id)
    if entry.sent_at is not None:
        raise RecapError("This entry is in Kimai: change it there.")
    with batch():
        entry.deleted_at = utcnow()
        log_action("day_entry.delete", target_type="day_entry", target_id=entry.id)
    return entry


def _undo_delete(row) -> None:
    entry = db.session.get(DayEntry, uuid.UUID(row.target_id))
    if entry is not None:
        entry.deleted_at = None


register_undo("day_entry.delete", _undo_delete)


# -- Kimai --------------------------------------------------------------------------------------


def _begin(entry: DayEntry) -> datetime:
    return datetime.combine(entry.day, datetime.strptime(entry.begin, "%H:%M").time())


def send(day: date, entry_ids: list[uuid.UUID]) -> list[DayEntry]:
    """Create the chosen drafts in Kimai. The owner's alone: no Claude, module or job may."""
    if current_actor() != "user":
        raise RecapError("Only the owner sends time entries.")
    _checked(day)
    if not _sending.acquire(blocking=False):
        raise RecapError("Entries are being sent already.")
    try:
        chosen = [get_entry(entry_id) for entry_id in dict.fromkeys(entry_ids)]
        if any(entry.day != day for entry in chosen):
            raise RecapError("An entry is not of this day.")
        chosen = sorted((e for e in chosen if e.sent_at is None), key=lambda e: e.begin)
        if not chosen:
            raise RecapError("These entries are in Kimai already.")
        if any(not entry.description.strip() for entry in chosen):
            raise RecapError("Write a description for each entry.")
        there = kimai.entries(day)
        free = [entry for entry in chosen if _same(entry, there) is None]
        _no_overlap(free, there)
        for entry in chosen:
            _send_one(entry, _same(entry, there))
    finally:
        _sending.release()
    return chosen


def _same(entry: DayEntry, there: list[dict[str, Any]]) -> int | None:
    """This very entry, sent before and whose answer was lost."""
    target, begin = get_target(entry.target_id), _begin(entry)
    for row in there:
        if (row["begin"], row["minutes"], row["project"], row["activity"]) == (
            begin,
            entry.minutes,
            target.kimai_project,
            target.kimai_activity,
        ):
            return row["id"]
    return None


def _no_overlap(chosen: list[DayEntry], there: list[dict[str, Any]]) -> None:
    taken = [
        (row["begin"], row["end"] or row["begin"] + timedelta(days=1), row["project_name"]) for row in there
    ]
    for entry in chosen:
        begin = _begin(entry)
        end = begin + timedelta(minutes=entry.minutes)
        for other, until, name in taken:
            if begin < until and other < end:
                raise RecapError(
                    f"Nothing was sent: {entry.begin} overlaps {name} ({other:%H:%M} to {until:%H:%M})."
                )
        taken.append((begin, end, get_target(entry.target_id).label))


def _send_one(entry: DayEntry, known: int | None) -> None:
    target = get_target(entry.target_id)
    kimai_id = known or kimai.create(
        _begin(entry),
        entry.minutes,
        target.kimai_project,
        target.kimai_activity,
        entry.description,
        target.tags,
    )
    with batch():  # one by one: what reached Kimai is recorded even if the next one fails
        entry.kimai_id, entry.sent_at = kimai_id, utcnow()
        log_action(
            "day_entry.send",
            target_type="day_entry",
            target_id=entry.id,
            meta={"kimai_id": kimai_id, "minutes": entry.minutes, "found": known is not None},
        )


# -- for the pages and the API ------------------------------------------------------------------


def describe_entry(entry: DayEntry) -> dict[str, Any]:
    target = db.session.get(WorkTarget, entry.target_id)
    return {
        "id": str(entry.id),
        "day": entry.day.isoformat(),
        "begin": entry.begin,
        "minutes": entry.minutes,
        "target_id": str(entry.target_id),
        "target": target.label,
        "project": target.project_label,
        "activity": target.activity_label,
        "description": entry.description,
        "sent": entry.sent_at is not None,
        "kimai_id": entry.kimai_id,
    }


def describe_target(target: WorkTarget) -> dict[str, Any]:
    names = (
        "label", "repos", "keywords", "is_default", "guidance", "about", "tags",
        "kimai_project", "project_label", "kimai_activity", "activity_label",
    )  # fmt: skip
    return {"id": str(target.id), **{name: getattr(target, name) for name in names}}


def describe_day(day: date) -> dict[str, Any]:
    found = get_day(day)
    facts = found.facts if found else None
    return {
        "day": day.isoformat(),
        "read_at": found.read_at.isoformat() if found and found.read_at else None,
        "facts": facts,
        "summary": found.summary_md if found else "",
        "unplaced": list(plan(facts, targets())[1]) if facts else [],
        "entries": [describe_entry(entry) for entry in entries(day)],
    }
