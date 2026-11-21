"""Settings page: appearance (theme) and every setting of app/settings/, with overrides and reset."""

from __future__ import annotations

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.utils import settings as settings_core
from app.features.account import account_core

settings = Blueprint("settings", __name__)


@settings.get("/settings")
def index():
    return render_template(
        "settings/index.html", groups=settings_core.grouped_settings(), themes=account_core.theme_choices()
    )


@settings.post("/settings/appearance")
def appearance():
    try:
        account_core.set_theme(current_user._get_current_object(), request.form.get("theme", ""))
    except account_core.AccountError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("settings.index"))


def _known(key: str) -> None:
    if key not in settings_core.definitions():
        abort(404)


@settings.post("/settings/<key>")
def update(key: str):
    _known(key)
    try:
        value = json.loads(request.form.get("value", ""))
    except json.JSONDecodeError as exc:
        flash(f"Not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).", "danger")
        return redirect(url_for("settings.index", _anchor=key))
    try:
        state = settings_core.set_setting(key, value)
    except settings_core.SettingError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"“{state.definition.label}” saved.", "success")
    return redirect(url_for("settings.index", _anchor=key))


@settings.post("/settings/<key>/reset")
def reset(key: str):
    _known(key)
    state = settings_core.reset_setting(key)
    flash(f"“{state.definition.label}” is back to its default.", "success")
    return redirect(url_for("settings.index", _anchor=key))
