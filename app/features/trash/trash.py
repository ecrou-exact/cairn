"""The trash: what was deleted, restore it, or delete it for good (the only hard delete)."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, url_for

from app.core.utils.history import batch
from app.core.utils.web import flash_undo
from app.features.comments import comments_core
from app.features.projects import projects_core
from app.features.resources import resources_core
from app.features.tasks import tasks_core

trash = Blueprint("trash", __name__)

CORES = {
    "tasks": tasks_core,
    "projects": projects_core,
    "resources": resources_core,
    "comments": comments_core,
}
ERRORS = (
    tasks_core.TaskError,
    projects_core.ProjectError,
    resources_core.ResourceError,
    comments_core.CommentError,
)
NOT_FOUND = (
    tasks_core.TaskNotFound,
    projects_core.ProjectNotFound,
    resources_core.ResourceNotFound,
    comments_core.CommentNotFound,
)


@trash.get("/trash")
def index():
    return render_template(
        "trash/index.html",
        tasks=tasks_core.deleted_tasks(),
        projects=projects_core.deleted_projects(),
        resources=resources_core.deleted_resources(),
        comments=comments_core.deleted_comments(),
    )


@trash.post("/trash/<kind>/<uuid:item_id>/restore")
def restore(kind: str, item_id: uuid.UUID):
    core = CORES.get(kind) or abort(404)
    try:
        with batch() as batch_id:
            core.restore(item_id)
    except NOT_FOUND:
        abort(404)
    except ERRORS as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Restored.", batch_id)
    return redirect(url_for("trash.index"))


@trash.post("/trash/<kind>/<uuid:item_id>/purge")
def purge(kind: str, item_id: uuid.UUID):
    core = CORES.get(kind) or abort(404)
    try:
        core.purge(item_id)
    except NOT_FOUND:
        abort(404)
    except ERRORS as exc:
        flash(str(exc), "danger")
    else:
        flash("Deleted for good.", "warning")
    return redirect(url_for("trash.index"))
