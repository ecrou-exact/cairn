"""Task pages: list, quick add, full form, task page, status, checklist, dependencies, timer."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, url_for

from app.core.schema.planning import BulkEdit, DependencyCreate, TaskCreate, TaskUpdate
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.settings import get_setting
from app.core.utils.web import FormErrors, back_to, flash_undo, split_list, validate
from app.features.comments import comments_core
from app.features.projects import projects_core
from app.features.resources import resources_core
from app.features.tasks import (
    brief_core,
    dependencies_core,
    quickadd_core,
    related_core,
    risk_core,
    tasks_core,
    templates_core,
    timer_core,
    workflow,
)
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


def _spawned(task, before) -> bool:
    """True when the change just made created the next occurrence of a repeating task."""
    return task.next_occurrence_id is not None and task.next_occurrence_id != before


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


def list_context() -> dict:
    """What every task list with bulk and inline editing needs (Tasks page, project page)."""
    return {
        "types": workflow.types(),
        "workflow_statuses": workflow.statuses(),
        "project_options": projects_core.options(),
        "templates": templates_core.templates(),
    }


@tasks.get("/tasks")
def index():
    after = latest_event_id()
    page = tasks_core.list_tasks(request.args)
    return render_template("tasks/index.html", page=page, events_after=after, **list_context())


@tasks.post("/tasks/bulk")
def bulk():
    form = request.form
    action = form.get("action", "")
    values: dict = {"task_ids": form.getlist("task_ids")}
    if action == "status":
        values["status"] = form.get("status") or None
    elif action == "priority":
        values["priority"] = form.get("priority") or None
    elif action == "project":
        target = form.get("project_id", "")
        values |= {"clear_project": True} if target == "none" else {"project_id": target or None}
    elif action == "tags":
        values |= {
            "add_tags": split_list(form.get("add_tags")),
            "remove_tags": split_list(form.get("remove_tags")),
        }
    elif action == "delete":
        values["delete"] = True
    else:
        abort(400)
    try:
        data = validate(BulkEdit, values)
    except FormErrors as exc:
        flash("Select at least one task." if "task_ids" in exc.errors else str(exc), "danger")
        return redirect(back_to(url_for("tasks.index")))
    with batch() as batch_id:
        changed, skipped = tasks_core.bulk_edit(data)
    if changed:
        what = "moved to the trash" if data.delete else "changed"
        flash_undo(f"{changed} task{'s' if changed != 1 else ''} {what}.", batch_id)
    for reason in skipped[:5]:
        flash(f"Skipped {reason}", "warning")
    if not changed and not skipped:
        flash("Nothing to change: the selected tasks already have it.", "info")
    return redirect(back_to(url_for("tasks.index")))


@tasks.post("/tasks/<uuid:task_id>/priority")
def change_priority(task_id: uuid.UUID):
    try:
        with batch() as batch_id:
            task = tasks_core.update(
                task_id, validate(TaskUpdate, {"priority": request.form.get("priority")})
            )
    except tasks_core.TaskNotFound:
        abort(404)
    except (FormErrors, tasks_core.TaskError) as exc:
        flash(str(exc), "danger")
    else:
        flash_undo(f"“{task.title}” is now {task.priority} priority.", batch_id)
    return redirect(back_to(url_for("tasks.detail", task_id=task_id)))


@tasks.post("/tasks/from-template")
def from_template():
    project_id = request.form.get("project_id") or None
    try:
        with batch() as batch_id:
            task = templates_core.instantiate(
                request.form.get("template", ""),
                request.form.get("title", ""),
                project_id=uuid.UUID(project_id) if project_id else None,
            )
    except (tasks_core.TaskError, ValueError) as exc:
        flash(str(exc).splitlines()[0], "danger")
        return redirect(back_to(url_for("tasks.index")))
    flash_undo(f"Created “{task.title}” from a template.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task.id))


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
    return redirect(back_to(url_for("tasks.index")))


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
    ancestors = tasks_core.ancestors(task)
    return render_template(
        "tasks/detail.html",
        task=task,
        events_after=after,
        ancestors=ancestors,
        subtasks=tasks_core.subtasks(task.id),
        dependencies=dependencies_core.for_task(task.id),
        chain=dependencies_core.blocking_chain(task.id) if task.is_blocked else [],
        risk=risk_core.risk_of(task.id) if task.is_open and task.due_on else None,
        next_statuses=[workflow.status_map()[key] for key in workflow.allowed_next(task.status)],
        types=workflow.types(),
        history=tasks_core.task_history(task.id),
        time_entries=timer_core.entries(task.id),
        timing=current is not None and current[1].id == task.id,
        directions=DEPENDENCY_DIRECTIONS,
        resources=resources_core.for_target("task", task.id),
        max_mb=get_setting("resources.max_upload_mb"),
        comments=comments_core.for_target("task", task.id),
        inherited=[
            (source, c)
            for source, c in comments_core.corrections_for_task(task, ancestors)
            if source != "this task"
        ],
        brief=brief_core.task_brief(task),
        related=related_core.related_for(task),
    )


@tasks.get("/tasks/<uuid:task_id>/brief.md")
def brief(task_id: uuid.UUID):
    task = _task_or_404(task_id)
    response = make_response(brief_core.task_brief(task))
    response.mimetype = "text/markdown"
    response.headers["Content-Disposition"] = f'attachment; filename="task-{task.id}.md"'
    return response


@tasks.post("/tasks/<uuid:task_id>/status")
def change_status(task_id: uuid.UUID):
    status = request.form.get("status", "")
    before = _task_or_404(task_id).next_occurrence_id
    try:
        with batch() as batch_id:
            task = tasks_core.set_status(task_id, status)
    except tasks_core.TaskNotFound:
        abort(404)
    except tasks_core.TaskError as exc:
        flash(str(exc), "danger")
    else:
        message = f"“{task.title}” is now {workflow.label_of(task.status)}."
        following = tasks_core.get_task(task.next_occurrence_id) if _spawned(task, before) else None
        if following is not None:
            when = f" for {following.due_on:%a %d %b}" if following.due_on else ""
            message += f" Next one created{when}."
        flash_undo(message, batch_id)
    return redirect(back_to(url_for("tasks.detail", task_id=task_id)))


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
    return redirect(back_to(url_for("tasks.index")))


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
    return redirect(back_to(url_for("tasks.detail", task_id=task_id)))


@tasks.post("/timer/stop")
def stop_timer():
    seconds = timer_core.stop()
    if seconds:
        flash(f"Timer stopped: {timer_core.format_duration(seconds)} added.", "success")
    return redirect(back_to(url_for("home.index")))
