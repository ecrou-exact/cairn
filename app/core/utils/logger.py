"""`log_action()`: the one way to record a change or a sensitive action."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from flask import has_request_context, request

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.core.utils.actor import current_actor
from app.core.utils.history import current_batch

LEVELS = ("debug", "info", "warning", "error", "critical")
_log = logging.getLogger("cairn.activity")


def log_action(
    action: str,
    *,
    target_type: str | None = None,
    target_id: object | None = None,
    diff: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    level: str = "info",
    batch_id: uuid.UUID | None = None,
) -> Activity:
    """Add an activity row to the current session (committed with the change itself).

    `action` is dot-namespaced (`task.create`, `auth.login_failed`). `diff` maps a
    field to `[old, new]`. Secrets never go in `diff` or `meta`. Inside
    `history.batch()`, the row joins the current batch (undo, §2.10).
    """

    if level not in LEVELS:
        raise ValueError(f"Unknown level '{level}'.")
    entry = Activity(
        action=action,
        level=level,
        actor=current_actor(),
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        diff=diff,
        meta=meta,
        batch_id=batch_id or current_batch(),
    )
    if has_request_context():
        entry.ip = request.remote_addr
        entry.user_agent = (request.user_agent.string or "")[:255]
    db.session.add(entry)
    _log.info("%s by %s on %s:%s", action, entry.actor, target_type, entry.target_id)
    return entry
