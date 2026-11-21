"""Projects, tasks and dependencies: inputs and outputs shared by forms, API and MCP tools.

`*Create` models carry defaults; `*Update` models have every field optional and only
the fields sent are changed (`model_dump(exclude_unset=True)`).
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, field_validator, model_validator

from app.core.db_class.planning import (
    CONDITION_KINDS,
    DEPENDENCY_KINDS,
    PRIORITIES,
    PROJECT_COLORS,
    PROJECT_STATUSES,
)
from app.core.schema.common import Output, Strict

_TAG = re.compile(r"^[\w][\w.+-]{0,31}$", re.UNICODE)


def _tags(values: list[str]) -> list[str]:
    seen: list[str] = []
    for raw in values:
        tag = raw.strip().lstrip("#").lower()
        if not _TAG.match(tag):
            raise ValueError(f"'{raw}' is not a valid tag (letters, digits, . _ + -, up to 32).")
        if tag not in seen:
            seen.append(tag)
    return seen


Tags = Annotated[list[str], Field(max_length=20), AfterValidator(_tags)]
Markdown = Annotated[str, Field(max_length=100_000)]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Level = Annotated[int, Field(ge=1, le=5)]
Hours = Annotated[float, Field(gt=0, le=10_000)]


class Link(Strict):
    label: Annotated[str, Field(min_length=1, max_length=60)]
    url: HttpUrl


class ChecklistItem(Strict):
    text: Annotated[str, Field(min_length=1, max_length=300)]
    done: bool = False


CustomValues = Annotated[
    dict[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")], str | float | None], Field(max_length=30)
]


class Recurrence(Strict):
    every: Annotated[int, Field(ge=1, le=365)] = 1
    unit: Literal["day", "week", "month", "year"]
    anchor: Literal["due", "done"] = "due"


# -- projects --------------------------------------------------------------------------------


class ProjectFields(Strict):
    description_md: Markdown = ""
    status: Literal[PROJECT_STATUSES] = "active"  # type: ignore[valid-type]
    color: Literal[PROJECT_COLORS] = "slate"  # type: ignore[valid-type]
    icon: Annotated[str, Field(pattern=r"^fa-[a-z0-9-]{1,36}$")] = "fa-folder"
    github_repo: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}$")] | None = None
    default_branch: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[^\s~^:?*\[\\]+$")] = "main"
    local_path: Annotated[str, Field(max_length=500)] | None = None
    stack: Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=30)] = Field(
        default_factory=list
    )
    links: Annotated[list[Link], Field(max_length=30)] = Field(default_factory=list)
    tags: Tags = Field(default_factory=list)
    claude_instructions_md: Markdown = ""
    weight: Annotated[float, Field(ge=0.25, le=3)] = 1.0


class ProjectCreate(ProjectFields):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")] | None = None


class ProjectUpdate(Strict):
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    slug: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")] | None = None
    description_md: Markdown | None = None
    status: Literal[PROJECT_STATUSES] | None = None  # type: ignore[valid-type]
    color: Literal[PROJECT_COLORS] | None = None  # type: ignore[valid-type]
    icon: Annotated[str, Field(pattern=r"^fa-[a-z0-9-]{1,36}$")] | None = None
    github_repo: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}$")] | None = None
    default_branch: (
        Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[^\s~^:?*\[\\]+$")] | None
    ) = None
    local_path: Annotated[str, Field(max_length=500)] | None = None
    stack: (
        Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=30)] | None
    ) = None
    links: Annotated[list[Link], Field(max_length=30)] | None = None
    tags: Tags | None = None
    claude_instructions_md: Markdown | None = None
    weight: Annotated[float, Field(ge=0.25, le=3)] | None = None


class ProjectOut(Output):
    id: uuid.UUID
    name: str
    slug: str
    description_md: str
    status: str
    color: str
    icon: str
    github_repo: str | None
    default_branch: str
    local_path: str | None
    stack: list[str]
    links: list[dict[str, str]]
    tags: list[str]
    claude_instructions_md: str
    weight: float
    created_at: datetime
    updated_at: datetime
    created_by: str


# -- tasks -----------------------------------------------------------------------------------


class TaskCreate(Strict):
    """Type and status are checked against the settings by tasks_core (they are configurable)."""

    title: Title
    description_md: Markdown = ""
    project_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    type: Annotated[str, Field(max_length=30)] = "feature"
    status: Annotated[str, Field(max_length=30)] | None = None  # first open status of the workflow
    priority: Literal[PRIORITIES] = "medium"  # type: ignore[valid-type]
    importance: Level = 3
    urgency: Level = 3
    start_on: date | None = None
    due_on: date | None = None
    hard_deadline: bool = False
    do_on: date | None = None
    estimate_hours: Hours | None = None
    assignee: Annotated[str, Field(min_length=1, max_length=80)] = "me"
    tags: Tags = Field(default_factory=list)
    checklist: Annotated[list[ChecklistItem], Field(max_length=100)] = Field(default_factory=list)
    acceptance_md: Markdown = ""
    claude_instructions_md: Markdown = ""
    recurrence: Recurrence | None = None
    custom: CustomValues = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join(value.split())


class TaskUpdate(Strict):
    title: Title | None = None
    description_md: Markdown | None = None
    project_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    type: Annotated[str, Field(max_length=30)] | None = None
    status: Annotated[str, Field(max_length=30)] | None = None
    priority: Literal[PRIORITIES] | None = None  # type: ignore[valid-type]
    importance: Level | None = None
    urgency: Level | None = None
    start_on: date | None = None
    due_on: date | None = None
    hard_deadline: bool | None = None
    do_on: date | None = None
    estimate_hours: Hours | None = None
    assignee: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    tags: Tags | None = None
    checklist: Annotated[list[ChecklistItem], Field(max_length=100)] | None = None
    acceptance_md: Markdown | None = None
    claude_instructions_md: Markdown | None = None
    recurrence: Recurrence | None = None  # sent as null: no longer repeats
    custom: CustomValues | None = None  # replaces every custom value; checked by tasks_core

    @field_validator("title")
    @classmethod
    def _one_line(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class TaskStatus(Strict):
    status: Annotated[str, Field(min_length=1, max_length=30)]


class QuickAdd(Strict):
    text: Annotated[str, Field(min_length=1, max_length=500)]
    project_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None


class TaskOut(Output):
    id: uuid.UUID
    title: str
    description_md: str
    project_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    type: str
    status: str
    priority: str
    importance: int
    urgency: int
    start_on: date | None
    due_on: date | None
    hard_deadline: bool
    do_on: date | None
    completed_at: datetime | None
    estimate_hours: float | None
    actual_hours: float
    assignee: str
    tags: list[str]
    checklist: list[dict[str, Any]]
    acceptance_md: str
    claude_instructions_md: str
    recurrence: dict[str, Any] | None
    custom: dict[str, Any]
    next_occurrence_id: uuid.UUID | None
    is_open: bool
    is_blocked: bool
    blocked_by_count: int
    unblocks_count: int
    score: float
    score_explain: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    created_by: str


# -- dependencies ----------------------------------------------------------------------------


class DependencyCreate(Strict):
    from_task_id: uuid.UUID
    to_task_id: uuid.UUID
    kind: Literal[DEPENDENCY_KINDS] = "blocks"  # type: ignore[valid-type]
    note: Annotated[str, Field(max_length=300)] = ""


class DependencyOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    from_task_id: uuid.UUID
    to_task_id: uuid.UUID
    kind: str
    note: str


class ConditionCreate(Strict):
    task_id: uuid.UUID
    kind: Literal[CONDITION_KINDS] = "other"  # type: ignore[valid-type]
    label: Annotated[str, Field(min_length=1, max_length=200)]
    url: Annotated[str, Field(max_length=2000, pattern=r"^https?://\S+$")] | None = None
    until_on: date | None = None

    @model_validator(mode="after")
    def _date_needs_a_day(self) -> ConditionCreate:
        if self.kind == "date" and self.until_on is None:
            raise ValueError("Say until which day it waits.")
        return self


class ConditionResolve(Strict):
    resolved: bool


class ConditionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    task_id: uuid.UUID
    kind: str
    label: str
    url: str | None
    until_on: date | None
    resolved_at: datetime | None


class BulkEdit(Strict):
    """One change applied to many tasks (one history batch, one undo)."""

    task_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=500)]
    status: Annotated[str, Field(max_length=30)] | None = None
    priority: Literal[PRIORITIES] | None = None  # type: ignore[valid-type]
    project_id: uuid.UUID | None = None
    clear_project: bool = False
    add_tags: Tags = Field(default_factory=list)
    remove_tags: Tags = Field(default_factory=list)
    delete: bool = False
