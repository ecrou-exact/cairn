"""The resource form: HTML fields to schema input and back, and `task:<id>` targets."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from app.core.db_class.resource import LINK_TARGETS, Resource
from app.core.schema.resources import LinkCreate
from app.core.utils.web import optional, split_list

# Fields each kind shows in the form (the others keep their defaults).
KIND_FIELDS = {
    "url": ("url",),
    "github": ("url",),
    "tool": ("url", "body", "icon"),
    "note": ("body",),
    "snippet": ("body", "language"),
    "file": ("path",),
    "image": (),
}


def values_from_form(form: Mapping[str, str], kind: str) -> dict[str, Any]:
    values: dict[str, Any] = {
        "title": optional(form, "title"),
        "description_md": form.get("description_md", ""),
        "tags": split_list(form.get("tags")),
    }
    for field in KIND_FIELDS[kind]:
        values[field] = optional(form, field) if field in ("url", "path") else (form.get(field) or "").strip()
    if kind == "note":
        values["body"] = form.get("body", "")
    return values


def values_from_resource(resource: Resource) -> dict[str, Any]:
    return {
        "title": resource.title,
        "description_md": resource.description_md,
        "url": resource.url or "",
        "body": resource.body,
        "language": resource.language,
        "path": resource.path or "",
        "icon": resource.icon,
        "tags": ", ".join(resource.tags),
    }


def parse_target(raw: str | None) -> LinkCreate | None:
    """`task:<uuid>` or `project:<uuid>` → a link target; None when empty or malformed."""
    kind, _, value = (raw or "").partition(":")
    if kind not in LINK_TARGETS:
        return None
    try:
        return LinkCreate(target_type=kind, target_id=uuid.UUID(value))
    except ValueError:
        return None
