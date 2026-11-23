"""Every project of the machine, found then started (D-088)."""

from __future__ import annotations

from app.core.jobs.context import JobContext
from app.core.jobs.registry import register_handler
from app.features.folder import discover_core


@register_handler(
    discover_core.FIND,
    lane="io",
    title="Look for my projects",
    max_attempts=1,
    timeout_seconds=900,
    manual=True,
)
def find(context: JobContext, payload: dict) -> dict:
    return discover_core.find(context)


@register_handler(
    discover_core.MAKE, lane="io", title="Start the projects found", max_attempts=1, timeout_seconds=900
)
def make(context: JobContext, payload: dict) -> dict:
    return discover_core.make(list(payload.get("keys") or []), context)
