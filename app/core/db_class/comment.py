"""Comments and the corrections log (PROJECT_BRIEF.md §2.2).

A comment is a Markdown note on a task or a project, from the owner or Claude. A
correction is a comment of kind `correction`: owner feedback on how the work must be
done. Active corrections of a task, its parent tasks and its project are given to every
later Claude run on that task (see `tasks/brief_core.py`).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime

COMMENT_KINDS = ("comment", "correction")
COMMENT_TARGETS = ("project", "task")


class Comment(BaseEntity):
    __tablename__ = "comment"
    __table_args__ = (Index("ix_comment_target", "target_type", "target_id"),)

    target_type: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), default="comment", nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    # A correction stops being given to Claude once retired; it stays in the log.
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
