"""Project pages: list (cards or table), project page with its tasks, form, delete."""

from __future__ import annotations

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from app.core.db_class.planning import PROJECT_COLORS, PROJECT_STATUSES
from app.core.schema.planning import ProjectCreate, ProjectUpdate
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.settings import get_setting
from app.core.utils.web import FormErrors, flash_undo, validate
from app.features.claude import claude_core
from app.features.comments import comments_core
from app.features.graph.graph import graph_view, with_graph_csp
from app.features.instances import found_core, instances_core
from app.features.projects import project_links_core, projects_core
from app.features.projects.projects_forms import values_from_form, values_from_project
from app.features.resources import resources_core
from app.features.tasks import tasks_core
from app.features.tasks.tasks import list_context

projects = Blueprint("projects", __name__)

TABS = ("plan", "tasks", "claude", "instances", "about")


def _project_or_404(slug: str):
    try:
        return projects_core.by_slug(slug)
    except projects_core.ProjectNotFound:
        abort(404)


def _form(values, errors=None, project=None, status=200):
    return (
        render_template(
            "projects/form.html",
            values=values,
            errors=errors or {},
            project=project,
            colors=PROJECT_COLORS,
            statuses=[(status, status.capitalize()) for status in PROJECT_STATUSES],
        ),
        status,
    )


@projects.get("/projects")
def index():
    after = latest_event_id()
    page = projects_core.list_projects(request.args)
    # Two views (D-065): the graph, or the list as soon as it is asked for or filtered.
    graph_view = not request.args
    response = make_response(
        render_template(
            "projects/index.html",
            page=page,
            graph_view=graph_view,
            stats=projects_core.stats([p.id for p in page.items]),
            events_after=after,
        )
    )
    return with_graph_csp(response)  # the plan of projects is a graph (D-044)


@projects.get("/projects/new")
def new():
    return _form(
        {"status": "active", "color": "slate", "icon": "fa-folder", "default_branch": "main", "weight": "1"}
    )


@projects.post("/projects/new")
def create():
    try:
        with batch() as batch_id:
            project = projects_core.create(validate(ProjectCreate, values_from_form(request.form)))
    except FormErrors as exc:
        return _form(request.form, exc.errors, status=422)
    flash_undo(f"Created the project “{project.name}”.", batch_id)
    return redirect(url_for("projects.detail", slug=project.slug))


@projects.get("/projects/<slug>")
def detail(slug: str):
    after = latest_event_id()
    project = _project_or_404(slug)
    page = tasks_core.list_tasks(request.args, project_id=project.id)
    # Three tabs (D-045): the plan (its graph), the tasks (the list), about (description,
    # resources, discussion). A list search, filter, sort or page lands on the tasks.
    tab = request.args.get("tab")
    if tab not in TABS:
        listing = page.has_filters or any(
            k in request.args for k in ("page", "sort", "dir", "view", "per_page")
        )
        tab = "tasks" if listing else "plan"
    outside = found_core.for_project(project)
    response = make_response(
        render_template(
            "projects/detail.html",
            project=project,
            page=page,
            tab=tab,
            links=project_links_core.for_project(project.id),
            claude=claude_core.overview(project_id=project.id) if tab == "claude" else None,
            instances=instances_core.for_project(project.id) if tab == "instances" else None,
            outside=outside,
            instances_running=instances_core.running_count(project.id) + len(outside),
            **graph_view(request.args, project=project),
            stats=projects_core.stats([project.id])[project.id],
            next_up=tasks_core.next_actions(limit=3, project_id=project.id),
            events_after=after,
            resources=resources_core.for_target("project", project.id),
            comments=comments_core.for_target("project", project.id),
            max_mb=get_setting("resources.max_upload_mb"),
            **list_context(),
        )
    )
    return with_graph_csp(response)


@projects.get("/projects/<slug>/edit")
def edit(slug: str):
    project = _project_or_404(slug)
    return _form(values_from_project(project), project=project)


@projects.post("/projects/<slug>/edit")
def save(slug: str):
    project = _project_or_404(slug)
    try:
        with batch() as batch_id:
            projects_core.update(project.id, validate(ProjectUpdate, values_from_form(request.form)))
    except FormErrors as exc:
        return _form(request.form, exc.errors, project, status=422)
    except projects_core.ProjectError as exc:
        return _form(request.form, {"slug": str(exc)}, project, status=422)
    flash_undo("Saved.", batch_id)
    return redirect(url_for("projects.detail", slug=project.slug))


@projects.post("/projects/<slug>/delete")
def delete(slug: str):
    project = _project_or_404(slug)
    with batch() as batch_id:
        moved = projects_core.delete(project.id)
    flash_undo(
        f"“{project.name}” and its {moved} task{'s' if moved != 1 else ''} moved to the trash.", batch_id
    )
    return redirect(url_for("projects.index"))
