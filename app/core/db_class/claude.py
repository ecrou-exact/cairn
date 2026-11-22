"""Claude Code sessions run by Cairn in a terminal (D-050).

The terminal itself lives in the web process (`features/claude/terminal_core.py`); this
row keeps where it ran, its Claude Code session id (which names its transcript), and how
it ended, for the Claude overview and the history.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime

SESSION_STATUSES = ("running", "ended")


class ClaudeSession(BaseEntity):
    __tablename__ = "claude_session"

    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project.id"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("task.id"), index=True)
    cwd: Mapped[str] = mapped_column(String(500), nullable=False)
    cli_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="running", nullable=False, index=True)
    pid: Mapped[int | None] = mapped_column(Integer)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    end_reason: Mapped[str] = mapped_column(String(200), default="", nullable=False)
