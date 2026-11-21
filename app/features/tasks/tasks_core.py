"""Tasks: create, edit, change status, delete / restore / purge, lists and views.

Every change is one history batch (undoable), writes a diff to the activity log,
publishes `task.changed` and refreshes the derived columns (blocked, score…).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy import delete as sql_delete

from app.core.db_class.base import utcnow
from app.core.db_class.planning import PRIORITIES, Dependency, Project, Task, TimeEntry
from app.core.extensions import db
from app.core.schema.planning import TaskCreate, TaskUpdate
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.tasks import workflow
from app.features.tasks.dependencies_core import refresh_derived

# Columns an edit may change, in form order (also the fields compared for the diff).
EDITABLE = tuple(TaskUpdate.model_fields)


class TaskError(ValueError):
    pass


class TaskNotFound(TaskError):
    pass


def _json(value: Any) -> Any:
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def get_task(task_id: uuid.UUID, *, deleted: bool = False) -> Task:
    task = db.session.get(Task, task_id)
    if task is None or task.is_deleted != deleted:
        raise TaskNotFound("This task does not exist." if not deleted else "This task is not in the trash.")
    return task


def _check_type(task_type: str) -> None:
    if task_type not in workflow.types():
        raise TaskError(f"Unknown task type '{task_type}'.")


def _check_status(status: str) -> None:
    if status not in workflow.status_map():
        raise TaskError(f"Unknown status '{status}'.")


def _check_project(project_id: uuid.UUID | None) -> None:
    if project_id is None:
        return
    project = db.session.get(Project, project_id)
    if project is None or project.is_deleted:
        raise TaskError("This project does not exist.")


def _check_parent(task_id: uuid.UUID | None, parent_id: uuid.UUID | None) -> None:
    if parent_id is None:
        return
    node = db.session.get(Task, parent_id)
    if node is None or node.is_deleted:
        raise TaskError("The parent task does not exist.")
    while node is not None:
        if node.id == task_id:
            raise TaskError("A task cannot be placed under itself or one of its subtasks.")
        node = db.session.get(Task, node.parent_id) if node.parent_id else None


def _changed(task: Task) -> None:
    publish("task.changed", {"id": str(task.id), "status": task.status, "title": task.title})


# -- writing ---------------------------------------------------------------------------------


def create(data: TaskCreate) -> Task:
    values = data.model_dump()
    values["status"] = values["status"] or workflow.default_status()
    _check_type(values["type"])
    _check_status(values["status"])
    _check_project(values["project_id"])
    _check_parent(None, values["parent_id"])
    if values["parent_id"] and not values["project_id"]:
        values["project_id"] = db.session.get(
            Task, values["parent_id"]
        ).project_id  # subtasks follow their parent
    with batch():
        task = Task(**values, created_by=current_actor())
        if not workflow.is_open_status(task.status):
            task.completed_at = utcnow()
        db.session.add(task)
        db.session.flush()
        log_action(
            "task.create",
            target_type="task",
            target_id=task.id,
            diff={k: [None, _json(v)] for k, v in values.items() if v not in (None, "", [], False)},
        )
        refresh_derived()
        _changed(task)
    return task


def update(task_id: uuid.UUID, data: TaskUpdate, *, force: bool = False) -> Task:
    """Apply the fields set in `data`. `force` skips the workflow transition check (undo)."""
    task = get_task(task_id)
    fields = data.model_dump(exclude_unset=True)
    if "type" in fields:
        _check_type(fields["type"])
    if "status" in fields and fields["status"] != task.status:
        _check_status(fields["status"])
        if not force and fields["status"] not in workflow.allowed_next(task.status):
            old, new = workflow.label_of(task.status), workflow.label_of(fields["status"])
            raise TaskError(f"A task cannot go from {old} to {new}.")
    if "project_id" in fields:
        _check_project(fields["project_id"])
    if "parent_id" in fields:
        _check_parent(task.id, fields["parent_id"])
    diff = {
        key: [_json(getattr(task, key)), _json(value)]
        for key, value in fields.items()
        if getattr(task, key) != value
    }
    if not diff:
        return task
    with batch():
        was_open = workflow.is_open_status(task.status)
        for key in diff:
            setattr(task, key, fields[key])
        now_open = workflow.is_open_status(task.status)
        if was_open and not now_open:
            task.completed_at = utcnow()
            _stop_timer_of(task)
        elif now_open and not was_open:
            task.completed_at = None
        log_action("task.update", target_type="task", target_id=task.id, diff=diff)
        refresh_derived()
        _changed(task)
    return task


def set_status(task_id: uuid.UUID, status: str) -> Task:
    return update(task_id, TaskUpdate(status=status))


def toggle_checklist(task_id: uuid.UUID, index: int) -> Task:
    task = get_task(task_id)
    if not 0 <= index < len(task.checklist):
        raise TaskError("This checklist item does not exist.")
    items = [dict(item) for item in task.checklist]
    items[index]["done"] = not items[index].get("done", False)
    return update(task_id, TaskUpdate(checklist=items))


def _descendants(task: Task, *, deleted_at: datetime | None) -> list[Task]:
    found: list[Task] = []
    frontier = [task.id]
    while frontier:
        children = list(
            db.session.scalars(
                select(Task).where(
                    Task.parent_id.in_(frontier),
                    Task.deleted_at.is_(None) if deleted_at is None else Task.deleted_at == deleted_at,
                )
            )
        )
        found.extend(children)
        frontier = [child.id for child in children]
    return found


def _stop_timer_of(task: Task) -> None:
    entry = db.session.scalar(
        select(TimeEntry).where(TimeEntry.task_id == task.id, TimeEntry.ended_at.is_(None))
    )
    if entry is not None:
        entry.ended_at = utcnow()
        task.tracked_seconds += int((entry.ended_at - entry.started_at).total_seconds())
        publish("timer.changed", {"running": False})


def _delete_one(task: Task, when: datetime) -> None:
    task.deleted_at = when
    _stop_timer_of(task)
    log_action(
        "task.delete", target_type="task", target_id=task.id, diff={"deleted_at": [None, when.isoformat()]}
    )
    _changed(task)


def _restore_one(task: Task) -> None:
    log_action(
        "task.restore",
        target_type="task",
        target_id=task.id,
        diff={"deleted_at": [task.deleted_at.isoformat(), None]},
    )
    task.deleted_at = None
    _changed(task)


def delete(task_id: uuid.UUID) -> int:
    """Move a task and its subtasks to the trash; returns how many tasks were moved."""
    task = get_task(task_id)
    when = utcnow()
    with batch():
        family = [task, *_descendants(task, deleted_at=None)]
        for item in family:
            _delete_one(item, when)
        db.session.flush()
        refresh_derived()
    return len(family)


def restore(task_id: uuid.UUID) -> int:
    """Bring a task back from the trash with the subtasks that were deleted with it."""
    task = get_task(task_id, deleted=True)
    parent = db.session.get(Task, task.parent_id) if task.parent_id else None
    if parent is not None and parent.is_deleted:
        raise TaskError(f"Restore its parent “{parent.title}” first.")
    if task.project_id and db.session.get(Project, task.project_id).is_deleted:
        raise TaskError("Restore its project first.")
    with batch():
        family = [task, *_descendants(task, deleted_at=task.deleted_at)]
        for item in family:
            _restore_one(item)
        db.session.flush()
        refresh_derived()
    return len(family)


def purge(task_id: uuid.UUID) -> None:
    """Delete for good, from the trash only: the task, its subtasks, links and time entries."""
    task = get_task(task_id, deleted=True)
    family = [task, *_descendants(task, deleted_at=task.deleted_at)]
    ids = [item.id for item in family]
    remaining_children = db.session.scalar(
        select(func.count()).select_from(Task).where(Task.parent_id.in_(ids), Task.id.not_in(ids))
    )
    if remaining_children:
        raise TaskError("Some subtasks are not in the trash: move them first.")
    db.session.execute(
        sql_delete(Dependency).where(or_(Dependency.from_task_id.in_(ids), Dependency.to_task_id.in_(ids)))
    )
    db.session.execute(sql_delete(TimeEntry).where(TimeEntry.task_id.in_(ids)))
    for item in reversed(family):  # children first
        log_action(
            "task.purge", target_type="task", target_id=item.id, meta={"title": item.title}, level="warning"
        )
        db.session.delete(item)
        db.session.flush()
    refresh_derived()
    db.session.commit()


# -- undo ------------------------------------------------------------------------------------


def _undo_create(row) -> None:
    task = db.session.get(Task, uuid.UUID(row.target_id))
    if task is not None and not task.is_deleted:
        with batch():
            _delete_one(task, utcnow())
            db.session.flush()
            refresh_derived()


def _undo_update(row) -> None:
    old = {key: values[0] for key, values in row.diff.items()}
    update(uuid.UUID(row.target_id), TaskUpdate.model_validate(old), force=True)


def _undo_delete(row) -> None:
    task = db.session.get(Task, uuid.UUID(row.target_id))
    if task is not None and task.is_deleted:
        _restore_one(task)
        db.session.flush()
        refresh_derived()


def _undo_restore(row) -> None:
    task = db.session.get(Task, uuid.UUID(row.target_id))
    if task is not None and not task.is_deleted:
        _delete_one(task, utcnow())
        db.session.flush()
        refresh_derived()


register_undo("task.create", _undo_create)
register_undo("task.update", _undo_update)
register_undo("task.delete", _undo_delete)
register_undo("task.restore", _undo_restore)


# -- lists -----------------------------------------------------------------------------------

PRIORITY_RANK = case({p: len(PRIORITIES) - i for i, p in enumerate(PRIORITIES)}, value=Task.priority, else_=0)


def list_spec(*, with_project_filter: bool = True) -> ListSpec:
    today = date.today()
    statuses = tuple((s["key"], s["label"]) for s in workflow.statuses())
    types = tuple((key, info["label"]) for key, info in workflow.types().items())
    filters = [
        FilterSpec(
            "state",
            "Show",
            None,
            (
                ("open", "Open"),
                ("actionable", "Actionable"),
                ("blocked", "Blocked"),
                ("overdue", "Overdue"),
                ("closed", "Done or cancelled"),
            ),
            conditions={
                "open": Task.is_open.is_(True),
                "actionable": Task.is_open.is_(True)
                & (Task.blocked_by_count == 0)
                & Task.status.not_in(workflow.keys_of_kinds("waiting")),
                "blocked": Task.is_open.is_(True)
                & ((Task.blocked_by_count > 0) | Task.status.in_(workflow.keys_of_kinds("waiting"))),
                "overdue": Task.is_open.is_(True) & (Task.due_on < today),
                "closed": Task.is_open.is_(False),
            },
        ),
        FilterSpec("status", "Status", Task.status, statuses),
        FilterSpec("type", "Type", Task.type, types),
        FilterSpec("priority", "Priority", Task.priority, tuple((p, p.capitalize()) for p in PRIORITIES)),
    ]
    if with_project_filter:
        projects = tuple(
            (str(pid), name)
            for pid, name in db.session.execute(
                select(Project.id, Project.name).where(Project.deleted_at.is_(None)).order_by(Project.name)
            )
        )
        filters.append(
            FilterSpec(
                "project",
                "Project",
                None,
                (("none", "No project"), *projects),
                conditions={"none": Task.project_id.is_(None)}
                | {value: Task.project_id == uuid.UUID(value) for value, _ in projects},
            )
        )
    return ListSpec(
        sortable={
            "score": Task.score,
            "due": Task.due_on,
            "priority": PRIORITY_RANK,
            "title": func.lower(Task.title),
            "created": Task.created_at,
            "updated": Task.updated_at,
            "status": Task.status,
        },
        default_sort="score",
        tiebreak=Task.id,
        searchable=(Task.title, Task.description_md),
        filters=tuple(filters),
    )


def list_tasks(args: Mapping[str, Any], *, project_id: uuid.UUID | None = None) -> ListPage:
    query = select(Task).where(Task.deleted_at.is_(None))
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    return run_list(list_spec(with_project_filter=project_id is None), query, args)


def subtasks(task_id: uuid.UUID) -> list[Task]:
    return list(
        db.session.scalars(
            select(Task)
            .where(Task.parent_id == task_id, Task.deleted_at.is_(None))
            .order_by(Task.is_open.desc(), Task.score.desc(), Task.created_at)
        )
    )


def ancestors(task: Task) -> list[Task]:
    chain: list[Task] = []
    node = db.session.get(Task, task.parent_id) if task.parent_id else None
    while node is not None and len(chain) < 50:
        chain.append(node)
        node = db.session.get(Task, node.parent_id) if node.parent_id else None
    return chain[::-1]


def deleted_tasks() -> list[Task]:
    return list(
        db.session.scalars(select(Task).where(Task.deleted_at.is_not(None)).order_by(Task.deleted_at.desc()))
    )


def task_history(task_id: uuid.UUID, limit: int = 50):
    from app.core.db_class.activity import Activity

    return list(
        db.session.scalars(
            select(Activity)
            .where(Activity.target_type == "task", Activity.target_id == str(task_id))
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
    )


# -- views -----------------------------------------------------------------------------------


def next_actions(limit: int = 7, today: date | None = None) -> list[Task]:
    """“What should I do now?”: actionable tasks (open, not blocked, not waiting, not
    scheduled for later), highest score first (PROJECT_BRIEF.md §3)."""
    today = today or date.today()
    return list(
        db.session.scalars(
            select(Task)
            .where(
                Task.deleted_at.is_(None),
                Task.is_open.is_(True),
                Task.blocked_by_count == 0,
                Task.status.not_in(workflow.keys_of_kinds("waiting")),
                or_(Task.do_on.is_(None), Task.do_on <= today),
                or_(Task.start_on.is_(None), Task.start_on <= today),
            )
            .order_by(Task.score.desc(), Task.created_at)
            .limit(limit)
        )
    )


def needs_attention(today: date | None = None) -> list[tuple[str, str, Task]]:
    """The Today radar: (reason key, sentence, task), most pressing first."""
    today = today or date.today()
    rules = get_setting("tasks.attention")
    open_tasks = select(Task).where(Task.deleted_at.is_(None), Task.is_open.is_(True))
    found: list[tuple[str, str, Task]] = []
    seen: set[uuid.UUID] = set()

    def add(key: str, text: str, task: Task) -> None:
        if task.id not in seen:
            seen.add(task.id)
            found.append((key, text, task))

    for task in db.session.scalars(open_tasks.where(Task.due_on < today).order_by(Task.due_on)):
        days = (today - task.due_on).days
        add("overdue", f"{days} day{'s' if days > 1 else ''} overdue", task)
    waiting = workflow.keys_of_kinds("waiting")
    for task in db.session.scalars(open_tasks.where(Task.status.in_(waiting), Task.blocked_by_count == 0)):
        add("unblocked", "Marked blocked, but nothing blocks it any more", task)
    soon = today + timedelta(days=int(rules["due_soon_days"]))
    for task in db.session.scalars(
        open_tasks.where(Task.due_on >= today, Task.due_on <= soon).order_by(Task.due_on)
    ):
        days = (task.due_on - today).days
        when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
        hard = "hard deadline, " if task.hard_deadline else ""
        blocked = f", still blocked by {task.blocked_by_count}" if task.blocked_by_count else ""
        add("due_soon", f"{hard}due {when}{blocked}", task)
    stale_before = utcnow() - timedelta(days=int(rules["stale_active_days"]))
    active = workflow.keys_of_kinds("active")
    for task in db.session.scalars(
        open_tasks.where(Task.status.in_(active), Task.updated_at < stale_before).order_by(Task.updated_at)
    ):
        days = (utcnow() - task.updated_at).days
        add("stale", f"{workflow.label_of(task.status)}, untouched for {days} days", task)
    return found


def counts_by_state() -> dict[str, int]:
    rows = db.session.execute(
        select(Task.is_open, func.count()).where(Task.deleted_at.is_(None)).group_by(Task.is_open)
    ).all()
    return {"open" if is_open else "closed": count for is_open, count in rows}
