"""Work linked to a project or a task (D-083)."""

from __future__ import annotations

import re
import uuid
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.core.db_class.worklink import WORK_KINDS, WORK_TARGETS
from app.core.schema.common import Strict

SHAPES = {
    "branch": re.compile(r"^[^\s~^:?*\[\\]{1,250}$"),
    "commit": re.compile(r"^[0-9a-fA-F]{7,40}$"),
    "pull": re.compile(r"^(?:[\w.-]+/[\w.-]+)?#\d{1,7}$"),
    "claude": re.compile(r"^[0-9a-fA-F-]{36}$"),
    "folder": re.compile(r"^(/|[A-Za-z]:[\\/]|~).{0,498}$"),
    "instance": re.compile(r"^.{1,80}$"),
}
TOLD = {
    "branch": "a branch name",
    "commit": "a commit's sha (7 to 40 characters)",
    "pull": "#123 or owner/name#123",
    "claude": "a conversation or session id",
    "folder": "a full path",
    "instance": "one of the project's instances, by its name",
}
PULL_URL = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)")


class WorkLinkCreate(Strict):
    target_type: Literal[WORK_TARGETS]  # type: ignore[valid-type]
    target_id: uuid.UUID
    kind: Literal[WORK_KINDS]  # type: ignore[valid-type]
    ref: Annotated[str, Field(min_length=1, max_length=500)]
    note: Annotated[str, Field(max_length=500)] = ""

    @model_validator(mode="after")
    def _shape(self) -> WorkLinkCreate:
        if self.kind == "pull" and (found := PULL_URL.search(self.ref)):
            self.ref = f"{found[1]}#{found[2]}"
        if self.kind == "commit":
            self.ref = self.ref.lower()
        if not SHAPES[self.kind].match(self.ref):
            raise ValueError(f"A {self.kind} is {TOLD[self.kind]}.")
        return self
