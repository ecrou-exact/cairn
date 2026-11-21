"""Connected accounts: GitHub, Anthropic (Claude) and other services Cairn may act with.

The token itself is in the vault (`Secret` named `connection:<id>`), never in this table;
the table keeps what Cairn learned when it checked the token (login, scopes) and its hint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime

CONNECTION_PROVIDERS = ("github", "anthropic", "other")
CONNECTION_STATES = ("unchecked", "checking", "ok", "failed")


class Connection(BaseEntity):
    __tablename__ = "connection"

    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    hint: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # last characters
    state: Mapped[str] = mapped_column(String(12), default="unchecked", nullable=False)
    identity: Mapped[str] = mapped_column(String(120), default="", nullable=False)  # login / org
    error: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)  # scopes, name…

    @property
    def secret_name(self) -> str:
        return f"connection:{self.id}"
