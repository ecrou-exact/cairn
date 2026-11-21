"""Task statuses, their kinds and allowed transitions, and task types — all from settings."""

from __future__ import annotations

from typing import Any

from app.core.utils.settings import get_setting

OPEN_KINDS = ("open", "active", "waiting")
CLOSED_KINDS = ("done", "cancelled")


def statuses() -> list[dict[str, str]]:
    return list(get_setting("tasks.workflow")["statuses"])


def status_map() -> dict[str, dict[str, str]]:
    return {s["key"]: s for s in statuses()}


def kind_of(status: str) -> str:
    """Kind of a status; a status removed from the workflow counts as open."""
    found = status_map().get(status)
    return found["kind"] if found else "open"


def label_of(status: str) -> str:
    found = status_map().get(status)
    return found["label"] if found else status.replace("_", " ").capitalize()


def is_open_status(status: str) -> bool:
    return kind_of(status) in OPEN_KINDS


def first_status(kind: str) -> str | None:
    return next((s["key"] for s in statuses() if s["kind"] == kind), None)


def default_status() -> str:
    return get_setting("tasks.workflow")["default"]


def allowed_next(status: str) -> list[str]:
    transitions: dict[str, list[str]] = get_setting("tasks.workflow")["transitions"]
    known = status_map()
    return [key for key in transitions.get(status, list(known)) if key in known and key != status]


def status_choices(current: str | None) -> list[dict[str, str]]:
    """Statuses a form may offer: all for a new task; the current one and its allowed next ones."""
    known = status_map()
    if current is None or current not in known:
        return statuses()
    return [known[current], *(known[key] for key in allowed_next(current))]


def keys_of_kinds(*kinds: str) -> list[str]:
    return [s["key"] for s in statuses() if s["kind"] in kinds]


def types() -> dict[str, dict[str, Any]]:
    return dict(get_setting("tasks.types"))
