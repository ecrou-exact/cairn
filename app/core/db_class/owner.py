"""The single owner account (Cairn is single-owner by design, §11)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime


class Owner(BaseEntity):
    __tablename__ = "owner"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    totp_last_step: Mapped[int | None] = mapped_column(default=None)
    # Bumped on password change / "sign out everywhere": old sessions stop working.
    session_version: Mapped[int] = mapped_column(default=1, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    theme: Mapped[str] = mapped_column(String(32), default="auto", nullable=False)
    # Profile. Kept on the owner while Cairn is single-user; moves to a user table with the
    # same fields when collaborators arrive (D-034).
    display_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    bio: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    avatar_name: Mapped[str | None] = mapped_column(String(64))  # stored file (storage_core)

    @property
    def shown_name(self) -> str:
        return self.display_name or self.username

    @property
    def initials(self) -> str:
        parts = self.shown_name.replace("_", " ").replace(".", " ").split()
        letters = "".join(part[0] for part in parts[:2]) or self.username[:1]
        return letters.upper()

    # Flask-Login interface. Written out instead of UserMixin, whose __eq__ (comparing get_id())
    # interferes with SQLAlchemy's identity map and recursed into attribute loading.
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def get_id(self) -> str:
        """Session identifier; includes session_version so bumping it signs out old sessions."""
        return f"{self.id}:{self.session_version}"
