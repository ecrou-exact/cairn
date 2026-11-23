"""What the owner takes from a project's folder (D-081)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.core.schema.common import Strict


class BringInput(Strict):
    keys: Annotated[
        list[Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]], Field(min_length=1, max_length=300)
    ]


class GitAction(Strict):
    folder: Annotated[str, Field(min_length=1, max_length=500)]
