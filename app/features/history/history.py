"""Undo from the page that showed the change."""

from __future__ import annotations

import uuid

from flask import Blueprint, flash, redirect, url_for

from app.core.utils import history as history_core
from app.core.utils.web import back_to, flash_undo

history = Blueprint("history", __name__)


@history.post("/history/<uuid:batch_id>/undo")
def undo(batch_id: uuid.UUID):
    try:
        redo_batch = history_core.undo(batch_id)
    except (history_core.UndoError, ValueError) as exc:
        flash(f"Could not undo: {exc}", "danger")
    else:
        flash_undo("Change undone.", redo_batch)
    return redirect(back_to(url_for("home.index")))
