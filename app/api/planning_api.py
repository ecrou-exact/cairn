"""Planning API: projects, tasks, dependencies, quick add with preview, timer, search, undo."""

from __future__ import annotations

import uuid

from flask import jsonify, request, url_for

from app.api import ApiError, api_blueprint, body
from app.core.schema.common import page_dict
from app.core.schema.planning import (
    ConditionCreate,
    ConditionOut,
    ConditionResolve,
    DependencyCreate,
    DependencyOut,
    ProjectCreate,
    ProjectLinkCreate,
    ProjectLinkOut,
    ProjectOut,
    ProjectUpdate,
    QuickAdd,
    TaskCreate,
    TaskOut,
    TaskStatus,
    TaskUpdate,
)
from app.core.utils import history
from app.core.utils.history import batch
from app.features.projects import project_links_core, projects_core
from app.features.resources import resources_core
from app.features.search import search_core
from app.features.tasks import (
    conditions_core,
    dependencies_core,
    quickadd_core,
    related_core,
    tasks_core,
    timer_core,
    workflow,
)

planning_api = api_blueprint("planning_api")


def _task(task) -> dict:
    return TaskOut.model_validate(task).model_dump(mode="json")


def _project(project) -> dict:
    return ProjectOut.model_validate(project).model_dump(mode="json")


def _guard(action, *args):
    """Core errors as API answers: missing → 404, refused → 409/422."""
    try:
        with batch() as batch_id:
            result = action(*args)
    except (tasks_core.TaskNotFound, projects_core.ProjectNotFound) as exc:
        raise ApiError(str(exc), 404) from exc
    except conditions_core.ConditionError as exc:
        raise ApiError(str(exc), 404) from exc
    except (
        tasks_core.TaskError,
        projects_core.ProjectError,
        dependencies_core.DependencyError,
        project_links_core.ProjectLinkError,
    ) as exc:
        raise ApiError(str(exc), 422) from exc
    return result, batch_id


# -- projects --------------------------------------------------------------------------------


@planning_api.get("/projects")
def list_projects():
    page = projects_core.list_projects(request.args)
    return jsonify(page_dict(page, [_project(p) for p in page.items]))


@planning_api.post("/projects")
def create_project():
    project, batch_id = _guard(projects_core.create, body(ProjectCreate))
    return jsonify(project=_project(project), batch=str(batch_id)), 201


@planning_api.get("/projects/<uuid:project_id>")
def get_project(project_id: uuid.UUID):
    project, _ = _guard(projects_core.get_project, project_id)
    return jsonify(_project(project))


@planning_api.patch("/projects/<uuid:project_id>")
def update_project(project_id: uuid.UUID):
    project, batch_id = _guard(projects_core.update, project_id, body(ProjectUpdate))
    return jsonify(project=_project(project), batch=str(batch_id))


@planning_api.delete("/projects/<uuid:project_id>")
def delete_project(project_id: uuid.UUID):
    moved, batch_id = _guard(projects_core.delete, project_id)
    return jsonify(tasks_moved=moved, batch=str(batch_id))


# -- tasks -----------------------------------------------------------------------------------


@planning_api.get("/tasks")
def list_tasks():
    page = tasks_core.list_tasks(request.args)
    return jsonify(page_dict(page, [_task(t) for t in page.items]))


@planning_api.post("/tasks")
def create_task():
    task, batch_id = _guard(tasks_core.create, body(TaskCreate))
    return jsonify(task=_task(task), batch=str(batch_id)), 201


@planning_api.get("/tasks/<uuid:task_id>")
def get_task(task_id: uuid.UUID):
    task, _ = _guard(tasks_core.get_task, task_id)
    data = _task(task)
    data["dependencies"] = {
        group: [{"id": str(dep.id), "task_id": str(other.id), "title": other.title} for dep, other in items]
        for group, items in dependencies_core.for_task(task.id).items()
    }
    data["subtasks"] = [
        {"id": str(t.id), "title": t.title, "status": t.status} for t in tasks_core.subtasks(task.id)
    ]
    return jsonify(data)


