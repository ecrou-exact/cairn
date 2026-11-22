"""Graph API: the plan at one level as Pivotick nodes and edges, with the critical path."""

from __future__ import annotations

import uuid
from typing import Any

from flask import jsonify, request

from app.api import ApiError, api_blueprint
from app.features.graph import graph_core

graph_api = api_blueprint("graph_api")


def _uuid(name: str) -> uuid.UUID | None:
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise ApiError(f"'{name}' must be an id.", 422) from exc


def _view() -> dict[str, Any]:
    """What the graph shows: `project`, `root` (a task: its subtasks, or its neighbourhood),
    `closed=1`, `level=all`, `state` (actionable, blocked, late, soon) and `tag`."""
    return {
        "project_id": _uuid("project"),
        "root_id": _uuid("root"),
        "include_closed": request.args.get("closed") == "1",
        "level": "all" if request.args.get("level") == "all" else "top",
        "state": request.args.get("state", "") if request.args.get("state") in graph_core.STATES else "",
        "tag": request.args.get("tag", "")[:32],
    }


@graph_api.get("/graph")
def get_graph():
    """The graph's cards and links for the view in the query string (see `_view`)."""
    return jsonify(graph_core.graph_data(**_view()))


@graph_api.get("/graph/find")
def find_in_graph():
    """Tasks whose title contains `q`, each with the card that holds it in this view."""
    return jsonify(graph_core.find(request.args.get("q", ""), **_view()))
