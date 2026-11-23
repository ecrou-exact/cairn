"""Project pages: list (cards or table), project page with its tasks, form, delete."""

from __future__ import annotations

import re
import uuid
from pathlib import Path, PurePath

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from app.core.db_class.planning import PROJECT_COLORS, PROJECT_STATUSES
from app.core.schema.planning import ProjectCreate, ProjectUpdate
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.settings import get_setting
from app.core.utils.web import FormErrors, back_to, flash_undo, local_path, validate
from app.features.changesets import changesets_core
from app.features.claude import claude_core, worktrees_core
from app.features.comments import comments_core
from app.features.folder import git_core
from app.features.graph.graph import graph_view, with_graph_csp
from app.features.instances import found_core, instances_core
from app.features.projects import open_core, project_links_core, projects_core, transfer_core
from app.features.projects.projects_forms import values_from_form, values_from_project
from app.features.resources import resources_core, storage_core
from app.features.resources.storage_core import StorageError
from app.features.tasks import tasks_core
from app.features.tasks.tasks import list_context
from app.features.worklinks import worklinks_core

projects = Blueprint("projects", __name__)

TABS = ("plan", "tasks", "git", "claude", "instances", "about")


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


def _picture(project) -> None:
    """The picture sent with the form, or its removal; a refused one leaves the rest saved."""
    picture = request.files.get("image")
    try:
        if picture is not None and picture.filename:
            projects_core.set_image(project.id, picture.stream)
        elif request.form.get("remove_image") == "1":
            projects_core.remove_image(project.id)
    except StorageError as exc:
        flash(f"The picture was not kept: {exc}", "danger")


@projects.get("/projects")
def index():
    after = latest_event_id()
    page = projects_core.list_projects(request.args)
    graph_view = request.args.get("mode") == "graph"  # two views (D-065): cards first, or the graph
    response = make_response(
        render_template(
            "projects/index.html",
            page=page,
            graph_view=graph_view,
            stats=projects_core.stats([p.id for p in page.items]),
            hidden_view=request.args.get("hidden") == "1",
            hidden_count=projects_core.hidden_count(),
            events_after=after,
        )
    )
    return with_graph_csp(response)  # the plan of projects is a graph (D-044)


@projects.get("/projects/new")
def new():
    values = {
        "status": "active",
        "color": "slate",
        "icon": "fa-folder",
        "default_branch": "main",
        "weight": "1",
    }
    if folder := request.args.get("folder", "")[:500]:
        values |= {"local_path": folder, "name": PurePath(folder).name}
    return _form(values)


@projects.post("/projects/new")
def create():
    try:
        with batch() as batch_id:
            project = projects_core.create(validate(ProjectCreate, values_from_form(request.form)))
    except FormErrors as exc:
        return _form(request.form, exc.errors, status=422)
    flash_undo(f"Created the project “{project.name}”.", batch_id)
    _picture(project)
    if project.local_path or project.github_repo:
        return redirect(url_for("folder.bring", slug=project.slug))
    return redirect(url_for("projects.detail", slug=project.slug))


# -- from one machine to another (D-084) ---------------------------------------------------------


def _waiting(token: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", token or ""):
        abort(404)
    folder = Path(current_app.config["CAIRN_DATA_DIR"]) / "imports"
    folder.mkdir(mode=0o700, exist_ok=True)
    return folder / f"{token}.cairn"


@projects.get("/projects/<slug>/export")
def export(slug: str):
    project = _project_or_404(slug)
    name = transfer_core.file_name(project)
    return Response(
        transfer_core.export(project),
        mimetype="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )


@projects.post("/projects/<slug>/export/save")
def export_save(slug: str):
    project = _project_or_404(slug)
    try:
        path = transfer_core.save(project)
    except (transfer_core.TransferError, OSError) as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Saved in the exchange folder: {path.name}. Import it on the other machine.", "success")
    return redirect(url_for("projects.detail", slug=slug))


@projects.get("/projects/import")
def import_form():
    return render_template(
        "projects/import.html",
        found=None,
        folder=transfer_core.exchange_folder(),
        files=transfer_core.waiting_files(),
    )


@projects.post("/projects/import")
def import_preview():
    sent = request.files.get("file")
    try:
        if request.form.get("name"):
            blob = transfer_core.from_folder(request.form["name"])
        else:
            blob = sent.read() if sent else b""
            if not blob:
                flash("Choose a file exported by Cairn.", "warning")
                return redirect(url_for("projects.import_form"))
        found = transfer_core.preview(blob)
    except transfer_core.TransferError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("projects.import_form"))
    token = uuid.uuid4().hex
    _waiting(token).write_bytes(blob)
    return render_template("projects/import.html", found=found, token=token)


@projects.post("/projects/import/<token>")
def import_apply(token: str):
    path = _waiting(token)
    if not path.exists():
        flash("This import is no longer waiting: choose the file again.", "warning")
        return redirect(url_for("projects.import_form"))
    folder = (request.form.get("folder") or "").strip() or None
    try:
        project, _ = transfer_core.bring(path.read_bytes(), folder)
    except transfer_core.TransferError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("projects.import_form"))
    path.unlink(missing_ok=True)
    flash(f"“{project.name}” is up to date with the file.", "success")
    return redirect(url_for("projects.detail", slug=project.slug))


