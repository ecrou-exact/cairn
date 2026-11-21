"""Deadline risk (PROJECT_BRIEF.md §3): the work still to do on a task and on every open
task blocking it, against the working time left before its due date.

remaining(task) = max(estimate − time spent, 0); a task without estimate counts as unknown.
available = working days from today to the due date (both included) × hours per day,
from the `tasks.capacity` setting.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select

from app.core.db_class.planning import Dependency, Task
from app.core.extensions import db
from app.core.utils.settings import get_setting


@dataclass(frozen=True)
class Risk:
    task: Task
    needed_hours: float
    available_hours: float
    chain_size: int  # open tasks counted, this one included
    unknown: int  # of which without estimate

    @property
    def short_by(self) -> float:
        return round(self.needed_hours - self.available_hours, 1)


def available_hours(due_on: date, today: date) -> float:
    capacity = get_setting("tasks.capacity")
    work_days = set(capacity["work_days"])
    days = sum(
        1 for n in range((due_on - today).days + 1) if (today + timedelta(days=n)).weekday() in work_days
    )
    return days * float(capacity["hours_per_day"])


def _remaining(task: Task) -> float | None:
    if task.estimate_hours is None:
        return None
    return max(task.estimate_hours - task.tracked_seconds / 3600, 0.0)


def deadline_risks(today: date | None = None) -> list[Risk]:
    """Open tasks due today or later whose chain needs more time than is left, worst first."""
    today = today or date.today()
    open_tasks = {
        t.id: t
        for t in db.session.scalars(select(Task).where(Task.deleted_at.is_(None), Task.is_open.is_(True)))
    }
    blockers: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for source, target in db.session.execute(
        select(Dependency.from_task_id, Dependency.to_task_id).where(Dependency.kind == "blocks")
    ):
        if source in open_tasks and target in open_tasks:
            blockers[target].append(source)

    risks: list[Risk] = []
    for task in open_tasks.values():
        if task.due_on is None or task.due_on < today:
            continue  # overdue tasks are already flagged as such
        chain, stack = {task.id}, list(blockers.get(task.id, ()))
        while stack:
            node = stack.pop()
            if node not in chain:
                chain.add(node)
                stack.extend(blockers.get(node, ()))
        remaining = [_remaining(open_tasks[node]) for node in chain]
        needed = round(sum(r for r in remaining if r is not None), 1)
        available = available_hours(task.due_on, today)
        if needed > available:
            risks.append(Risk(task, needed, available, len(chain), sum(r is None for r in remaining)))
    return sorted(risks, key=lambda r: -r.short_by)


def risk_of(task_id: uuid.UUID, today: date | None = None) -> Risk | None:
    return next((r for r in deadline_risks(today) if r.task.id == task_id), None)
