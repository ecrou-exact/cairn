"""Task pages: list, quick add, full form, task page, status, checklist, dependencies, timer."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.schema.planning import DependencyCreate, TaskCreate, TaskUpdate
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, validate
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, quickadd_core, tasks_core, timer_core, workflow
from app.features.tasks.tasks_forms import values_from_form, values_from_task

tasks = Blueprint("tasks", __name__)

DEPENDENCY_DIRECTIONS = {
    # form choice -> (kind, this task is the source?)
    "blocked_by": ("blocks", False),
    "blocks": ("blocks", True),
    "follows": ("follows", False),
    "relates": ("relates", True),
    "duplicates": ("duplicates", True),
}


def _back(default: str) -> str:
    target = request.form.get("next") or ""
    if target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target.rstrip("?")
    return default


def _task_or_404(task_id: uuid.UUID):
    try:
        return tasks_core.get_task(task_id)
    except tasks_core.TaskNotFound:
        abort(404)


def _form_context(values, errors: dict | None = None, task=None) -> dict:
    """What the task form needs; choices are (value, label) pairs."""
    return {
        "values": values,
        "errors": errors or {},
        "task": task,
        "project_choices": [(str(p.id), p.name) for p in projects_core.options()],
        "type_choices": [(key, info["label"]) for key, info in workflow.types().items()],
        "status_choices": [
            (s["key"], s["label"]) for s in workflow.status_choices(task.status if task else None)
        ],
    }


# -- lists and quick add ---------------------------------------------------------------------


@tasks.get("/tasks")
def index():
    after = latest_event_id()
    page = tasks_core.list_tasks(request.args)
    return render_template("tasks/index.html", page=page, events_after=after, types=workflow.types())


@tasks.post("/tasks/quick")
def quick_add():
    text = request.form.get("text", "")
    project_id = request.form.get("project_id") or None
    parent_id = request.form.get("parent_id") or None
    try:
        with batch() as batch_id:
            task = quickadd_core.quick_add(
                text,
                project_id=uuid.UUID(project_id) if project_id else None,
                parent_id=uuid.UUID(parent_id) if parent_id else None,
            )
    except (tasks_core.TaskError, ValueError) as exc:
        flash(str(exc).splitlines()[0], "danger")
    else:
        flash_undo(f"Added “{task.title}”.", batch_id)
    return redirect(_back(url_for("tasks.index")))


# -- full form -------------------------------------------------------------------------------


@tasks.get("/tasks/new")
def new():
    values = {
        "project_id": request.args.get("project_id", ""),
        "parent_id": request.args.get("parent_id", ""),
    }
    values |= {"status": workflow.default_status(), "priority": "medium", "importance": 3, "urgency": 3}
    return render_template("tasks/form.html", **_form_context(values))


@tasks.post("/tasks/new")
def create():
    values = values_from_form(request.form)
    try:
        with batch() as batch_id:
            task = tasks_core.create(validate(TaskCreate, values))
    except FormErrors as exc:
        return render_template("tasks/form.html", **_form_context(request.form, exc.errors)), 422
    except tasks_core.TaskError as exc:
        return render_template("tasks/form.html", **_form_context(request.form, {"": str(exc)})), 422
    flash_undo(f"Created “{task.title}”.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task.id))


@tasks.get("/tasks/<uuid:task_id>/edit")
def edit(task_id: uuid.UUID):
    task = _task_or_404(task_id)
    return render_template("tasks/form.html", **_form_context(values_from_task(task), task=task))


@tasks.post("/tasks/<uuid:task_id>/edit")
def save(task_id: uuid.UUID):
    task = _task_or_404(task_id)
    try:
        with batch() as batch_id:
            tasks_core.update(task.id, validate(TaskUpdate, values_from_form(request.form)))
    except FormErrors as exc:
        return render_template("tasks/form.html", **_form_context(request.form, exc.errors, task)), 422
    except tasks_core.TaskError as exc:
        return render_template("tasks/form.html", **_form_context(request.form, {"": str(exc)}, task)), 422
    flash_undo("Saved.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task.id))


# -- task page -------------------------------------------------------------------------------


@tasks.get("/tasks/<uuid:task_id>")
def detail(task_id: uuid.UUID):
    after = latest_event_id()
    task = _task_or_404(task_id)
    current = timer_core.running()
    return render_template(
        "tasks/detail.html",
        task=task,
        events_after=after,
        ancestors=tasks_core.ancestors(task),
        subtasks=tasks_core.subtasks(task.id),
        dependencies=dependencies_core.for_task(task.id),
        chain=dependencies_core.blocking_chain(task.id) if task.is_blocked else [],
        next_statuses=[workflow.status_map()[key] for key in workflow.allowed_next(task.status)],
        types=workflow.types(),
        history=tasks_core.task_history(task.id),
        time_entries=timer_core.entries(task.id),
        timing=current is not None and current[1].id == task.id,
        directions=DEPENDENCY_DIRECTIONS,
    )


@tasks.post("/tasks/<uuid:task_id>/status")
def change_status(task_id: uuid.UUID):
    status = request.form.get("status", "")
    try:
        with batch() as batch_id:
            task = tasks_core.set_status(task_id, status)
    except tasks_core.TaskNotFound:
        abort(404)
    except tasks_core.TaskError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo(f"“{task.title}” is now {workflow.label_of(task.status)}.", batch_id)
    return redirect(_back(url_for("tasks.detail", task_id=task_id)))


@tasks.post("/tasks/<uuid:task_id>/checklist/<int:index>")
def toggle_item(task_id: uuid.UUID, index: int):
    try:
        tasks_core.toggle_checklist(task_id, index)
    except tasks_core.TaskNotFound:
        abort(404)
    except tasks_core.TaskError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("tasks.detail", task_id=task_id, _anchor="checklist"))


@tasks.post("/tasks/<uuid:task_id>/delete")
def delete(task_id: uuid.UUID):
    try:
        with batch() as batch_id:
            count = tasks_core.delete(task_id)
    except tasks_core.TaskNotFound:
        abort(404)
    extra = f" with {count - 1} subtask{'s' if count > 2 else ''}" if count > 1 else ""
    flash_undo(f"Moved to the trash{extra}.", batch_id)
    return redirect(_back(url_for("tasks.index")))


# -- dependencies ----------------------------------------------------------------------------


@tasks.post("/tasks/<uuid:task_id>/dependencies")
def add_dependency(task_id: uuid.UUID):
    _task_or_404(task_id)
    direction = DEPENDENCY_DIRECTIONS.get(request.form.get("direction", ""))
    other = request.form.get("other_id", "")
    try:
        other_id = uuid.UUID(other)
    except ValueError:
        flash("Pick a task in the list.", "danger")
        return redirect(url_for("tasks.detail", task_id=task_id, _anchor="dependencies"))
    if direction is None:
        abort(400)
    kind, outgoing = direction
    source, target = (task_id, other_id) if outgoing else (other_id, task_id)
    try:
        with batch() as batch_id:
            dependencies_core.add(
                DependencyCreate(
                    from_task_id=source, to_task_id=target, kind=kind, note=request.form.get("note", "")
                )
            )
    except (dependencies_core.DependencyError, ValueError) as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Dependency added.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task_id, _anchor="dependencies"))


@tasks.post("/tasks/<uuid:task_id>/dependencies/<uuid:dependency_id>/remove")
def remove_dependency(task_id: uuid.UUID, dependency_id: uuid.UUID):
    try:
        with batch() as batch_id:
            dependencies_core.remove(dependency_id)
    except dependencies_core.DependencyError:
        abort(404)
    flash_undo("Dependency removed.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task_id, _anchor="dependencies"))


# -- timer -----------------------------------------------------------------------------------


@tasks.post("/tasks/<uuid:task_id>/timer/start")
def start_timer(task_id: uuid.UUID):
    try:
        task = timer_core.start(task_id)
    except tasks_core.TaskNotFound:
        abort(404)
    except tasks_core.TaskError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Working on “{task.title}”. The timer runs until you stop it or close the task.", "success")
    return redirect(_back(url_for("tasks.detail", task_id=task_id)))


@tasks.post("/timer/stop")
def stop_timer():
    seconds = timer_core.stop()
    if seconds:
        flash(f"Timer stopped: {timer_core.format_duration(seconds)} added.", "success")
    return redirect(_back(url_for("home.index")))
