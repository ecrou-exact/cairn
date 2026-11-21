"""Time tracking: one running timer at most. Starting work on a task stops the previous
timer and moves the task to the first active status when the workflow allows it."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.planning import Task, TimeEntry
from app.core.extensions import db
from app.core.schema.planning import TaskUpdate
from app.core.utils.events import publish
from app.core.utils.logger import log_action
from app.features.tasks import tasks_core, workflow


def running() -> tuple[TimeEntry, Task] | None:
    entry = db.session.scalar(select(TimeEntry).where(TimeEntry.ended_at.is_(None)).limit(1))
    if entry is None:
        return None
    return entry, db.session.get(Task, entry.task_id)


def _close(entry: TimeEntry) -> int:
    entry.ended_at = utcnow()
    seconds = max(0, int((entry.ended_at - entry.started_at).total_seconds()))
    task = db.session.get(Task, entry.task_id)
    task.tracked_seconds += seconds
    log_action("timer.stop", target_type="task", target_id=task.id, meta={"seconds": seconds})
    return seconds


def start(task_id: uuid.UUID) -> Task:
    task = tasks_core.get_task(task_id)
    if not task.is_open:
        raise tasks_core.TaskError("This task is closed: reopen it before working on it.")
    current = running()
    if current is not None and current[1].id == task.id:
        return task
    if current is not None:
        _close(current[0])
    db.session.add(TimeEntry(task_id=task.id, started_at=utcnow()))
    log_action("timer.start", target_type="task", target_id=task.id)
    publish("timer.changed", {"running": True, "task_id": str(task.id), "title": task.title})
    db.session.commit()
    active = workflow.first_status("active")
    if workflow.kind_of(task.status) == "open" and active in workflow.allowed_next(task.status):
        tasks_core.update(task.id, TaskUpdate(status=active))
    return task


def stop() -> int:
    """Stop the running timer; returns the seconds it added (0 when none was running)."""
    current = running()
    if current is None:
        return 0
    seconds = _close(current[0])
    publish("timer.changed", {"running": False})
    db.session.commit()
    return seconds


def entries(task_id: uuid.UUID, limit: int = 20) -> list[TimeEntry]:
    return list(
        db.session.scalars(
            select(TimeEntry)
            .where(TimeEntry.task_id == task_id, TimeEntry.ended_at.is_not(None))
            .order_by(TimeEntry.started_at.desc())
            .limit(limit)
        )
    )


def format_duration(seconds: int) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes = rest // 60
    return f"{hours} h {minutes:02d}" if hours else f"{minutes} min"
