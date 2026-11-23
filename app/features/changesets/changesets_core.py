"""Changesets (D-071): Claude proposes several changes to the plan at once, the owner approves
them one by one, and what is kept is applied in one batch, undone at once.

A proposal is tried first and rolled back, so what cannot work (a loop, a status move that is not
allowed, a task that is gone) is told to Claude instead of reaching the owner. Applying tries
again: the plan may have changed since. A change that needs one the owner refused is refused too.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import func, select

from app.core.db_class.changeset import CHANGESET_STATUSES, Changeset
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.changesets import ChangeItem, ChangesetCreate
from app.core.schema.comments import CommentCreate
from app.core.schema.planning import DependencyCreate, TaskCreate, TaskUpdate
from app.core.utils.actor import acting_as, current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action
from app.features.comments import comments_core
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, tasks_core, workflow

ITEM = TypeAdapter(ChangeItem)
LABELS = {
    "create_task": ("New task", "fa-plus"),
    "update_task": ("Change", "fa-pen"),
    "set_status": ("Status", "fa-arrow-right"),
    "link_tasks": ("Link", "fa-link"),
    "comment": ("Comment", "fa-comment"),
}
FIELDS = {"description": "description_md", "acceptance": "acceptance_md"}
DIRECT = ("type", "priority", "importance", "estimate_hours", "start_on", "do_on", "due_on", "tags", "title")
REFUSALS = (
    tasks_core.TaskError,
    tasks_core.TaskNotFound,
    dependencies_core.DependencyError,
    comments_core.CommentError,
    projects_core.ProjectError,
)


class ChangesetError(ValueError):
    pass


class _TriedOut(Exception):
    """Rolls a trial back."""


def get(changeset_id: uuid.UUID) -> Changeset:
    found = db.session.get(Changeset, changeset_id)
    if found is None or found.is_deleted:
        raise ChangesetError("This proposal does not exist.")
    return found


def _changed(changeset: Changeset) -> None:
    publish(
        "changeset.changed",
        {"id": str(changeset.id), "title": changeset.title, "status": changeset.status},
    )


# -- applying one item -------------------------------------------------------------------------


def _task(ref: str, made: Mapping[str, Task]) -> Task:
    if ref in made:
        return made[ref]
    try:
        return tasks_core.get_task(uuid.UUID(ref))
    except ValueError as exc:
        raise ChangesetError(f"“{ref}” is neither a task's id nor the key of an item before it") from exc


def _project(ref: str | None, fallback: uuid.UUID | None) -> uuid.UUID | None:
    if not ref:
        return fallback
    query = select(Project).where(Project.deleted_at.is_(None))
    try:
        query = query.where(Project.id == uuid.UUID(ref))
    except ValueError:
        query = query.where((Project.slug == ref.lower()) | (func.lower(Project.name) == ref.lower()))
    project = db.session.scalar(query)
    if project is None:
        raise ChangesetError(f"there is no project “{ref}”")
    return project.id


def _values(item: Any, task: Task | None = None) -> dict[str, Any]:
    given = item.model_dump(exclude_unset=True)
    values = {FIELDS.get(k, k): v for k, v in given.items() if k in FIELDS or k in DIRECT}
    if given.get("checklist") is not None:
        done = {entry["text"] for entry in task.checklist if entry.get("done")} if task else set()
        values["checklist"] = [{"text": text, "done": text in done} for text in given["checklist"]]
    return values


def _apply(item: Any, made: dict[str, Task], project_id: uuid.UUID | None) -> tuple[str, uuid.UUID]:
    """Do one change; returns what it touched."""
    if item.op == "create_task":
        parent = _task(item.parent, made) if item.parent else None
        place = parent.project_id if parent is not None else _project(item.project, project_id)
        values = {k: v for k, v in _values(item).items() if v is not None}
        task = tasks_core.create(
            TaskCreate.model_validate(
                {**values, "project_id": place, "parent_id": parent.id if parent else None}
            )
        )
        made[item.key] = task
    elif item.op == "link_tasks":
        first, task = _task(item.first, made), _task(item.then, made)
        dependencies_core.add(DependencyCreate(from_task_id=first.id, to_task_id=task.id, kind=item.kind))
    else:
        task = _task(item.task, made)
        if item.op == "update_task":
            tasks_core.update(task.id, TaskUpdate.model_validate(_values(item, task)))
        elif item.op == "set_status":
            tasks_core.set_status(task.id, item.status)
        else:
            comments_core.create(
                CommentCreate(target_type="task", target_id=task.id, kind="comment", body_md=item.text)
            )
    db.session.flush()
    return "task", task.id


def _apply_all(
    items: list[Any], keep: set[int], project_id: uuid.UUID | None
) -> tuple[dict[int, uuid.UUID], dict[int, str]]:
    """Apply the kept items in order: (what each touched, what each that failed says)."""
    made: dict[str, Task] = {}
    touched: dict[int, uuid.UUID] = {}
    wrong: dict[int, str] = {}
    for place, item in enumerate(items):
        if place not in keep:
            continue
        try:
            touched[place] = _apply(item, made, project_id)[1]
        except (ChangesetError, *REFUSALS) as exc:
            wrong[place] = str(exc)
        except ValueError as exc:  # pydantic: which field
            wrong[place] = "; ".join(
                f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in getattr(exc, "errors", list)()
            ) or str(exc)
    return touched, wrong


# -- proposing and answering -------------------------------------------------------------------


def propose(
    data: ChangesetCreate, project_id: uuid.UUID | None = None, session_id: uuid.UUID | None = None
) -> Changeset:
    wrong: dict[int, str] = {}
    try:
        with batch():
            _, wrong = _apply_all(data.items, set(range(len(data.items))), project_id)
            raise _TriedOut
    except _TriedOut:
        db.session.expire_all()
    if wrong:
        told = "; ".join(f"item {place + 1}: {text}" for place, text in sorted(wrong.items()))
        raise ChangesetError(f"Nothing was proposed. {told}")
    with batch():
        changeset = Changeset(
            title=data.title,
            reason_md=data.reason,
            project_id=project_id,
            session_id=session_id,
            items=[item.model_dump(mode="json", exclude_unset=True) for item in data.items],
            created_by=current_actor(),
        )
        db.session.add(changeset)
        db.session.flush()
        log_action(
            "changeset.propose",
            target_type="changeset",
            target_id=changeset.id,
            meta={"items": len(data.items), "title": data.title},
        )
        _changed(changeset)
    return changeset


def needs(items: list[dict[str, Any]]) -> list[list[int]]:
    """For each item, the items that create a task it names."""
    creators = {item["key"]: place for place, item in enumerate(items) if item["op"] == "create_task"}
    return [
        sorted(
            {
                creators[ref]
                for name in ("task", "parent", "first", "then")
                if (ref := item.get(name)) in creators
            }
        )
        for item in items
    ]


def apply(changeset_id: uuid.UUID, keep: list[int]) -> Changeset:
    """Apply what the owner keeps, all or nothing, as the one who proposed it."""
    changeset = get(changeset_id)
    if changeset.status != "proposed":
        raise ChangesetError("This proposal was already answered.")
    kept = {place for place in keep if place < len(changeset.items)}
    required = needs(changeset.items)
    while missing := {place for place in kept if not set(required[place]) <= kept}:
        kept -= missing  # it needs a task the owner refused
    if not kept:
        raise ChangesetError("Nothing to apply: what is kept needs a change that was refused.")
    items = [ITEM.validate_python(item) for item in changeset.items]
    with batch() as batch_id:
        with acting_as(changeset.created_by):
            touched, wrong = _apply_all(items, kept, changeset.project_id)
        if wrong:
            told = "; ".join(f"change {place + 1}: {text}" for place, text in sorted(wrong.items()))
            raise ChangesetError(f"Nothing was applied, the plan changed since: {told}")
        changeset.items = [
            {**item, "kept": place in kept, **({"target": str(touched[place])} if place in kept else {})}
            for place, item in enumerate(changeset.items)
        ]
        changeset.status, changeset.batch_id = "applied", batch_id
        log_action(
            "changeset.apply",
            target_type="changeset",
            target_id=changeset.id,
            meta={"kept": len(kept), "of": len(items)},
        )
        _changed(changeset)
    return changeset


def dismiss(changeset_id: uuid.UUID) -> Changeset:
    changeset = get(changeset_id)
    if changeset.status != "proposed":
        raise ChangesetError("This proposal was already answered.")
    with batch():
        changeset.status = "dismissed"
        log_action("changeset.dismiss", target_type="changeset", target_id=changeset.id)
        _changed(changeset)
    return changeset


def _undo_apply(row) -> None:
    """Undone with the changes themselves (one batch): it waits for an answer again."""
    changeset = db.session.get(Changeset, uuid.UUID(row.target_id))
    if changeset is not None:
        changeset.status, changeset.batch_id = "proposed", None
        changeset.items = [
            {k: v for k, v in item.items() if k not in ("kept", "target")} for item in changeset.items
        ]
        _changed(changeset)


def _undo_dismiss(row) -> None:
    changeset = db.session.get(Changeset, uuid.UUID(row.target_id))
    if changeset is not None and changeset.status == "dismissed":
        changeset.status = "proposed"
        _changed(changeset)


register_undo("changeset.apply", _undo_apply)
register_undo("changeset.dismiss", _undo_dismiss)


# -- reading -----------------------------------------------------------------------------------


def list_spec() -> ListSpec:
    return ListSpec(
        sortable={"created": Changeset.created_at, "title": func.lower(Changeset.title)},
        default_sort="created",
        default_direction="desc",
        tiebreak=Changeset.id,
        searchable=(Changeset.title, Changeset.reason_md),
        filters=(
            FilterSpec(
                "status", "Status", Changeset.status, tuple((s, s.capitalize()) for s in CHANGESET_STATUSES)
            ),
        ),
        views=("cards", "table"),
    )


def list_changesets(args: Mapping[str, Any]) -> ListPage:
    return run_list(list_spec(), select(Changeset).where(Changeset.deleted_at.is_(None)), args)


def waiting(project_id: uuid.UUID | None = None) -> list[Changeset]:
    query = select(Changeset).where(Changeset.status == "proposed", Changeset.deleted_at.is_(None))
    if project_id is not None:
        query = query.where(Changeset.project_id == project_id)
    return list(db.session.scalars(query.order_by(Changeset.created_at.desc())))


def _name(ref: str | None, created: Mapping[str, str]) -> dict[str, Any] | None:
    if not ref:
        return None
    if ref in created:
        return {"title": created[ref], "new": True, "url": None}
    try:
        task = db.session.get(Task, uuid.UUID(ref))
    except ValueError:
        task = None
    if task is None or task.is_deleted:
        return {"title": "a task that is gone", "new": False, "url": None}
    return {"title": task.title, "new": False, "url": f"/tasks/{task.id}"}


def _shown(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {v['text'] if isinstance(v, dict) else v}" for v in value)
    return "" if value is None else str(value)


def describe(changeset: Changeset) -> dict[str, Any]:
    """A proposal for the owner: each change in words, with what it replaces."""
    created = {item["key"]: item["title"] for item in changeset.items if item["op"] == "create_task"}
    required, rows = needs(changeset.items), []
    for place, item in enumerate(changeset.items):
        label, icon = LABELS[item["op"]]
        task = None
        if item["op"] in ("update_task", "set_status") and item["task"] not in created:
            try:
                task = db.session.get(Task, uuid.UUID(item["task"]))
            except ValueError:
                task = None
        fields = []
        for name, value in item.items():
            if name not in (*FIELDS, *DIRECT, "checklist", "status") or (
                name == "title" and item["op"] == "create_task"
            ):
                continue
            before = _shown(getattr(task, FIELDS.get(name, name), None)) if task is not None else ""
            after = _shown(value)
            if name == "status":
                before, after = workflow.label_of(before) if before else "", workflow.label_of(value)
            fields.append({"name": name.replace("_", " "), "before": before, "after": after})
        rows.append(
            {
                "place": place,
                "op": item["op"],
                "label": label,
                "icon": icon,
                "title": item.get("title") if item["op"] == "create_task" else None,
                "task": _name(item.get("task"), created),
                "parent": _name(item.get("parent"), created),
                "first": _name(item.get("first"), created),
                "then": _name(item.get("then"), created),
                "kind": item.get("kind", "blocks") if item["op"] == "link_tasks" else None,
                "text": item.get("text"),
                "fields": fields,
                "reason": item.get("reason", ""),
                "needs": required[place],
                "kept": item.get("kept"),
                "target": f"/tasks/{item['target']}" if item.get("target") else None,
            }
        )
    project = db.session.get(Project, changeset.project_id) if changeset.project_id else None
    return {
        "id": str(changeset.id),
        "title": changeset.title,
        "reason": changeset.reason_md,
        "status": changeset.status,
        "project": {"name": project.name, "slug": project.slug} if project else None,
        "session": str(changeset.session_id) if changeset.session_id else None,
        "by": comments_core.author_label(changeset.created_by),
        "created": changeset.created_at.isoformat(),
        "batch": str(changeset.batch_id) if changeset.batch_id else None,
        "items": rows,
        "kept": sum(1 for row in rows if row["kept"]),
    }
