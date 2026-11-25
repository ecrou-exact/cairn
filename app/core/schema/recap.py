"""Inputs of the day summary and of the time entries (D-078)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.core.schema.common import Strict

Clock = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
Minutes = Annotated[int, Field(ge=5, le=24 * 60)]
Description = Annotated[str, Field(max_length=4000)]
Word = Annotated[str, Field(min_length=1, max_length=60)]
Slug = Annotated[str, Field(min_length=1, max_length=80)]


class TargetInput(Strict):
    label: Annotated[str, Field(min_length=1, max_length=80)]
    repos: Annotated[list[Word], Field(max_length=40)] = Field(default_factory=list)
    keywords: Annotated[list[Word], Field(max_length=40)] = Field(default_factory=list)
    is_default: bool = False
    guidance: Annotated[str, Field(max_length=2000)] = ""
    about: Annotated[str, Field(max_length=500)] = ""
    kimai_project: Annotated[int, Field(ge=1)]
    kimai_activity: Annotated[int, Field(ge=1)]
    tags: Annotated[list[Word], Field(max_length=10)] = Field(default_factory=list)

    @field_validator("repos")
    @classmethod
    def _names(cls, values: list[str]) -> list[str]:
        # `owner/name` and a fork of it are one: only the name counts
        names = (v.lower().rstrip("/").removesuffix(".git").rsplit("/", 1)[-1] for v in values)
        return [name for name in dict.fromkeys(names) if name]

    @field_validator("keywords")
    @classmethod
    def _lower(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(v.lower() for v in values))

    @field_validator("tags")
    @classmethod
    def _no_comma(cls, values: list[str]) -> list[str]:
        if any("," in v for v in values):
            raise ValueError("a tag has no comma")
        return values

    @model_validator(mode="after")
    def _matches(self) -> TargetInput:
        if not (self.repos or self.keywords or self.guidance):
            raise ValueError("Say what goes here: repositories, words, or an explanation for Claude.")
        return self


class EntryInput(Strict):
    target_id: uuid.UUID
    begin: Clock
    minutes: Minutes
    description: Description = ""


class EntryUpdate(Strict):
    target_id: uuid.UUID | None = None
    day: date | None = None
    kimai_project: Annotated[int, Field(ge=1)] | None = None
    kimai_activity: Annotated[int, Field(ge=1)] | None = None
    tags: Annotated[list[Word], Field(max_length=10)] | None = None
    begin: Clock | None = None
    minutes: Minutes | None = None
    description: Description | None = None

    @model_validator(mode="after")
    def _pair(self) -> EntryUpdate:
        if (self.kimai_project is None) != (self.kimai_activity is None):
            raise ValueError("Choose a project and its activity.")
        if any("," in tag for tag in self.tags or []):
            raise ValueError("a tag has no comma")
        return self


class SummaryInput(Strict):
    summary: Annotated[str, Field(max_length=50_000)]


class SendInput(Strict):
    """The drafts the owner sends, named one by one."""

    entries: Annotated[list[uuid.UUID], Field(min_length=1, max_length=30)]


class RulesInput(Strict):
    """Rules of another Cairn, or a copy of these."""

    rules: Annotated[list[TargetInput], Field(min_length=1, max_length=100)]


class PeriodTryInput(Strict):
    """The projects (slugs) looked at for a period (D-104)."""

    projects: Annotated[list[Slug], Field(min_length=1, max_length=100)]


class PeriodSendInput(Strict):
    """The rules whose drafts of a period the owner sends (D-103)."""

    rules: Annotated[list[uuid.UUID], Field(min_length=1, max_length=100)]
