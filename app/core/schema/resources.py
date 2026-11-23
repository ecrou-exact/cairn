"""Resources: inputs and outputs shared by forms, API and MCP tools (PROJECT_BRIEF.md §2.4).

Uploaded files and images come in through `resources_core.upload`, not through these
models: a `ResourceCreate` of kind `file` is a reference to a path, never file content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, Field, field_validator, model_validator

from app.core.db_class.resource import LINK_TARGETS, RESOURCE_KINDS
from app.core.schema.common import Output, Strict
from app.core.schema.planning import Markdown, Tags

CREATABLE_KINDS = tuple(kind for kind in RESOURCE_KINDS if kind != "image")  # images are uploaded


def _web_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Use a full web address starting with http:// or https://.")
    if any(c.isspace() for c in value):
        raise ValueError("A web address cannot contain spaces.")
    return value


def _github_url(value: str) -> str:
    if (urlsplit(value).hostname or "").lower() not in ("github.com", "www.github.com"):
        raise ValueError("A GitHub item is an address on github.com.")
    return value


WebUrl = Annotated[str, Field(max_length=2000), AfterValidator(_web_url)]
Language = Annotated[str, Field(max_length=30, pattern=r"^[a-z0-9+#._-]*$")]
Icon = Annotated[str, Field(pattern=r"^(fa-[a-z0-9-]{1,36})?$")]
Body = Annotated[str, Field(max_length=200_000)]
ResourceTitle = Annotated[str, Field(min_length=1, max_length=200)]


def required_fields(kind: str, *, url: str | None, body: str, path: str | None) -> str | None:
    """What a resource of `kind` is missing, or None. Shared by create and update."""
    if kind in ("url", "github") and not url:
        return "url"
    if kind == "github" and url:
        _github_url(url)
    if kind in ("note", "snippet") and not body.strip():
        return "body"
    if kind == "tool" and not url and not body.strip():
        return "url"
    if kind == "file" and not path:
        return "path"
    if kind == "skill" and not path and not body.strip():
        return "skill"
    return None


MISSING = {
    "url": "Give the address.",
    "body": "Write the content.",
    "path": "Give the path of the file, or upload it instead.",
    "skill": "Give the skill's folder, or write its instructions.",
}


class ResourceCreate(Strict):
    kind: Literal[CREATABLE_KINDS]  # type: ignore[valid-type]
    title: ResourceTitle | None = None  # from the address for url and github, required otherwise
    description_md: Markdown = ""
    url: WebUrl | None = None
    body: Body = ""
    language: Language = ""
    path: Annotated[str, Field(max_length=500)] | None = None
    icon: Icon = ""
    tags: Tags = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _one_line(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @model_validator(mode="after")
    def _complete(self) -> ResourceCreate:
        missing = required_fields(self.kind, url=self.url, body=self.body, path=self.path)
        if missing:
            raise ValueError(MISSING[missing])
        if not self.title and self.kind not in ("url", "github"):
            raise ValueError("Give it a title.")
        return self


class ResourceUpdate(Strict):
    """The kind never changes: a note does not become a file."""

    title: ResourceTitle | None = None
    description_md: Markdown | None = None
    url: WebUrl | None = None
    body: Body | None = None
    language: Language | None = None
    path: Annotated[str, Field(max_length=500)] | None = None
    icon: Icon | None = None
    tags: Tags | None = None

    @field_validator("title")
    @classmethod
    def _one_line(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class LinkCreate(Strict):
    target_type: Literal[LINK_TARGETS]  # type: ignore[valid-type]
    target_id: uuid.UUID
    note: Annotated[str, Field(max_length=300)] = ""


class ResourceOut(Output):
    id: uuid.UUID
    kind: str
    title: str
    description_md: str
    url: str | None
    body: str
    language: str
    path: str | None
    icon: str
    tags: list[str]
    original_name: str | None
    mime: str | None
    size_bytes: int | None
    sha256: str | None
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str


class LinkOut(Output):
    id: uuid.UUID
    resource_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    note: str
