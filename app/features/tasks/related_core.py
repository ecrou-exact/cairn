"""What is related to a task: close tasks, matching resources, and how it fits the schedule.

Shown on the task page, put in the task brief, and the base of the `find_related` MCP tool
that a Claude run uses to fill a task (roadmap: "Ask Claude to fill a task"). Deterministic
and explainable: every match says why it was found.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlsplit

from sqlalchemy import or_, select

from app.core.db_class.planning import Task
from app.core.db_class.resource import Resource
from app.core.extensions import db
from app.core.utils.listing import escape_like
from app.features.resources import resources_core
from app.features.tasks import risk_core, tasks_core

_WORD = re.compile(r"[\w][\w.+-]*", re.UNICODE)
# Words of four letters or more that say nothing about a topic (shorter ones are skipped anyway).
STOPWORDS = frozenset(
    {
        "with", "from", "into", "that", "this", "then", "than", "when", "what", "which", "about",
        "after", "before", "over", "under", "make", "more", "most", "some", "such", "only", "also",
        "just", "very", "each", "pour", "avec", "dans", "sans", "sous", "plus", "faire", "mettre",
        "ajouter",
    }
)  # fmt: skip
MIN_SCORE = 0.25


@dataclass
class Match:
    task: Task
    score: float
    why: list[str] = field(default_factory=list)


@dataclass
class ScheduleFit:
    due_on: date
    available_hours: float
    booked_hours: float  # open estimated work due on or before the same day, other tasks
    booked_tasks: int
    own_hours: float | None

    @property
    def free_hours(self) -> float:
        return round(self.available_hours - self.booked_hours, 1)

    @property
    def fits(self) -> bool | None:
        return None if self.own_hours is None else self.own_hours <= self.free_hours


@dataclass
class Related:
    tasks: list[Match]
    resources: list[tuple[Resource, str]]
    schedule: ScheduleFit | None


def keywords(text: str) -> set[str]:
    return {w for w in (m.lower() for m in _WORD.findall(text)) if len(w) >= 4 and w not in STOPWORDS}


def _family_ids(task: Task) -> set:
    ids = {task.id, *(parent.id for parent in tasks_core.ancestors(task))}
    ids |= {sub.id for sub in tasks_core.subtasks(task.id)}
    return ids


def related_tasks(task: Task, limit: int = 6) -> list[Match]:
    words = keywords(task.title) | set(task.tags)
    if not words:
        return []
    skip = _family_ids(task)
    title = " ".join(task.title.lower().split())
    matches = []
    for other in db.session.scalars(select(Task).where(Task.deleted_at.is_(None))):
        if other.id in skip:
            continue
        other_words = keywords(other.title)
        shared_words = sorted(words & other_words)
        shared_tags = sorted(set(task.tags) & set(other.tags))
        ratio = difflib.SequenceMatcher(None, title, other.title.lower()).ratio()
        score = 0.5 * len(shared_words) / max(len(words | other_words), 1) + 0.25 * min(len(shared_tags), 2)
        score += 0.4 * max(ratio - 0.5, 0) * 2
        if other.project_id is not None and other.project_id == task.project_id:
            score += 0.05
        if score < MIN_SCORE:
            continue
        why = []
        if ratio >= 0.75:
            why.append("almost the same title")
        if shared_words:
            why.append("words: " + ", ".join(shared_words[:4]))
        if shared_tags:
            why.append("tags: " + ", ".join(f"#{t}" for t in shared_tags))
        matches.append(Match(other, round(score, 2), why))
    return sorted(matches, key=lambda m: (-m.score, not m.task.is_open))[:limit]


def related_resources(task: Task, limit: int = 5) -> list[tuple[Resource, str]]:
    """Library resources not attached to the task whose title, address or tags match its words."""
    words = sorted(keywords(task.title) | set(task.tags))[:8]
    if not words:
        return []
    attached = {r.id for _, r in resources_core.for_target("task", task.id)}
    clauses = []
    for word in words:
        pattern = f"%{escape_like(word)}%"
        clauses += [Resource.title.ilike(pattern, escape="\\"), Resource.url.ilike(pattern, escape="\\")]
    found = []
    for resource in db.session.scalars(
        select(Resource)
        .where(Resource.deleted_at.is_(None), or_(*clauses))
        .order_by(Resource.updated_at.desc())
    ):
        if resource.id in attached:
            continue
        # The site name is not a topic: every GitHub link would match a task about GitHub.
        haystack = f"{resource.title} {urlsplit(resource.url or '').path} {' '.join(resource.tags)}".lower()
        hits = [w for w in words if w in haystack]
        if not hits:
            continue
        found.append((len(hits), resource, "matches " + ", ".join(hits[:3])))
    found.sort(key=lambda item: -item[0])
    return [(resource, why) for _, resource, why in found[:limit]]


def schedule_fit(task: Task, today: date | None = None) -> ScheduleFit | None:
    """Working time until the due date, and how much of it other open tasks already take."""
    today = today or date.today()
    if task.due_on is None or not task.is_open or task.due_on < today:
        return None
    others = db.session.scalars(
        select(Task).where(
            Task.deleted_at.is_(None),
            Task.is_open.is_(True),
            Task.id != task.id,
            Task.due_on.is_not(None),
            Task.due_on <= task.due_on,
            Task.estimate_hours.is_not(None),
        )
    ).all()
    booked = sum(max(t.estimate_hours - t.tracked_seconds / 3600, 0) for t in others)
    own = None if task.estimate_hours is None else max(task.estimate_hours - task.tracked_seconds / 3600, 0)
    return ScheduleFit(
        task.due_on, risk_core.available_hours(task.due_on, today), round(booked, 1), len(others), own
    )


def related_for(task: Task) -> Related:
    return Related(related_tasks(task), related_resources(task), schedule_fit(task))
