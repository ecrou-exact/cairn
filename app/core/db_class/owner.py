"""The single owner account (Cairn is single-owner by design, §11)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity


class Owner(BaseEntity):
    __tablename__ = "owner"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    totp_last_step: Mapped[int | None] = mapped_column(default=None)
    # Bumped on password change / "sign out everywhere": old sessions stop working.
    session_version: Mapped[int] = mapped_column(default=1, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    theme: Mapped[str] = mapped_column(String(32), default="auto", nullable=False)

    # Flask-Login interface. Written out instead of UserMixin, whose __eq__ (comparing get_id())
    # interferes with SQLAlchemy's identity map and recursed into attribute loading.
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def get_id(self) -> str:
        """Session identifier; includes session_version so bumping it signs out old sessions."""
        return f"{self.id}:{self.session_version}"
