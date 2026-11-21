"""The graph page: the plan drawn with Pivotick (PROJECT_BRIEF.md §4)."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from flask import Blueprint, abort, make_response, render_template, request

from app.core.security.headers import CSP_GRAPH
from app.core.utils.events import latest_event_id
from app.features.graph import graph_core
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
    level = "all" if request.args.get("level") == "all" else "top"
    state = request.args.get("state", "") if request.args.get("state") in graph_core.STATES else ""
    tag = request.args.get("tag", "")[:32]
    closed = request.args.get("closed") == "1"
    wanted = {
        "project": project.id if project and not root else None,
        "root": root.id if root else None,
        "closed": "1" if closed else None,
        "level": "all" if level == "all" and not root else None,
        "state": state or None,
        "tag": tag or None,
    }
    response = make_response(
        render_template(
            "graph/index.html",
            project=project,
            root=root,
            level=level,
            states=graph_core.STATES,
            state=state,
            tags=graph_core.tags_in_use(),
            tag=tag,
            closed=closed,
            graph_query=urlencode({k: str(v) for k, v in wanted.items() if v}),
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
