"""Owner overrides of the settings shipped in `app/settings/<key>.json`.

The file is the default and is never rewritten (a `git pull` stays clean). An override
remembers the file value it was made from (`base_value`), so an update that changes the
default can be detected and shown to the owner.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity


class SettingOverride(BaseEntity):
    __tablename__ = "setting_override"

    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    base_value: Mapped[Any] = mapped_column(JSON, nullable=True)
