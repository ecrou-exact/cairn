"""The graph page: the plan drawn with Pivotick (PROJECT_BRIEF.md §4)."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, make_response, render_template, request

from app.core.security.headers import CSP_GRAPH
from app.core.utils.events import latest_event_id
from app.features.projects import projects_core
from app.features.tasks import tasks_core, workflow

graph = Blueprint("graph", __name__)


@graph.get("/graph")
def index():
    after = latest_event_id()
    project = root = None
    try:
        if request.args.get("project"):
            project = projects_core.get_project(uuid.UUID(request.args["project"]))
        if request.args.get("root"):
            root = tasks_core.get_task(uuid.UUID(request.args["root"]))
            project = root.project
    except (ValueError, projects_core.ProjectNotFound, tasks_core.TaskNotFound):
        abort(404)
    response = make_response(
        render_template(
            "graph/index.html",
            project=project,
            root=root,
            level="all" if request.args.get("level") == "all" else "top",
            projects=projects_core.options(),
            types=workflow.types(),
            events_after=after,
        )
    )
    return with_graph_csp(response)


def with_graph_csp(response):
    """Pages that embed the graph get the graph CSP (D-035)."""
    response.headers["Content-Security-Policy"] = CSP_GRAPH
    return response
