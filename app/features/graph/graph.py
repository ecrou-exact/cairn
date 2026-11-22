"""The graph page: the plan drawn with Pivotick (PROJECT_BRIEF.md §4)."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from app.core.security.headers import CSP_GRAPH
from app.core.utils.events import latest_event_id
from app.features.graph import graph_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core, workflow

graph = Blueprint("graph", __name__)


def graph_view(args, *, project=None, root=None) -> dict:
    """What a task graph shows, read from the query string: level, state, tag, done tasks; and
    the query its stage sends to /api/graph. Shared by a case's graph and the project page."""
    level = "all" if args.get("level") == "all" and root is None else "top"
    state = args.get("state", "") if args.get("state") in graph_core.STATES else ""
    tag = args.get("tag", "")[:32]
    closed = args.get("closed") == "1"
    wanted = {
        "project": project.id if project is not None and root is None else None,
        "root": root.id if root is not None else None,
        "closed": "1" if closed else None,
        "level": "all" if level == "all" else None,
        "state": state or None,
        "tag": tag or None,
    }
    return {
        "level": level,
        "states": graph_core.STATES,
        "state": state,
        "tags": graph_core.tags_in_use(),
        "tag": tag,
        "closed": closed,
        "graph_query": urlencode({k: str(v) for k, v in wanted.items() if v}),
    }


@graph.get("/graph")
def index():
    """A case's own graph (`root`). The graph lives in the projects (D-044): without a case,
    the plan of projects (Projects page) or the project's plan (its page)."""
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
    if root is None:
        if project is not None:
            return redirect(url_for("projects.detail", slug=project.slug, tab="plan"))
        return redirect(url_for("projects.index"))
    response = make_response(
        render_template(
            "graph/index.html",
            project=project,
            root=root,
            types=workflow.types(),
            events_after=after,
            **graph_view(request.args, project=project, root=root),
        )
    )
    return with_graph_csp(response)


def with_graph_csp(response):
    """Pages that embed the graph get the graph CSP (D-035)."""
    response.headers["Content-Security-Policy"] = CSP_GRAPH
    return response
