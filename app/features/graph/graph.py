"""The graph page: the plan drawn with Pivotick (PROJECT_BRIEF.md §4)."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, make_response, render_template, request

from app.core.security.headers import CSP_GRAPH
from app.core.utils.events import latest_event_id
from app.features.projects import projects_core
from app.features.tasks import workflow

graph = Blueprint("graph", __name__)


@graph.get("/graph")
def index():
    after = latest_event_id()
    project = None
    if request.args.get("project"):
        try:
            project = projects_core.get_project(uuid.UUID(request.args["project"]))
        except (ValueError, projects_core.ProjectNotFound):
            abort(404)
    response = make_response(
        render_template(
            "graph/index.html",
            project=project,
            projects=projects_core.options(),
            types=workflow.types(),
            events_after=after,
        )
    )
    response.headers["Content-Security-Policy"] = CSP_GRAPH
    return response
