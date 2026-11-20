"""Columns shared by every Cairn entity (PROJECT_BRIEF.md §2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


class BaseEntity(db.Model):
    """UUID primary key, timestamps, author and soft delete.

    `created_by` is `user`, `claude:<run-id>` or `module:<id>`; it is filled by the
    core service that creates the row, from the current actor (see `app.core.utils.actor`).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(80), default="user", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
