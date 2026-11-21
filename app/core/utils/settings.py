"""Settings: defaults in `app/settings/<key>.json`, owner overrides in the database.

File format::

    {"label": "...", "category": "...", "description": "...", "value": <any JSON>}

Code reads a value with `get_setting("jobs.retention_days")`. Every setting has a
pydantic type in `app/core/schema/settings.py` (`SETTING_TYPES`); an override must fit it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from itertools import groupby
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from app.core.db_class.setting import SettingOverride
from app.core.extensions import db
from app.core.schema.settings import SETTING_TYPES
from app.core.utils.events import publish
from app.core.utils.logger import log_action

SETTINGS_DIR = Path(__file__).resolve().parent.parent.parent / "settings"
_KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")


class SettingError(ValueError):
    pass


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    label: str
    category: str
    description: str
    default: Any


@dataclass(frozen=True)
class SettingState:
    definition: SettingDefinition
    value: Any
    overridden: bool
    default_changed: bool  # the shipped default moved since the owner's override


@cache
def definitions() -> dict[str, SettingDefinition]:
    found: dict[str, SettingDefinition] = {}
    for path in sorted(SETTINGS_DIR.glob("*.json")):
        key = path.stem
        if not _KEY.match(key):
            raise SettingError(f"Invalid setting file name: {path.name}")
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = {"label", "category", "description", "value"} - data.keys()
        if missing:
            raise SettingError(f"{path.name} is missing {', '.join(sorted(missing))}")
        found[key] = SettingDefinition(
            key, data["label"], data["category"], data["description"], data["value"]
        )
    return found


def _definition(key: str) -> SettingDefinition:
    try:
        return definitions()[key]
    except KeyError as exc:
        raise SettingError(f"Unknown setting '{key}'.") from exc


def _override(key: str) -> SettingOverride | None:
    return db.session.scalar(select(SettingOverride).where(SettingOverride.key == key))


def get_setting(key: str) -> Any:
    definition = _definition(key)
    row = _override(key)
    return row.value if row is not None else definition.default


def setting_state(key: str) -> SettingState:
    definition = _definition(key)
    row = _override(key)
    if row is None:
        return SettingState(definition, definition.default, False, False)
    return SettingState(definition, row.value, True, row.base_value != definition.default)


def all_settings() -> list[SettingState]:
    return [setting_state(key) for key in definitions()]


def grouped_settings() -> list[tuple[str, list[SettingState]]]:
    """Every setting by category, both sorted, as the Settings page shows them."""
    states = sorted(all_settings(), key=lambda s: (s.definition.category, s.definition.label))
    return [
        (category, list(items)) for category, items in groupby(states, key=lambda s: s.definition.category)
    ]


def validate_value(key: str, value: Any) -> Any:
    """The value in its stored (JSON) form, or SettingError with a readable reason."""
    definition = _definition(key)
    adapter = SETTING_TYPES.get(key)
    if adapter is None:
        raise SettingError(f"'{definition.label}' cannot be changed.")
    try:
        return adapter.dump_python(adapter.validate_python(value), mode="json")
    except ValidationError as exc:
        reasons = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'value'}: {err['msg']}" for err in exc.errors()
        )
        raise SettingError(f"'{definition.label}' is not valid ({reasons}).") from exc


def set_setting(key: str, value: Any) -> SettingState:
    definition = _definition(key)
    value = validate_value(key, value)
    row = _override(key)
    old = row.value if row else definition.default
    if row is None:
        row = SettingOverride(key=key, value=value, base_value=definition.default)
        db.session.add(row)
    else:
        row.value, row.base_value = value, definition.default
    log_action("setting.update", target_type="setting", target_id=key, diff={"value": [old, value]})
    publish("setting.changed", {"key": key})
    db.session.commit()
    return setting_state(key)


def reset_setting(key: str) -> SettingState:
    definition = _definition(key)
    row = _override(key)
    if row is not None:
        log_action(
            "setting.reset",
            target_type="setting",
            target_id=key,
            diff={"value": [row.value, definition.default]},
        )
        db.session.delete(row)
        publish("setting.changed", {"key": key})
        db.session.commit()
    return setting_state(key)
