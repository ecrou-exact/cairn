"""Graph API: the plan as Pivotick nodes and edges, with the critical path."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint
from app.features.graph import graph_core

graph_api = api_blueprint("graph_api")


@graph_api.get("/graph")
def get_graph():
    project_id = None
    if request.args.get("project"):
        try:
            project_id = uuid.UUID(request.args["project"])
        except ValueError as exc:
            raise ApiError("'project' must be a project id.", 422) from exc
    return jsonify(graph_core.graph_data(project_id, include_closed=request.args.get("closed") == "1"))
