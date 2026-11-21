"""Helpers for HTML routes: form values to schema input, readable errors, undo flashes."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from flask import flash
from pydantic import BaseModel, ValidationError


class FormErrors(ValueError):
    """Field name → message, shown next to each field; `""` is the form-level message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def validate[M: BaseModel](schema: type[M], values: Mapping[str, Any]) -> M:
    try:
        return schema.model_validate(values)
    except ValidationError as exc:
        errors: dict[str, str] = {}
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else ""
            message = err["msg"].removeprefix("Value error, ")
            errors.setdefault(field, message[0].upper() + message[1:] if message else message)
        raise FormErrors(errors) from exc


def optional(form: Mapping[str, str], name: str) -> str | None:
    """A text field, None when left empty."""
    value = (form.get(name) or "").strip()
    return value or None


def split_list(raw: str | None, separator: str = ",") -> list[str]:
    return [part.strip() for part in (raw or "").replace("\n", separator).split(separator) if part.strip()]


def flash_undo(message: str, batch_id: uuid.UUID) -> None:
    """A success message with an Undo button for the change made in `batch_id`."""
    flash({"text": message, "batch": str(batch_id)}, "undo")
