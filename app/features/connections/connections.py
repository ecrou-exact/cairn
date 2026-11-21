"""Connected accounts page: add a token, check it, make it the default, replace, remove."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.utils.events import latest_event_id
from app.features.connections import connections_core as core

connections = Blueprint("connections", __name__)


def _back():
    return redirect(url_for("connections.index"))


@connections.get("/connections")
def index():
    after = latest_event_id()
    return render_template(
        "connections/index.html",
        items=core.connections(),
        providers=core.PROVIDERS,
        chosen=request.args.get("provider", "claude_code"),
        events_after=after,
    )


@connections.post("/connections")
def add():
    provider = request.form.get("provider", "")
    if provider not in core.PROVIDERS:
        abort(400)
    try:
        connection = core.add(
            provider,
            request.form.get("label", ""),
            request.form.get("token", ""),
            request.form.get("path", ""),
        )
    except core.ConnectionError_ as exc:
        flash(str(exc), "danger")
        return redirect(url_for("connections.index", provider=provider))
    saved = "connected" if connection.provider == "claude_code" else "saved in the vault"
    checking = " Checking it now…" if connection.state == "checking" else ""
    flash(f"“{connection.label}” {saved}.{checking}", "success")
    return _back()


def _act(action, connection_id: uuid.UUID, message: str, *args):
    try:
        action(connection_id, *args)
    except core.ConnectionError_ as exc:
        flash(str(exc), "danger")
    else:
        flash(message, "success")
    return _back()


@connections.post("/connections/<uuid:connection_id>/check")
def check(connection_id: uuid.UUID):
    return _act(core.request_check, connection_id, "Checking it now…")


@connections.post("/connections/<uuid:connection_id>/default")
def make_default(connection_id: uuid.UUID):
    return _act(core.make_default, connection_id, "This account is now the default.")


@connections.post("/connections/<uuid:connection_id>/rename")
def rename(connection_id: uuid.UUID):
    return _act(core.rename, connection_id, "Renamed.", request.form.get("label", ""))


@connections.post("/connections/<uuid:connection_id>/token")
def replace_token(connection_id: uuid.UUID):
    return _act(
        core.replace_token, connection_id, "Token replaced. Checking it now…", request.form.get("token", "")
    )


@connections.post("/connections/<uuid:connection_id>/remove")
def remove(connection_id: uuid.UUID):
    return _act(core.remove, connection_id, "Account removed and its token erased from the vault.")
