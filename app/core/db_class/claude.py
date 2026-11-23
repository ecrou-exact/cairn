"""Claude Code sessions run by Cairn in a terminal (D-050).

The terminal itself lives in the web process (`features/claude/terminal_core.py`); this
row keeps where it ran, its Claude Code session id (which names its transcript), and how
it ended, for the Claude overview and the history.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime

SESSION_STATUSES = ("running", "ended")
SESSION_KINDS = ("claude", "instance", "log")


class ProjectInstance(BaseEntity):
    """A command that runs a project (D-053): its dev server, a worker, tests in watch mode…
    Started from Cairn in a terminal, in the project's folder (or a subfolder of it)."""

    __tablename__ = "project_instance"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    command: Mapped[str] = mapped_column(String(1000), nullable=False)
    subfolder: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    port: Mapped[int | None] = mapped_column(Integer)
    # Started again once per session of the machine (D-073)
    autostart: Mapped[bool] = mapped_column(default=False, server_default=false(), nullable=False)


class ClaudeSession(BaseEntity):
    """A terminal Cairn runs (D-050, D-053): Claude Code (`kind` claude) a project's
    instance (`kind` instance), or a log being followed (`kind` log, D-061)."""

    __tablename__ = "claude_session"

    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project.id"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("task.id"), index=True)
    cwd: Mapped[str] = mapped_column(String(500), nullable=False)
    # Not unique: a conversation resumed in Cairn gets a new session row with the same id.
    cli_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="running", nullable=False, index=True)
    kind: Mapped[str] = mapped_column(
        String(10), default="claude", server_default="claude", nullable=False, index=True
    )
    instance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project_instance.id"), index=True)
    port: Mapped[int | None] = mapped_column(Integer)  # the port given to an instance (PORT)
    pid: Mapped[int | None] = mapped_column(Integer)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    end_reason: Mapped[str] = mapped_column(String(200), default="", nullable=False)


class ClaudeRequest(BaseEntity):
    """The main Claude asking for a project's Claude to be opened with some work (D-068): written
    by its MCP server, answered by the web process, where terminals live."""

    __tablename__ = "claude_request"

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("project.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("task.id"))
    work: Mapped[str] = mapped_column(Text, nullable=False)
    # pending, opening, opened, refused
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claude_session.id"))
    error: Mapped[str] = mapped_column(String(300), default="", nullable=False)
