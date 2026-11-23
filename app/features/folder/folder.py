"""A project's copies on the machine, and what Cairn can take from its folder (D-081)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.jobs import jobs_core
from app.core.schema.folder import BringInput, DiscoverMake
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, local_path, validate
from app.features.changesets.changesets_core import ChangesetError
from app.features.folder import copies_core, discover_core, git_core, scan_core
from app.features.instances.instances_core import InstanceError
from app.features.projects import projects_core
from app.features.resources.resources_core import ResourceError

folder = Blueprint("folder", __name__)


def _project(slug: str):
    try:
        return projects_core.by_slug(slug)
    except projects_core.ProjectNotFound:
        abort(404)


@folder.get("/projects/<slug>/copies")
def copies(slug: str):
    project = _project(slug)
    return render_template("folder/copies.html", project=project, found=copies_core.overview(project))


@folder.get("/projects/<slug>/bring")
def bring(slug: str):
    project = _project(slug)
    return render_template("folder/bring.html", project=project, found=scan_core.scan(project))


@folder.post("/projects/<slug>/bring")
def take(slug: str):
    project = _project(slug)
    try:
        taken = scan_core.bring(project, validate(BringInput, {"keys": request.form.getlist("keys")}).keys)
    except FormErrors:
        flash("Choose at least one thing.", "warning")
        return redirect(url_for("folder.bring", slug=slug))
    except (scan_core.ScanError, ChangesetError, ResourceError, InstanceError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("folder.bring", slug=slug))
    added = [
        f"{n} {word}{'s' if n != 1 else ''}"
        for n, word in ((taken["skills"], "skill"), (taken["commands"], "command"))
        if n
    ]
    if added:
        flash(f"Added {' and '.join(added)}.", "success")
    if taken["changeset"] is not None:
        return redirect(url_for("changesets.detail", changeset_id=taken["changeset"].id))
    return redirect(url_for("folder.bring", slug=slug))


@folder.post("/projects/<slug>/git/<any(fetch, pull):action>")
def git_action(slug: str, action: str):
    project = _project(slug)
    back = local_path(request.form.get("next")) or url_for("projects.detail", slug=slug, tab="git")
    try:
        said = git_core.act(project, request.form.get("folder", ""), action)
    except git_core.GitError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"{action.capitalize()}: {said.splitlines()[-1][:200]}", "success")
    return redirect(back)


@folder.post("/projects/<slug>/git/task")
def git_task(slug: str):
    project = _project(slug)
    try:
        with batch() as batch_id:
            task = git_core.task_from_copy(project, request.form.get("folder", ""))
    except git_core.GitError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("projects.detail", slug=slug, tab="git"))
    flash_undo(f"Task made: {task.title}.", batch_id)
    return redirect(url_for("tasks.detail", task_id=task.id, tab="git"))


# -- every project of the machine (D-088) ------------------------------------------------------------


@folder.get("/projects/discover")
def discover():
    found, made = discover_core.last(discover_core.FIND), discover_core.last(discover_core.MAKE)
    return render_template("folder/discover.html", found=found, made=made, roots=discover_core._roots())


@folder.post("/projects/discover")
def discover_start():
    jobs_core.enqueue(discover_core.FIND, {}, title="Look for my projects")
    return redirect(url_for("folder.discover"))


@folder.post("/projects/discover/make")
def discover_make():
    try:
        keys = validate(DiscoverMake, {"keys": request.form.getlist("keys")}).keys
    except FormErrors:
        flash("Choose at least one project.", "warning")
        return redirect(url_for("folder.discover"))
    jobs_core.enqueue(discover_core.MAKE, {"keys": keys}, title=f"Start {len(keys)} projects")
    return redirect(url_for("folder.discover"))
