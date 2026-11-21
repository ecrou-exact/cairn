"""Settings and appearance as the API reads and changes them."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, JsonValue, TypeAdapter

from app.core.schema.common import Strict


class SettingUpdate(Strict):
    value: JsonValue


class SettingOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    value: Any
    default: Any
    overridden: bool
    default_changed: bool

    @classmethod
    def from_state(cls, state) -> SettingOut:
        d = state.definition
        return cls(
            key=d.key,
            label=d.label,
            category=d.category,
            description=d.description,
            value=state.value,
            default=d.default,
            overridden=state.overridden,
            default_changed=state.default_changed,
        )


class ThemeUpdate(Strict):
    theme: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9-]*$")


class Lanes(Strict):
    """Every lane must stay: a lane left out would never run its jobs."""

    agent: int = Field(ge=1, le=16)
    io: int = Field(ge=1, le=32)
    module: int = Field(ge=1, le=16)
    system: int = Field(ge=1, le=4)


THEME_NAMES = Literal["auto", "stone", "basalt", "moss", "ember"]

# One type per settings file (checked by tests/test_settings.py). An override must fit it.
SETTING_TYPES: dict[str, TypeAdapter] = {
    "jobs.lanes": TypeAdapter(Lanes),
    "jobs.retention_days": TypeAdapter(Annotated[int, Field(strict=True, ge=1, le=3650)]),
    "lists.per_page": TypeAdapter(
        Annotated[list[Annotated[int, Field(strict=True, ge=5, le=500)]], Field(min_length=1, max_length=6)]
    ),
    "ui.themes": TypeAdapter(
        Annotated[dict[THEME_NAMES, Annotated[str, Field(min_length=1, max_length=60)]], Field(min_length=1)]
    ),
}
