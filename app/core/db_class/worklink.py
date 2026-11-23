"""Work linked to a project, a task or a subtask (D-083): a branch, a commit, a pull request, a
Claude conversation or a folder, so that the next Claude on it starts with the real context."""

from __future__ import annotations

import uuid

from sqlalchemy import Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity

WORK_KINDS = ("branch", "commit", "pull", "claude", "folder")
WORK_TARGETS = ("project", "task")


class WorkLink(BaseEntity):
    __tablename__ = "work_link"
    __table_args__ = (Index("ix_work_link_target", "target_type", "target_id"),)

    target_type: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    ref: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # a name, a sha, owner/name#n, an id, a path
    note: Mapped[str] = mapped_column(String(500), default="", nullable=False)