BULK = {
    "star": ("starred", True), "unstar": ("starred", False),
    "pin": ("pinned", True), "unpin": ("pinned", False),
    "hide": ("hidden", True), "show": ("hidden", False),
}  # fmt: skip


@projects.post("/projects/bulk")
def bulk():
    """Star, pin or hide the chosen projects, and back (D-089). The page does it in place with the API."""
    field, value = BULK.get(request.form.get("action", ""), (None, None))
    chosen = request.form.getlist("project_ids")[:500]
    if field is None or not chosen:
        flash("Choose projects and what to do.", "warning")
        return redirect(back_to(url_for("projects.index")))
    try:
        ids = [uuid.UUID(raw) for raw in chosen]
    except ValueError:
        abort(400)
    with batch() as batch_id:
        for project_id in ids:
            projects_core.update(project_id, ProjectUpdate(**{field: value}))
    flash_undo(f"{len(ids)} project{'s' if len(ids) != 1 else ''} changed.", batch_id)
    return redirect(back_to(url_for("projects.index")))


@projects.post("/projects/<slug>/<any(star, pin, hide):mark>")
def mark(slug: str, mark: str):
    """Star (first in the list), pin (in the menu) or hide (out of the list), and back (D-089)."""
    project = _project_or_404(slug)
    field = {"star": "starred", "pin": "pinned", "hide": "hidden"}[mark]
    with batch() as batch_id:
        projects_core.update(project.id, ProjectUpdate(**{field: not getattr(project, field)}))
    on = getattr(project, field)
    told = {
        "starred": ("Starred", "Unstarred"),
        "pinned": ("Pinned in the menu", "Unpinned"),
        "hidden": ("Hidden from the list", "Back in the list"),
    }[field]
    flash_undo(f"{told[0] if on else told[1]}: {project.name}.", batch_id)
    return redirect(local_path(request.form.get("next")) or url_for("projects.detail", slug=slug))


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
            worktrees=worktrees_core.for_project(project.id) if tab == "claude" else None,
            instances=instances_core.for_project(project.id) if tab == "instances" else None,
            git=git_core.state(project) if tab == "git" else None,
            wanted_pull=request.args.get("pull", "")[:10] if tab == "git" else "",
            outside=outside,
            proposals=changesets_core.waiting(project.id),
            editor=get_setting("projects.editor"),
            instances_running=instances_core.running_count(project.id) + len(outside),
            **graph_view(request.args, project=project),
            stats=projects_core.stats([project.id])[project.id],
            next_up=tasks_core.next_actions(limit=3, project_id=project.id),
            events_after=after,
            resources=resources_core.for_target("project", project.id),
            work=worklinks_core.for_target("project", project.id) if tab == "about" else None,
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
    _picture(project)
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


@projects.get("/projects/<slug>/image")
def image(slug: str):
    return storage_core.serve_square(_project_or_404(slug).image_name) or abort(404)


@projects.post("/projects/<slug>/open/<any(files, editor):kind>")
def open_folder(slug: str, kind: str):
    """Open the project's folder on this machine (D-067)."""
    project = _project_or_404(slug)
    try:
        open_core.open_folder(project, kind)
    except projects_core.ProjectError as exc:
        flash(str(exc), "danger")
    return redirect(back_to(url_for("projects.detail", slug=project.slug)))
