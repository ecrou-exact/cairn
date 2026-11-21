"""Resources and the resource library (PROJECT_BRIEF.md §2.4).

A resource lives once in the library and is attached to any number of projects and tasks
through `ResourceLink`, so the same link, file or snippet is never copied around.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity

RESOURCE_KINDS = ("url", "file", "image", "snippet", "tool", "note", "github")
LINK_TARGETS = ("project", "task")


class Resource(BaseEntity):
    __tablename__ = "resource"

    kind: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    url: Mapped[str | None] = mapped_column(String(2000))  # url, tool, github
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)  # note, snippet, tool command
    language: Mapped[str] = mapped_column(String(30), default="", nullable=False)  # snippet highlighting
    path: Mapped[str | None] = mapped_column(String(500))  # file reference on disk or in a repository
    icon: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Uploaded file (kinds file and image), stored under a random name (storage_core).
    stored_name: Mapped[str | None] = mapped_column(String(64), unique=True)
    original_name: Mapped[str | None] = mapped_column(String(255))
    mime: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)

    # Facts found by Cairn, never typed by the owner: page preview, GitHub reference,
    # image size. Shown as hints, overwritten by the next fetch.
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    @property
    def has_file(self) -> bool:
        return self.stored_name is not None


class ResourceLink(BaseEntity):
    """A resource attached to a project or a task (`target_type`, `target_id`)."""

    __tablename__ = "resource_link"
    __table_args__ = (UniqueConstraint("resource_id", "target_type", "target_id", name="uq_resource_link"),)

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resource.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)
