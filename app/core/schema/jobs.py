"""Jobs as the API and MCP tools read and start them."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.schema.common import Output, Strict


class JobStart(Strict):
    type: str = Field(min_length=3, max_length=80, pattern=r"^[a-z][a-z_]*(\.[a-z_]+)+$")


class JobSummary(Output):
    id: uuid.UUID
    type: str
    lane: str
    title: str
    status: str
    progress: int
    attempts: int
    max_attempts: int
    error: str | None
    cancel_requested: bool
    created_at: datetime
    run_after: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobDetail(JobSummary):
    payload: dict[str, Any]
    result: dict[str, Any] | None
    log: str
    timeout_seconds: int
    created_by: str
