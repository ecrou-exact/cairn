"""Proposals of changes: the list, the review page, the answer (D-071)."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.schema.changesets import ChangesetApply
from app.core.utils.events import latest_event_id
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, validate
from app.features.changesets import changesets_core

changesets = Blueprint("changesets", __name__)


@changesets.get("/changesets")
def index():
    after = latest_event_id()
    return render_template(
        "changesets/index.html", page=changesets_core.list_changesets(request.args), events_after=after
    )


@changesets.get("/changesets/<uuid:changeset_id>")
def detail(changeset_id: uuid.UUID):
    after = latest_event_id()
    try:
        changeset = changesets_core.get(changeset_id)
    except changesets_core.ChangesetError:
        abort(404)
    return render_template(
        "changesets/detail.html", changeset=changesets_core.describe(changeset), events_after=after
    )


@changesets.post("/changesets/<uuid:changeset_id>/apply")
def apply(changeset_id: uuid.UUID):
    back = redirect(url_for("changesets.detail", changeset_id=changeset_id))
    try:
        data = validate(ChangesetApply, {"keep": request.form.getlist("keep")})
        with batch() as batch_id:
            changeset = changesets_core.apply(changeset_id, data.keep)
    except FormErrors:
        flash("Keep at least one change, or dismiss the proposal.", "warning")
        return back
    except changesets_core.ChangesetError as exc:
        flash(str(exc), "danger")
        return back
    kept = sum(1 for item in changeset.items if item.get("kept"))
    flash_undo(f"{kept} change{'s' if kept != 1 else ''} applied.", batch_id)
    return back


@changesets.post("/changesets/<uuid:changeset_id>/dismiss")
def dismiss(changeset_id: uuid.UUID):
    try:
        with batch() as batch_id:
            changesets_core.dismiss(changeset_id)
    except changesets_core.ChangesetError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("changesets.index"))
    flash_undo("Proposal dismissed.", batch_id)
    return redirect(url_for("changesets.index"))
