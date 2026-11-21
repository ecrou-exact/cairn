"""External conditions a task waits for (PROJECT_BRIEF.md §2.3).

"Waiting for review from X", "waiting for upstream release vX.Y", "waiting for a PR to be
merged", "waiting until a date". An open condition blocks the task like a blocking task
does (`refresh_derived` counts it); a `date` condition lifts itself on its day.
Conditions are links on the task: removed for good, kept in the activity log for undo.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.planning import ExternalCondition, Task
from app.core.extensions import db
from app.core.schema.planning import ConditionCreate
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action
from app.features.tasks.dependencies_core import refresh_derived

KIND_LABELS = {
    "review": "Review",
    "release": "Upstream release",
    "pr": "Pull request merged",
    "date": "A date",
    "other": "Something else",
}
KIND_ICONS = {
    "review": "fa-user-check",
    "release": "fa-box-open",
    "pr": "fa-code-merge",
    "date": "fa-calendar-day",
    "other": "fa-hourglass-half",
}


class ConditionError(ValueError):
    pass


def _get(condition_id: uuid.UUID) -> ExternalCondition:
    condition = db.session.get(ExternalCondition, condition_id)
    if condition is None:
        raise ConditionError("This condition does not exist.")
    return condition


def _snapshot(condition: ExternalCondition) -> dict:
    return {
        "task_id": str(condition.task_id),
        "kind": condition.kind,
        "label": condition.label,
        "url": condition.url,
        "until_on": condition.until_on.isoformat() if condition.until_on else None,
    }


def _changed(condition: ExternalCondition) -> None:
    db.session.flush()
    refresh_derived()
    publish("task.changed", {"id": str(condition.task_id)})


def add(data: ConditionCreate) -> ExternalCondition:
    task = db.session.get(Task, data.task_id)
    if task is None or task.is_deleted:
        raise ConditionError("This task does not exist.")
    with batch():
        condition = ExternalCondition(**data.model_dump(), created_by=current_actor())
        db.session.add(condition)
        db.session.flush()
        log_action(
            "condition.create", target_type="condition", target_id=condition.id, meta=_snapshot(condition)
        )
        _changed(condition)
    return condition


def set_resolved(condition_id: uuid.UUID, resolved: bool) -> ExternalCondition:
    condition = _get(condition_id)
    if (condition.resolved_at is not None) == resolved:
        return condition
    with batch():
        old = condition.resolved_at.isoformat() if condition.resolved_at else None
        condition.resolved_at = utcnow() if resolved else None
        log_action(
            "condition.resolve" if resolved else "condition.reopen",
            target_type="condition",
            target_id=condition.id,
            diff={"resolved_at": [old, condition.resolved_at.isoformat() if condition.resolved_at else None]},
        )
        _changed(condition)
    return condition


def remove(condition_id: uuid.UUID) -> ExternalCondition:
    condition = _get(condition_id)
    with batch():
        log_action(
            "condition.delete", target_type="condition", target_id=condition.id, meta=_snapshot(condition)
        )
        db.session.delete(condition)
        _changed(condition)
    return condition


def forget_tasks(task_ids: list[uuid.UUID]) -> None:
    if task_ids:
        db.session.execute(sql_delete(ExternalCondition).where(ExternalCondition.task_id.in_(task_ids)))


def for_task(task_id: uuid.UUID) -> list[ExternalCondition]:
    return list(
        db.session.scalars(
            select(ExternalCondition)
            .where(ExternalCondition.task_id == task_id)
            .order_by(ExternalCondition.resolved_at.is_not(None), ExternalCondition.created_at)
        )
    )


def waiting(task_id: uuid.UUID, today: date | None = None) -> list[ExternalCondition]:
    today = today or date.today()
    return [c for c in for_task(task_id) if c.is_waiting(today)]


def _undo_create(row) -> None:
    condition = db.session.get(ExternalCondition, uuid.UUID(row.target_id))
    if condition is not None:
        remove(condition.id)


def _undo_delete(row) -> None:
    add(ConditionCreate.model_validate(row.meta))


def _undo_resolve(row) -> None:
    if db.session.get(ExternalCondition, uuid.UUID(row.target_id)) is not None:
        set_resolved(uuid.UUID(row.target_id), False)


def _undo_reopen(row) -> None:
    if db.session.get(ExternalCondition, uuid.UUID(row.target_id)) is not None:
        set_resolved(uuid.UUID(row.target_id), True)


register_undo("condition.create", _undo_create)
register_undo("condition.delete", _undo_delete)
register_undo("condition.resolve", _undo_resolve)
register_undo("condition.reopen", _undo_reopen)
