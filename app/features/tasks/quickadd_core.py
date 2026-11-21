"""Quick add in plain words (PROJECT_BRIEF.md §5):

    fix login bug for rulezet by friday #bug !high ~2h @claude

| Written                             | Understood as                                        |
|-------------------------------------|------------------------------------------------------|
| `for <project>` / `+<project>`      | project, by slug or name (left in the title if none) |
| `by <date>` / `due <date>`          | due date; `!hard` makes it a hard deadline           |
| `on <date>`, or a bare `today`…     | the "do on" date                                     |
| `#word`                             | a task type when one has that key, else a tag        |
| `!critical !high !medium !low`, `!1`–`!4` | priority                                       |
| `~2h`, `~30m`, `~1.5h`, `~1d`       | estimate (1 d = 8 h)                                 |
| `@me`, `@claude`, `@name`           | assignee                                             |

Dates: today, tomorrow, weekday names (English or French, the next one to come),
`next week`, `in 3 days` / `in 2 weeks`, `end of week`, `end of month`, `2026-12-01`,
`1/12`, `01/12/2026` (day first).
"""

from __future__ import annotations

import calendar
import difflib
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_, select

from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.planning import TaskCreate
from app.features.tasks import recurrence_core, tasks_core, workflow

WEEKDAYS = {
    **{
        name: i
        for i, name in enumerate(
            ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        )
    },
    **{name: i for i, name in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun"))},
    **{
        name: i
        for i, name in enumerate(("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"))
    },
}
PRIORITY_WORDS = {"critical": "critical", "high": "high", "medium": "medium", "low": "low", "1": "critical"}
PRIORITY_WORDS |= {"2": "high", "3": "medium", "4": "low", "crit": "critical", "urgent": "critical"}
DUE_WORDS = ("by", "due", "before", "avant")
# Recurrence: "daily", "weekly", "every 2 weeks", "chaque semaine", "tous les mois".
REPEAT_ADVERBS = {
    "daily": "day", "weekly": "week", "monthly": "month", "yearly": "year",
    "quotidien": "day", "hebdo": "week", "hebdomadaire": "week", "mensuel": "month", "annuel": "year",
}  # fmt: skip
REPEAT_UNITS = {
    "day": "day", "days": "day", "week": "week", "weeks": "week", "month": "month", "months": "month",
    "year": "year", "years": "year", "jour": "day", "jours": "day", "semaine": "week", "semaines": "week",
    "mois": "month", "an": "year", "ans": "year", "année": "year", "années": "year",
}  # fmt: skip
REPEAT_WORDS = ("every", "chaque", "toutes", "tous")
DO_WORDS = ("on", "le")
PROJECT_WORDS = ("for", "pour")
DUPLICATE_RATIO = 0.82


@dataclass
class Parsed:
    title: str = ""
    project: Project | None = None
    type: str | None = None
    tags: list[str] = field(default_factory=list)
    priority: str | None = None
    due_on: date | None = None
    do_on: date | None = None
    hard_deadline: bool = False
    estimate_hours: float | None = None
    assignee: str | None = None
    recurrence: dict[str, Any] | None = None
    understood: list[dict[str, str]] = field(default_factory=list)  # chips for the preview

    def note(self, kind: str, text: str) -> None:
        self.understood.append({"kind": kind, "text": text})


def _date(words: list[str], today: date) -> tuple[date | None, int]:
    """A date at the start of `words`, and how many words it used."""
    if not words:
        return None, 0
    first = words[0].lower().rstrip(",.")
    second = words[1].lower().rstrip(",.") if len(words) > 1 else ""
    if first in ("today", "aujourd'hui"):
        return today, 1
    if first in ("tomorrow", "tmrw", "demain"):
        return today + timedelta(days=1), 1
    if first in WEEKDAYS:
        ahead = (WEEKDAYS[first] - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead), 1
    if first == "next" and second == "week":
        return today + timedelta(days=7 - today.weekday()), 2
    if first == "end" and len(words) > 2 and second == "of":
        third = words[2].lower().rstrip(",.")
        if third == "week":
            return today + timedelta(days=(4 - today.weekday()) % 7), 3
        if third == "month":
            return today.replace(day=calendar.monthrange(today.year, today.month)[1]), 3
    if first == "in" and len(words) > 2 and second.isdigit():
        unit = words[2].lower().rstrip(",.")
        if unit.startswith("day") or unit.startswith("jour"):
            return today + timedelta(days=int(second)), 3
        if unit.startswith("week") or unit.startswith("semaine"):
            return today + timedelta(weeks=int(second)), 3
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", first):
        try:
            return date(int(m[1]), int(m[2]), int(m[3])), 1
        except ValueError:
            return None, 0
    if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", first):
        year = int(m[3]) if m[3] else today.year
        year = year + 2000 if year < 100 else year
        try:
            found = date(year, int(m[2]), int(m[1]))
        except ValueError:
            return None, 0
        if not m[3] and found < today:
            found = found.replace(year=year + 1)
        return found, 1
    return None, 0


def _repeat(word: str, rest: list[str]) -> tuple[dict[str, Any], int] | None:
    """A recurrence starting at `word`, and how many of the following words it used."""
    if word in REPEAT_ADVERBS:
        return {"every": 1, "unit": REPEAT_ADVERBS[word], "anchor": "due"}, 0
    if word not in REPEAT_WORDS:
        return None
    following = [w.lower().rstrip(",.") for w in rest[:3]]
    if following and following[0] in ("les", "the"):  # "tous les jours", "toutes les 2 semaines"
        following, skipped = following[1:], 1
    else:
        skipped = 0
    every = 1
    if following and following[0].isdigit() and 0 < int(following[0]) <= 365:
        every, following, skipped = int(following[0]), following[1:], skipped + 1
    if following and following[0] in REPEAT_UNITS:
        return {"every": every, "unit": REPEAT_UNITS[following[0]], "anchor": "due"}, skipped + 1
    return None


def _project(name: str) -> Project | None:
    name = name.strip().lower()
    if not name:
        return None
    return db.session.scalar(
        select(Project).where(
            Project.deleted_at.is_(None), or_(Project.slug == name, func.lower(Project.name) == name)
        )
    )


def parse(text: str, today: date | None = None) -> Parsed:
    today = today or date.today()
    words = text.split()
    types = workflow.types()
    result = Parsed()
    title: list[str] = []
    i = 0
    while i < len(words):
        word = words[i]
        lower = word.lower()
        rest = words[i + 1 :]
        if lower in DUE_WORDS or lower in DO_WORDS:
            found, used = _date(rest, today)
            if found is not None:
                if lower in DUE_WORDS:
                    result.due_on = found
                    result.note("due", f"Due {found:%a %d %b}")
                else:
                    result.do_on = found
                    result.note("do", f"Do on {found:%a %d %b}")
                i += 1 + used
                continue
        if lower in PROJECT_WORDS and rest:
            project = _project(rest[0]) or (_project(" ".join(rest[:2])) if len(rest) > 1 else None)
            if project is not None:
                result.project = project
                result.note("project", project.name)
                i += 1 + (1 if _project(rest[0]) else 2)
                continue
        if word.startswith("+") and len(word) > 1 and (project := _project(word[1:])):
            result.project = project
            result.note("project", project.name)
            i += 1
            continue
        if word.startswith("#") and len(word) > 1:
            key = lower[1:]
            if key in types and result.type is None:
                result.type = key
                result.note("type", types[key]["label"])
            elif re.fullmatch(r"[\w][\w.+-]{0,31}", key):
                result.tags.append(key)
                result.note("tag", f"#{key}")
            i += 1
            continue
        if result.recurrence is None and (found := _repeat(lower, rest)):
            rule, used = found
            result.recurrence = rule
            result.note("repeat", recurrence_core.describe(rule).split(",")[0])
            i += 1 + used
            continue
        if lower == "!hard":
            result.hard_deadline = True
            result.note("hard", "Hard deadline")
            i += 1
            continue
        if word.startswith("!") and lower[1:] in PRIORITY_WORDS:
            result.priority = PRIORITY_WORDS[lower[1:]]
            result.note("priority", f"Priority {result.priority}")
            i += 1
            continue
        if m := re.fullmatch(r"~(\d+(?:[.,]\d+)?)(h|m|min|d)", lower):
            amount = float(m[1].replace(",", "."))
            hours = amount / 60 if m[2] in ("m", "min") else amount * 8 if m[2] == "d" else amount
            if 0 < hours <= 10_000:
                result.estimate_hours = round(hours, 2)
                result.note("estimate", f"~{result.estimate_hours:g} h")
                i += 1
                continue
        if re.fullmatch(r"@[\w.-]{1,40}", word):
            result.assignee = word[1:].lower()
            result.note("assignee", word)
            i += 1
            continue
        if lower in ("today", "tomorrow", "demain") and result.do_on is None:
            result.do_on, _ = _date([lower], today)
            result.note("do", f"Do on {result.do_on:%a %d %b}")
            i += 1
            continue
        title.append(word)
        i += 1
    result.title = " ".join(title).strip()
    if result.hard_deadline and result.due_on is None:
        result.hard_deadline = False
        result.understood = [chip for chip in result.understood if chip["kind"] != "hard"]
    return result


def to_create(
    parsed: Parsed, *, project_id: uuid.UUID | None = None, parent_id: uuid.UUID | None = None
) -> TaskCreate:
    values: dict[str, Any] = {"title": parsed.title, "parent_id": parent_id, "tags": parsed.tags}
    values["project_id"] = parsed.project.id if parsed.project else project_id
    for key in ("type", "priority", "due_on", "do_on", "estimate_hours", "assignee", "recurrence"):
        if getattr(parsed, key) is not None:
            values[key] = getattr(parsed, key)
    values["hard_deadline"] = parsed.hard_deadline
    return TaskCreate(**values)


def similar_tasks(
    title: str, project_id: uuid.UUID | None = None, limit: int = 3
) -> list[tuple[float, Task]]:
    """Open tasks whose title is close to `title` (possible duplicates), best first."""
    wanted = " ".join(title.lower().split())
    if len(wanted) < 4:
        return []
    query = select(Task).where(Task.deleted_at.is_(None), Task.is_open.is_(True))
    if project_id is not None:
        query = query.where(or_(Task.project_id == project_id, Task.project_id.is_(None)))
    matches = []
    for task in db.session.scalars(query):
        ratio = difflib.SequenceMatcher(None, wanted, task.title.lower()).ratio()
        if ratio >= DUPLICATE_RATIO:
            matches.append((ratio, task))
    return sorted(matches, key=lambda m: -m[0])[:limit]


def quick_add(text: str, *, project_id: uuid.UUID | None = None, parent_id: uuid.UUID | None = None) -> Task:
    parsed = parse(text)
    if not parsed.title:
        raise tasks_core.TaskError("Write what the task is, not only its date or tags.")
    return tasks_core.create(to_create(parsed, project_id=project_id, parent_id=parent_id))
