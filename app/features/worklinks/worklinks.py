"""Work linked from the task and project pages (D-083)."""

from __future__ import annotations

import uuid

from flask import Blueprint, flash, redirect, request

from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, local_path, validate
from app.features.worklinks import worklinks_core

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
