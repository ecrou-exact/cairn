"""Undo from the page that showed the change."""

from __future__ import annotations

import uuid

from flask import Blueprint, flash, redirect, request, url_for

from app.core.utils import history as history_core
from app.core.utils.web import flash_undo

history = Blueprint("history", __name__)


def _back() -> str:
    target = request.form.get("next") or ""
    if target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target.rstrip("?")
    return url_for("home.index")


@history.post("/history/<uuid:batch_id>/undo")
def undo(batch_id: uuid.UUID):
    try:
        redo_batch = history_core.undo(batch_id)
    except (history_core.UndoError, ValueError) as exc:
        flash(f"Could not undo: {exc}", "danger")
    else:
        flash_undo("Change undone.", redo_batch)
    return redirect(_back())
