"""Settings API: read every setting, change or reset one, choose the theme."""

from __future__ import annotations

from flask import jsonify
from flask_login import current_user

from app.api import ApiError, api_blueprint, body
from app.core.schema.settings import SettingOut, SettingUpdate, ThemeUpdate
from app.core.utils import settings as settings_core
from app.features.account import account_core

settings_api = api_blueprint("settings_api")


def _out(state) -> dict:
    return SettingOut.from_state(state).model_dump(mode="json")


def _state(action, key: str, *args):
    if key not in settings_core.definitions():
        raise ApiError("Unknown setting.", 404)
    try:
        return action(key, *args)
    except settings_core.SettingError as exc:
        raise ApiError(str(exc), 422) from exc


@settings_api.get("/settings")
def list_settings():
    return jsonify([_out(state) for state in settings_core.all_settings()])


@settings_api.get("/settings/<key>")
def get_setting(key: str):
    return jsonify(_out(_state(settings_core.setting_state, key)))


@settings_api.put("/settings/<key>")
def update_setting(key: str):
    data = body(SettingUpdate)
    return jsonify(_out(_state(settings_core.set_setting, key, data.value)))


@settings_api.delete("/settings/<key>")
def reset_setting(key: str):
    return jsonify(_out(_state(settings_core.reset_setting, key)))


@settings_api.put("/account/theme")
def update_theme():
    data = body(ThemeUpdate)
    try:
        account_core.set_theme(current_user._get_current_object(), data.theme)
    except account_core.AccountError as exc:
        raise ApiError(str(exc), 422) from exc
    return jsonify(theme=data.theme)
