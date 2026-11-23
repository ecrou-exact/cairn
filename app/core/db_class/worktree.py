"""A git worktree Cairn made for a Claude (D-077): its own folder and branch of a project."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity


class Worktree(BaseEntity):
    __tablename__ = "worktree"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project.id"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("task.id"))
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    branch: Mapped[str] = mapped_column(String(120), nullable=False)
    base: Mapped[str] = mapped_column(String(100), default="", nullable=False)  # what it started from
