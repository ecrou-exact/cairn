"""What was done in a day, and the time entries made from it (D-078)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity, UTCDateTime


class WorkTarget(BaseEntity):
    """Where the work of some repositories is logged: a project and an activity in Kimai."""

    __tablename__ = "work_target"

    label: Mapped[str] = mapped_column(String(80), nullable=False)
    repos: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)  # names, lower case
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guidance: Mapped[str] = mapped_column(Text, default="", nullable=False)  # what goes here, for Claude
    about: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    kimai_project: Mapped[int] = mapped_column(Integer, nullable=False)
    project_label: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    kimai_activity: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_label: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class WorkDay(BaseEntity):
    """The facts of one day as they were read, and the summary written from them."""

    __tablename__ = "work_day"
    __table_args__ = (UniqueConstraint("day"),)

    day: Mapped[date] = mapped_column(Date, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    summary_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DayEntry(BaseEntity):
    """One line of a day's time: a draft in Cairn until the owner sends it."""

    __tablename__ = "day_entry"

    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    begin: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM, local time
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("work_target.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    kimai_id: Mapped[int | None] = mapped_column(Integer)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
