"""Work linked from the task and project pages (D-083)."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, local_path, validate
from app.features.projects import projects_core
from app.features.worklinks import github_work_core, worklinks_core

worklinks = Blueprint("worklinks", __name__)


def _back():
    return redirect(local_path(request.form.get("next")) or "/")


@worklinks.post("/work-links")
def add():
    values = {k: request.form.get(k, "") for k in ("target_type", "target_id", "kind", "ref", "note")}
    try:
        with batch() as batch_id:
            worklinks_core.add(validate(WorkLinkCreate, values))
    except FormErrors as exc:
        flash(" ".join(exc.errors.values()), "danger")
    except worklinks_core.WorkLinkError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Linked.", batch_id)
    return _back()


@worklinks.post("/work-links/<uuid:link_id>/delete")
def remove(link_id: uuid.UUID):
    try:
        with batch() as batch_id:
            worklinks_core.remove(link_id)
    except worklinks_core.WorkLinkError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Link removed.", batch_id)
    return _back()


# -- a task per pull request or issue (D-085) --------------------------------------------------------


@worklinks.get("/projects/<slug>/github")
def github(slug: str):
    try:
        project = projects_core.by_slug(slug)
    except projects_core.ProjectNotFound:
        abort(404)
    return render_template("worklinks/github.html", project=project, found=github_work_core.choices(project))


@worklinks.post("/projects/<slug>/github")
def make_tasks(slug: str):
    try:
        project = projects_core.by_slug(slug)
    except projects_core.ProjectNotFound:
        abort(404)
    try:
        with batch() as batch_id:
            made = github_work_core.make_tasks(project, request.form.getlist("refs")[:200])
    except github_work_core.GithubWorkError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("worklinks.github", slug=slug))
    flash_undo(f"{len(made)} task{'s' if len(made) != 1 else ''} made, each linked.", batch_id)
    return redirect(url_for("projects.detail", slug=slug, tab="tasks"))
