"""Inputs for Claude Code sessions in a terminal (D-050)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.core.schema.common import Strict

PRESETS = ("free", "task", "pr", "fix", "review")


class SessionStart(Strict):
    """Where to open Claude Code — a project (its local path) or a task (its project's path) —
    and what for (`preset`): work freely, on the task (its brief), a pull request (`detail` is
    its URL), a bug (`detail` describes it), a review. `detail` is otherwise added as the owner's
    own words. `with_brief` is the task preset, kept for the task page's buttons."""

    project_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    preset: Literal[PRESETS] = "free"  # type: ignore[valid-type]
    detail: Annotated[str, Field(max_length=8000)] = ""
    with_brief: bool = False
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32

    @model_validator(mode="after")
    def _where(self) -> SessionStart:
        if (self.project_id is None) == (self.task_id is None):
            raise ValueError("give a project or a task")
        if self.with_brief:
            self.preset = "task"
        if self.preset == "task" and self.task_id is None:
            raise ValueError("pick the task to work on")
        if self.preset == "pr" and not self.detail.startswith(("https://", "http://")):
            raise ValueError("give the pull request's address (https://…)")
        if self.preset == "fix" and not self.detail:
            raise ValueError("describe the bug to fix")
        return self


class NewProjectStart(Strict):
    """A new project: its folder (created if missing or empty), then Claude Code in it to
    set it up from the owner's description."""

    name: Annotated[str, Field(min_length=1, max_length=120)]
    folder: Annotated[str, Field(min_length=3, max_length=500)]
    description: Annotated[str, Field(max_length=8000)] = ""
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32


class TerminalInput(Strict):
    """Keys typed in the terminal (as the terminal encodes them)."""

    data: Annotated[str, Field(min_length=1, max_length=65536)]


class TerminalResize(Strict):
    cols: Annotated[int, Field(ge=20, le=500)]
    rows: Annotated[int, Field(ge=5, le=200)]


class ResumeStart(Strict):
    """Reopen a Claude Code conversation in Cairn, in its own folder."""

    cli_session_id: uuid.UUID
    cwd: Annotated[str, Field(min_length=3, max_length=500)]
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32
