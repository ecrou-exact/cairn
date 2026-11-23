"""Inputs for project instances (D-053)."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import Field

from app.core.schema.common import Strict


class InstanceCreate(Strict):
    """A command that runs the project, e.g. `npm run dev` on port 5173."""

    project_id: uuid.UUID
    name: Annotated[str, Field(min_length=1, max_length=80)]
    command: Annotated[str, Field(min_length=1, max_length=1000)]
    subfolder: Annotated[str, Field(max_length=300)] = ""
    port: Annotated[int, Field(ge=1, le=65535)] | None = None


class LogOpen(Strict):
    """Follow a log of an instance found outside Cairn: its key, as listed."""

    project_id: uuid.UUID
    key: Annotated[str, Field(min_length=1, max_length=1000)]


class InstanceStart(Strict):
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32
