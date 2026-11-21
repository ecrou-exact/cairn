"""Planning: projects, tasks, dependencies and time entries (PROJECT_BRIEF.md §2.1–2.3).

Configurable lists (statuses, workflow, types, score weights) live in settings
(`app/settings/tasks.*.json`); columns store their keys.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_class.base import BaseEntity, UTCDateTime

PROJECT_STATUSES = ("active", "paused", "archived")
PRIORITIES = ("critical", "high", "medium", "low")
DEPENDENCY_KINDS = ("blocks", "relates", "duplicates", "follows")
# Project colours are names of palette tokens (--cn-palette-<name> in tokens.css), never raw colours.
PROJECT_COLORS = ("terracotta", "moss", "slate", "plum", "ochre", "sea")


class Project(BaseEntity):
    __tablename__ = "project"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(20), default="slate", nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="fa-folder", nullable=False)
    github_repo: Mapped[str | None] = mapped_column(String(140))
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(500))
    stack: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    links: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    claude_instructions_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # project weight in the score

    tasks: Mapped[list[Task]] = relationship(back_populates="project", lazy="selectin", viewonly=True)


class Task(BaseEntity):
    __tablename__ = "task"
    __table_args__ = (Index("ix_task_open_score", "is_open", "score"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("project.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("task.id"), index=True)
    type: Mapped[str] = mapped_column(String(30), default="feature", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="todo", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium", nullable=False, index=True)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1–5
    urgency: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1–5
    start_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date, index=True)
    hard_deadline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    do_on: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    estimate_hours: Mapped[float | None] = mapped_column(Float)
    assignee: Mapped[str] = mapped_column(String(80), default="me", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    acceptance_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    claude_instructions_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # {"every", "unit", "anchor"} (recurrence_core); done → the next occurrence is created.
    recurrence: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    next_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

    # Derived, recomputed by tasks_core after every planning change (and daily): kept as
    # columns so lists can filter and sort on them in the database.
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocked_by_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unblocks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_explain: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    tracked_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[Project | None] = relationship(back_populates="tasks", lazy="joined")

    @property
    def is_blocked(self) -> bool:
        return self.blocked_by_count > 0

    @property
    def actual_hours(self) -> float:
        return round(self.tracked_seconds / 3600, 2)


class Dependency(BaseEntity):
    """`from_task` → `to_task`: for `blocks`, from_task must be done before to_task can start."""

    __tablename__ = "dependency"
    __table_args__ = (UniqueConstraint("from_task_id", "to_task_id", "kind", name="uq_dependency_edge"),)

    from_task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("task.id"), nullable=False, index=True)
    to_task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("task.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(12), default="blocks", nullable=False)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)


class TimeEntry(BaseEntity):
    """Time spent on a task: one open entry (ended_at NULL) at most, owner-wide."""

    __tablename__ = "time_entry"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("task.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)
