"""Activity log: one row per change or sensitive action.

It is at the same time the audit log (§11), the entity history used for undo
(§2.10, `diff` + `batch_id`) and the source of the activity feed (§6.9).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import UTCDateTime, utcnow
from app.core.extensions import db


class Activity(db.Model):
    __tablename__ = "activity"
    __table_args__ = (
        Index("ix_activity_target", "target_type", "target_id"),
        Index("ix_activity_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(10), default="info", nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(64))
    diff: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
