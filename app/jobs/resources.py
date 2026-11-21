"""Resource jobs: link previews."""

from __future__ import annotations

import uuid

from app.core.db_class.resource import Resource
from app.core.extensions import db
from app.core.jobs.context import JobContext
from app.core.jobs.registry import register_handler
from app.core.utils.settings import get_setting
from app.features.resources import preview_core, resources_core


@register_handler(
    "resources.preview", lane="io", title="Fetch a link preview", max_attempts=2, timeout_seconds=60
)
def preview(context: JobContext, payload: dict) -> dict:
    resource = db.session.get(Resource, uuid.UUID(payload["resource_id"]))
    if resource is None or resource.is_deleted or not resource.url:
        context.log("The resource is gone or has no address: nothing to fetch.")
        return {"skipped": True}
    if not get_setting("resources.previews"):
        context.log("Link previews are turned off in the settings.")
        return {"skipped": True}
    context.log(f"Fetching {resource.url}")
    try:
        found = preview_core.fetch(resource.url)
    except preview_core.PreviewError as exc:
        resources_core.apply_preview(resource.id, None, str(exc))
        db.session.commit()
        context.log(str(exc), "WARN")
        return {"ok": False, "error": str(exc)}
    resources_core.apply_preview(resource.id, found)
    db.session.commit()
    context.log(f"Title: {found.get('title') or '(none)'}")
    return {"ok": True, **found}
