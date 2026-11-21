"""`GET /events`: the Server-Sent Events stream every page listens to."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, request, stream_with_context

from app.api import ApiError
from app.core.utils import events as events_core

events = Blueprint("events", __name__)


@events.get("/events")
def stream():
    try:
        topics = events_core.parse_topics(request.args.get("topics"))
    except ValueError as exc:
        raise ApiError(str(exc), 400) from exc
    raw = request.headers.get("Last-Event-ID") or request.args.get("after")
    after = int(raw) if raw and raw.isdigit() else None
    body = events_core.sse_stream(after, topics, lifetime=current_app.config["SSE_LIFETIME_SECONDS"])
    return Response(
        stream_with_context(body),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
