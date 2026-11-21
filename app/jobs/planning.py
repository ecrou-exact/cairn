"""Planning maintenance jobs."""

from __future__ import annotations

from app.core.extensions import db
from app.core.jobs.context import JobContext
from app.core.jobs.registry import register_handler
from app.features.tasks.dependencies_core import refresh_derived


@register_handler(
    "tasks.rescore",
    lane="system",
    title="Recompute task scores and blocked states",
    max_attempts=2,
    manual=True,
)
def rescore(context: JobContext, payload: dict) -> dict:
    """Deadlines come closer and tasks age every day: scores move without any edit."""
    changed = refresh_derived()
    db.session.commit()
    context.log(f"{changed} task{'s' if changed != 1 else ''} updated.")
    return {"changed": changed}
