"""Changes Claude proposes together, approved by the owner one by one (D-071)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity

CHANGESET_STATUSES = ("proposed", "applied", "dismissed")


class Changeset(BaseEntity):
    __tablename__ = "changeset"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reason_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="proposed", nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project.id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claude_session.id"))
    # Each as `ChangeItem` (core/schema/changesets.py); once applied, with `kept` and `target`.
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # what it changed, to undo it