@planning_api.get("/tasks/<uuid:task_id>/related")
def related(task_id: uuid.UUID):
    """Close tasks, matching resources and schedule fit, each with why (base of `find_related`)."""
    task, _ = _guard(tasks_core.get_task, task_id)
    found = related_core.related_for(task)
    fit = found.schedule
    return jsonify(
        tasks=[
            {
                "id": str(m.task.id),
                "title": m.task.title,
                "status": m.task.status,
                "score": m.score,
                "why": m.why,
            }
            for m in found.tasks
        ],
        resources=[
            {"id": str(r.id), "title": r.title, "kind": r.kind, "why": why} for r, why in found.resources
        ],
        schedule=None
        if fit is None
        else {
            "due_on": fit.due_on.isoformat(),
            "available_hours": fit.available_hours,
            "booked_hours": fit.booked_hours,
            "booked_tasks": fit.booked_tasks,
            "own_hours": fit.own_hours,
            "free_hours": fit.free_hours,
            "fits": fit.fits,
        },
    )


@planning_api.patch("/tasks/<uuid:task_id>")
def update_task(task_id: uuid.UUID):
    task, batch_id = _guard(tasks_core.update, task_id, body(TaskUpdate))
    return jsonify(task=_task(task), batch=str(batch_id))


@planning_api.post("/tasks/<uuid:task_id>/status")
def set_task_status(task_id: uuid.UUID):
    task, batch_id = _guard(tasks_core.set_status, task_id, body(TaskStatus).status)
    return jsonify(task=_task(task), batch=str(batch_id))


@planning_api.delete("/tasks/<uuid:task_id>")
def delete_task(task_id: uuid.UUID):
    moved, batch_id = _guard(tasks_core.delete, task_id)
    return jsonify(tasks_moved=moved, batch=str(batch_id))


@planning_api.get("/workflow")
def get_workflow():
    return jsonify(statuses=workflow.statuses(), types=workflow.types(), default=workflow.default_status())


# -- quick add -------------------------------------------------------------------------------


@planning_api.post("/tasks/parse")
def parse_quick_add():
    """What quick add understood, without creating anything (live preview)."""
    data = body(QuickAdd)
    parsed = quickadd_core.parse(data.text)
    project_id = parsed.project.id if parsed.project else data.project_id
    similar = quickadd_core.similar_tasks(parsed.title, project_id) if parsed.title else []
    return jsonify(
        title=parsed.title,
        understood=parsed.understood,
        similar=[
            {
                "id": str(t.id),
                "title": t.title,
                "url": url_for("tasks.detail", task_id=t.id),
                "match": round(r, 2),
            }
            for r, t in similar
        ],
    )


@planning_api.post("/tasks/quick")
def quick_add():
    data = body(QuickAdd)
    task, batch_id = _guard(quickadd_core.quick_add, data.text, data.project_id, data.parent_id)
    return jsonify(task=_task(task), batch=str(batch_id), url=url_for("tasks.detail", task_id=task.id)), 201


# -- dependencies ----------------------------------------------------------------------------


@planning_api.post("/dependencies")
def add_dependency():
    dependency, batch_id = _guard(dependencies_core.add, body(DependencyCreate))
    return jsonify(
        dependency=DependencyOut.model_validate(dependency).model_dump(mode="json"), batch=str(batch_id)
    ), 201


@planning_api.post("/project-links")
def add_project_link():
    """`from_project_id` passes before `to_project_id` (D-044); refused if it closes a loop."""
    link, batch_id = _guard(project_links_core.add, body(ProjectLinkCreate))
    return jsonify(link=ProjectLinkOut.model_validate(link).model_dump(mode="json"), batch=str(batch_id)), 201


@planning_api.delete("/project-links/<uuid:link_id>")
def remove_project_link(link_id: uuid.UUID):
    try:
        with batch() as batch_id:
            project_links_core.remove(link_id)
    except project_links_core.ProjectLinkError as exc:
        raise ApiError(str(exc), 404) from exc
    return jsonify(batch=str(batch_id))


