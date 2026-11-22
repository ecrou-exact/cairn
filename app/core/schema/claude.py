"""Inputs for Claude Code sessions in a terminal (D-050)."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import Field, model_validator

from app.core.schema.common import Strict


class SessionStart(Strict):
    """Where to open Claude Code: a project (its local path) or a task (its project's path).
    `with_brief` starts on the task, with its brief as the first message."""

    project_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    with_brief: bool = False
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32

    @model_validator(mode="after")
    def _where(self) -> SessionStart:
        if (self.project_id is None) == (self.task_id is None):
            raise ValueError("give a project or a task")
        if self.with_brief and self.task_id is None:
            raise ValueError("a brief needs a task")
        return self


class TerminalInput(Strict):
    """Keys typed in the terminal (as the terminal encodes them)."""

    data: Annotated[str, Field(min_length=1, max_length=65536)]


class TerminalResize(Strict):
    cols: Annotated[int, Field(ge=20, le=500)]
    rows: Annotated[int, Field(ge=5, le=200)]
