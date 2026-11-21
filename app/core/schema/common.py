"""Pieces shared by every schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    """Inputs: unknown fields are refused instead of silently dropped."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def page_dict(page, items: list[dict[str, Any]]) -> dict[str, Any]:
    """The JSON shape of a server-side list page (app/core/utils/listing.py)."""
    return {
        "items": items,
        "total": page.total,
        "page": page.page,
        "pages": page.pages,
        "per_page": page.per_page,
        "sort": page.sort,
        "dir": page.direction,
        "q": page.search,
        "filters": page.active_filters,
    }
