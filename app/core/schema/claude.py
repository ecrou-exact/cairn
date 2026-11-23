"""Inputs for Claude Code sessions in a terminal (D-050)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from app.core.schema.common import Strict

PRESETS = ("free", "task", "pr", "fix", "review")


class SessionStart(Strict):
    """Where to open Claude Code — a project (its local path), a task (its project's path) or
    any folder, free of a project (it can be linked later) —
    and what for (`preset`): work freely, on the task (its brief), a pull request (`detail` is
    its URL), a bug (`detail` describes it), a review. `detail` is otherwise added as the owner's
    own words. `with_brief` is the task preset, kept for the task page's buttons."""

    project_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    folder: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    preset: Literal[PRESETS] = "free"  # type: ignore[valid-type]
    detail: Annotated[str, Field(max_length=8000)] = ""
    with_brief: bool = False
    worktree: bool | None = None  # its own folder and branch; None: as the settings say (tasks)
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32

    @model_validator(mode="after")
    def _where(self) -> SessionStart:
        if self.worktree and self.folder is not None:
            raise ValueError("a worktree is made for a project or a task")
        if sum(x is not None for x in (self.project_id, self.task_id, self.folder)) != 1:
            raise ValueError("give a project, a task or a folder")
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
    """A new project: its folder (created if missing), then Claude Code in it, to set it up
    from the owner's description or, when the folder has files, to read it."""

    name: Annotated[str, Field(min_length=1, max_length=120)]
    folder: Annotated[str, Field(min_length=3, max_length=500)]
    description: Annotated[str, Field(max_length=8000)] = ""
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32


class SessionLink(Strict):
    """Link a session to a project: one that exists, or a new one (`name`) for a folder (the
    session's by default), which Claude may `read`. Neither: the session is free again."""

    project_id: uuid.UUID | None = None
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    folder: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    read: bool = False

    @model_validator(mode="after")
    def _one(self) -> SessionLink:
        if self.project_id is not None and self.name is not None:
            raise ValueError("pick a project or name a new one, not both")
        return self


class CurrentPage(Strict):
    """The page in front of the owner, told by the dock."""

    path: Annotated[str, Field(min_length=1, max_length=500, pattern=r"^/([^/].*)?$")]
    title: Annotated[str, Field(max_length=300)] = ""


class OutsideStop(Strict):
    """A Claude Code running outside Cairn, to close or read it: its pid and start time, so that a reused pid
    is never taken for it."""

    pid: Annotated[int, Field(ge=2)]
    started: float


class TerminalInput(Strict):
    """Keys typed in the terminal, exactly as the terminal encodes them: Enter, Space and Tab
    are whitespace, so nothing is stripped here."""

    model_config = ConfigDict(str_strip_whitespace=False)

    data: Annotated[str, Field(min_length=1, max_length=65536)]


class TerminalResize(Strict):
    cols: Annotated[int, Field(ge=20, le=500)]
    rows: Annotated[int, Field(ge=5, le=200)]


class ResumeStart(Strict):
    """Reopen a Claude Code conversation in Cairn, in its own folder. `take_over` closes the
    Claude Code that has it open outside Cairn first: one conversation, one Claude."""

    cli_session_id: uuid.UUID
    cwd: Annotated[str, Field(min_length=3, max_length=500)]
    take_over: bool = False
    cols: Annotated[int, Field(ge=20, le=500)] = 120
    rows: Annotated[int, Field(ge=5, le=200)] = 32
