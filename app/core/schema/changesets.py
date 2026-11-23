"""A changeset's items (D-071). A task is named by its id, or by the `key` of an item of the same
changeset that creates it. Fields are the ones the pages accept, less what stays the owner's."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.core.db_class.planning import DEPENDENCY_KINDS, PRIORITIES
from app.core.schema.common import Strict
from app.core.schema.planning import Hours, Level, Markdown, Tags, Title

Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")]
Ref = Annotated[str, Field(min_length=1, max_length=60)]  # a task's id, or an item's key
Reason = Annotated[str, Field(max_length=500)]
Line = Annotated[str, Field(min_length=1, max_length=300)]
MAX_ITEMS = 100


class TaskFields(Strict):
    description: Markdown | None = None
    acceptance: Markdown | None = None
    checklist: Annotated[list[Line], Field(max_length=100)] | None = None
    type: Annotated[str, Field(max_length=30)] | None = None
    priority: Literal[PRIORITIES] | None = None  # type: ignore[valid-type]
    importance: Level | None = None
    estimate_hours: Hours | None = None
    start_on: date | None = None
    do_on: date | None = None
    due_on: date | None = None
    tags: Tags | None = None


class CreateTask(TaskFields):
    op: Literal["create_task"]
    key: Key
    title: Title
    project: Annotated[str, Field(max_length=120)] | None = None  # id, slug or name
    parent: Ref | None = None
    reason: Reason = ""


class UpdateTask(TaskFields):
    op: Literal["update_task"]
    task: Ref
    title: Title | None = None
    reason: Reason = ""

    @model_validator(mode="after")
    def _something(self) -> UpdateTask:
        if not self.model_fields_set - {"op", "task", "reason"}:
            raise ValueError("says nothing to change")
        return self


class SetStatus(Strict):
    op: Literal["set_status"]
    task: Ref
    status: Annotated[str, Field(min_length=1, max_length=30)]
    reason: Reason = ""


class LinkTasks(Strict):
    op: Literal["link_tasks"]
    first: Ref
    then: Ref
    kind: Literal[DEPENDENCY_KINDS] = "blocks"  # type: ignore[valid-type]
    reason: Reason = ""


class Comment(Strict):
    op: Literal["comment"]
    task: Ref
    text: Annotated[str, Field(min_length=1, max_length=20_000)]
    reason: Reason = ""


ChangeItem = Annotated[CreateTask | UpdateTask | SetStatus | LinkTasks | Comment, Field(discriminator="op")]


class ChangesetCreate(Strict):
    title: Title
    reason: Markdown = ""
    items: Annotated[list[ChangeItem], Field(min_length=1, max_length=MAX_ITEMS)]

    @model_validator(mode="after")
    def _keys(self) -> ChangesetCreate:
        keys = [item.key for item in self.items if isinstance(item, CreateTask)]
        if len(keys) != len(set(keys)):
            raise ValueError("two items have the same key")
        return self


class ChangesetApply(Strict):
    """The items the owner keeps, by their place in the list."""

    keep: Annotated[
        list[Annotated[int, Field(ge=0, lt=MAX_ITEMS)]], Field(min_length=1, max_length=MAX_ITEMS)
    ]
