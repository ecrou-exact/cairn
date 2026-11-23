"""Tasks: create, edit, change status, delete / restore / purge, lists and views.

Every change is one history batch (undoable), writes a diff to the activity log,
publishes `task.changed` and refreshes the derived columns (blocked, score…).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy import delete as sql_delete

from app.core.db_class.base import utcnow
from app.core.db_class.planning import PRIORITIES, Dependency, Project, Task, TimeEntry
from app.core.extensions import db
from app.core.schema.planning import BulkEdit, TaskCreate, TaskUpdate
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.comments import comments_core
from app.features.resources import resources_core
from app.features.tasks import conditions_core, recurrence_core, workflow
from app.features.tasks.dependencies_core import refresh_derived
from app.features.tasks.risk_core import deadline_risks

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


def clean_custom(values: dict[str, Any]) -> dict[str, Any]:
    """Custom field values checked against their definitions; empty ones are dropped."""
    fields = workflow.custom_fields()
    clean: dict[str, Any] = {}
    for key, raw in values.items():
        spec = fields.get(key)
        if spec is None:
            raise TaskError(f"There is no custom field '{key}' (see Settings → Custom task fields).")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        label, kind = spec["label"], spec["type"]
        text = raw.strip() if isinstance(raw, str) else raw
        if kind == "number":
            try:
                clean[key] = float(text)
            except (TypeError, ValueError):
                raise TaskError(f"{label} must be a number.") from None
        elif kind == "date":
            try:
                clean[key] = date.fromisoformat(str(text)).isoformat()
            except ValueError:
                raise TaskError(f"{label} must be a date (YYYY-MM-DD).") from None
        elif kind == "url":
            if not re.fullmatch(r"https?://\S{1,1990}", str(text)):
                raise TaskError(f"{label} must be a web address starting with http:// or https://.")
            clean[key] = text
        elif kind == "select":
            if text not in spec.get("options", []):
                raise TaskError(f"{label} must be one of: {', '.join(spec.get('options', []))}.")
            clean[key] = text
        else:
            if len(str(text)) > 500:
                raise TaskError(f"{label} is too long (500 characters at most).")
            clean[key] = str(text)
    return clean


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
    values["custom"] = clean_custom(values.get("custom") or {})
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
    # exclude_unset also drops the defaults inside nested items (`done: false`, `anchor`)
    if data.checklist is not None:
        fields["checklist"] = [item.model_dump() for item in data.checklist]
    if data.recurrence is not None:
        fields["recurrence"] = data.recurrence.model_dump()
    if "custom" in fields:
        fields["custom"] = clean_custom(fields["custom"] or {})
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
        if was_open and workflow.kind_of(task.status) == "done":
            _spawn_next_occurrence(task)
        refresh_derived()
        _changed(task)
    return task


def _spawn_next_occurrence(task: Task) -> Task | None:
    """A recurring task just done: create the next one (once, even if it is reopened and
    done again). Undoing the change removes it with the rest of the batch."""
    if not task.recurrence:
        return None
    existing = db.session.get(Task, task.next_occurrence_id) if task.next_occurrence_id else None
    if existing is not None and not existing.is_deleted:
        return None
    dates = recurrence_core.next_dates(
        task.recurrence, start_on=task.start_on, do_on=task.do_on, due_on=task.due_on, today=date.today()
    )
    following = create(
        TaskCreate(
            title=task.title,
            description_md=task.description_md,
            project_id=task.project_id,
            parent_id=task.parent_id,
            type=task.type,
            priority=task.priority,
            importance=task.importance,
            urgency=task.urgency,
            hard_deadline=task.hard_deadline and dates["due_on"] is not None,
            estimate_hours=task.estimate_hours,
            assignee=task.assignee,
            tags=task.tags,
            checklist=[{"text": item["text"], "done": False} for item in task.checklist],
            acceptance_md=task.acceptance_md,
            claude_instructions_md=task.claude_instructions_md,
            recurrence=task.recurrence,
            custom=task.custom,
            **dates,
        )
    )
    log_action(
        "task.recur",
        target_type="task",
        target_id=task.id,
        diff={"next_occurrence_id": [_json(task.next_occurrence_id), str(following.id)]},
    )
    task.next_occurrence_id = following.id
    return following


def _undo_recur(row) -> None:
    task = db.session.get(Task, uuid.UUID(row.target_id))
    if task is not None:
        old = row.diff["next_occurrence_id"][0]
        task.next_occurrence_id = uuid.UUID(old) if old else None


register_undo("task.recur", _undo_recur)


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
    """Delete for good, from the trash only: the task, its subtasks, links, time entries,
    comments and resource attachments (the resources stay in the library)."""
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
    resources_core.forget_targets("task", ids)
    comments_core.forget_targets("task", ids)
    conditions_core.forget_tasks(ids)
    for item in reversed(family):  # children first
        log_action(
            "task.purge", target_type="task", target_id=item.id, meta={"title": item.title}, level="warning"
        )
        db.session.delete(item)
        db.session.flush()
    refresh_derived()
    db.session.commit()


def bulk_edit(data: BulkEdit) -> tuple[int, list[str]]:
    """Apply one change to many tasks in one batch. Tasks the change cannot apply to (a
    transition the workflow refuses, a task deleted meanwhile) are skipped and reported;
    the others are changed. Returns (changed count, reasons for the skipped ones)."""
    changed, skipped = 0, []
    with batch():
        for task_id in dict.fromkeys(data.task_ids):
            task = db.session.get(Task, task_id)
            if task is not None and task.is_deleted and data.delete:
                continue  # a subtask already moved with its selected parent
            if task is None or task.is_deleted:
                skipped.append("A selected task no longer exists.")
                continue
            if data.delete:
                changed += delete(task_id)
                continue
            fields: dict[str, Any] = {}
            if data.status and data.status != task.status:
                fields["status"] = data.status
            if data.priority:
                fields["priority"] = data.priority
            if data.clear_project:
                fields["project_id"] = None
            elif data.project_id:
                fields["project_id"] = data.project_id
            if data.add_tags or data.remove_tags:
                tags = [t for t in task.tags if t not in data.remove_tags]
                fields["tags"] = tags + [t for t in data.add_tags if t not in tags]
            if not any(getattr(task, key) != value for key, value in fields.items()):
                continue
            try:
                update(task.id, TaskUpdate(**fields))
                changed += 1
            except TaskError as exc:
                skipped.append(f"“{task.title}”: {exc}")
    return changed, skipped


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


def in_live_projects() -> ColumnElement:
    """A task of no project, or of a project that is neither paused nor archived (D-095): the
    others are left out of what to do, the home page, the lists and the counts until resumed."""
    resting = select(Project.id).where(Project.status.in_(("paused", "archived")))
    return Task.project_id.is_(None) | Task.project_id.not_in(resting)


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
    elif "project" not in args:  # a paused project's tasks when that project is asked for
        query = query.where(in_live_projects())
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


def next_actions(
    limit: int = 7, today: date | None = None, project_id: uuid.UUID | None = None
) -> list[Task]:
    """“What should I do now?”: actionable tasks (open, not blocked, not waiting, not
    scheduled for later), highest score first (PROJECT_BRIEF.md §3), optionally in one project."""
    today = today or date.today()
    in_project = [Task.project_id == project_id] if project_id is not None else [in_live_projects()]
    return list(
        db.session.scalars(
            select(Task)
            .where(
                *in_project,
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
    open_tasks = select(Task).where(Task.deleted_at.is_(None), Task.is_open.is_(True), in_live_projects())
    found: list[tuple[str, str, Task]] = []
    seen: set[uuid.UUID] = set()

    def add(key: str, text: str, task: Task) -> None:
        if task.id not in seen:
            seen.add(task.id)
            found.append((key, text, task))

    for task in db.session.scalars(open_tasks.where(Task.due_on < today).order_by(Task.due_on)):
        days = (today - task.due_on).days
        add("overdue", f"{days} day{'s' if days > 1 else ''} overdue", task)
    for risk in deadline_risks(today):
        unknown = f", {risk.unknown} without estimate" if risk.unknown else ""
        chain = (
            f" with {risk.chain_size - 1} blocking task{'s' if risk.chain_size > 2 else ''}"
            if risk.chain_size > 1
            else ""
        )
        add(
            "at_risk",
            f"needs ~{risk.needed_hours:g} h{chain}{unknown}, {risk.available_hours:g} h of work time left",
            risk.task,
        )
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


def pulse(today: date | None = None) -> dict[str, int]:
    """Today's numbers: open, ready to do, blocked, late, and done in the last 7 days."""
    today = today or date.today()
    waiting = workflow.keys_of_kinds("waiting")
    live = select(func.count()).select_from(Task).where(Task.deleted_at.is_(None), in_live_projects())
    is_open = Task.is_open.is_(True)
    since = datetime.combine(today - timedelta(days=7), datetime.min.time(), tzinfo=UTC)
    return {
        "open": db.session.scalar(live.where(is_open)) or 0,
        "ready": db.session.scalar(
            live.where(is_open, Task.blocked_by_count == 0, Task.status.not_in(waiting))
        )
        or 0,
        "blocked": db.session.scalar(
            live.where(is_open, (Task.blocked_by_count > 0) | Task.status.in_(waiting))
        )
        or 0,
        "late": db.session.scalar(live.where(is_open, Task.due_on < today)) or 0,
        "done_week": db.session.scalar(live.where(Task.completed_at >= since)) or 0,
    }


def counts_by_state() -> dict[str, int]:
    rows = db.session.execute(
        select(Task.is_open, func.count())
        .where(Task.deleted_at.is_(None), in_live_projects())
        .group_by(Task.is_open)
    ).all()
    return {"open" if is_open else "closed": count for is_open, count in rows}
