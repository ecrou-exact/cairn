"""Comments and corrections: inputs and outputs shared by forms, API and MCP tools."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from app.core.db_class.comment import COMMENT_KINDS, COMMENT_TARGETS
from app.core.schema.common import Output, Strict

CommentBody = Annotated[str, Field(min_length=1, max_length=50_000)]


class CommentCreate(Strict):
    target_type: Literal[COMMENT_TARGETS]  # type: ignore[valid-type]
    target_id: uuid.UUID
    kind: Literal[COMMENT_KINDS] = "comment"  # type: ignore[valid-type]
    body_md: CommentBody


class CommentUpdate(Strict):
    body_md: CommentBody | None = None
    kind: Literal[COMMENT_KINDS] | None = None  # type: ignore[valid-type]
    active: bool | None = None


class CommentOut(Output):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    kind: str
    body_md: str
    active: bool
    created_at: datetime
    edited_at: datetime | None
    created_by: str
