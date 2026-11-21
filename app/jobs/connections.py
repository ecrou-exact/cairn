"""Connected account jobs: check a token with its service."""

from __future__ import annotations

import uuid

from app.core.jobs.context import JobContext
from app.core.jobs.registry import register_handler
from app.features.connections import connections_core


@register_handler(
    "connections.check", lane="io", title="Check a connected account", max_attempts=1, timeout_seconds=60
)
def check(context: JobContext, payload: dict) -> dict:
    try:
        connection = connections_core.run_check(uuid.UUID(payload["connection_id"]))
    except connections_core.ConnectionError_ as exc:  # removed while the check was waiting
        context.log(str(exc), "WARN")
        return {"skipped": True}
    if connection.state == "ok":
        context.log(f"{connection.label}: OK ({connection.identity}).")
    else:
        context.log(f"{connection.label}: {connection.error}", "WARN")
    return {"state": connection.state}
