"""A project's copies on the machine, and what Cairn can take from its folder (D-081)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.schema.folder import BringInput
from app.core.utils.web import FormErrors, validate
from app.features.changesets.changesets_core import ChangesetError
from app.features.folder import copies_core, scan_core
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