@planning_api.delete("/dependencies/<uuid:dependency_id>")
def remove_dependency(dependency_id: uuid.UUID):
    try:
        with batch() as batch_id:
            dependencies_core.remove(dependency_id)
    except dependencies_core.DependencyError as exc:
        raise ApiError(str(exc), 404) from exc
    return jsonify(batch=str(batch_id))


@planning_api.get("/tasks/<uuid:task_id>/conditions")
def list_conditions(task_id: uuid.UUID):
    _guard(tasks_core.get_task, task_id)
    return jsonify(
        items=[
            ConditionOut.model_validate(c).model_dump(mode="json") for c in conditions_core.for_task(task_id)
        ]
    )


@planning_api.post("/conditions")
def add_condition():
    condition, batch_id = _guard(conditions_core.add, body(ConditionCreate))
    return jsonify(
        condition=ConditionOut.model_validate(condition).model_dump(mode="json"), batch=str(batch_id)
    ), 201


@planning_api.patch("/conditions/<uuid:condition_id>")
def resolve_condition(condition_id: uuid.UUID):
    data = body(ConditionResolve)
    condition, batch_id = _guard(conditions_core.set_resolved, condition_id, data.resolved)
    return jsonify(
        condition=ConditionOut.model_validate(condition).model_dump(mode="json"), batch=str(batch_id)
    )


@planning_api.delete("/conditions/<uuid:condition_id>")
def remove_condition(condition_id: uuid.UUID):
    _, batch_id = _guard(conditions_core.remove, condition_id)
    return jsonify(batch=str(batch_id))


# -- timer, search, undo ---------------------------------------------------------------------


@planning_api.get("/timer")
def get_timer():
    current = timer_core.running()
    if current is None:
        return jsonify(running=False)
    entry, task = current
    return jsonify(
        running=True,
        started_at=entry.started_at.isoformat(),
        task={"id": str(task.id), "title": task.title, "url": url_for("tasks.detail", task_id=task.id)},
    )


@planning_api.post("/tasks/<uuid:task_id>/timer/start")
def start_timer(task_id: uuid.UUID):
    task, _ = _guard(timer_core.start, task_id)
    return jsonify(task=_task(task))


@planning_api.post("/timer/stop")
def stop_timer():
    return jsonify(seconds=timer_core.stop())


@planning_api.get("/search")
def search():
    found = search_core.search(request.args.get("q", ""), open_only=request.args.get("open") == "1")
    parents = search_core.parent_titles(found["tasks"])
    place = search_core.github_place(request.args.get("q", ""))
    return jsonify(
        projects=[
            {"id": str(p.id), "name": p.name, "slug": p.slug, "url": url_for("projects.detail", slug=p.slug)}
            for p in found["projects"]
        ],
        github=(
            {"repo": place[0], "kind": place[1], "what": place[2], "known": bool(found["projects"])}
            if place
            else None
        ),
        tasks=[
            {
                "id": str(t.id),
                "title": t.title,
                "status": workflow.label_of(t.status),
                "open": t.is_open,
                "project": t.project.name if t.project else None,
                "parent": parents.get(t.parent_id),
                "url": url_for("tasks.detail", task_id=t.id),
            }
            for t in found["tasks"]
        ],
        resources=[
            {
                "id": str(r.id),
                "title": r.title,
                "kind": resources_core.KIND_LABELS[r.kind],
                "icon": resources_core.icon_of(r),
                "url": url_for("resources.detail", resource_id=r.id),
            }
            for r in found["resources"]
        ],
    )


@planning_api.post("/history/<uuid:batch_id>/undo")
def undo(batch_id: uuid.UUID):
    try:
        redo = history.undo(batch_id)
    except (history.UndoError, ValueError) as exc:
        raise ApiError(str(exc), 409) from exc
    return jsonify(batch=str(redo))
