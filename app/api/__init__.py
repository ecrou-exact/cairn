"""REST API under /api: thin blueprints that validate input with the shared schemas
(`app/core/schema/`) and call the same core functions as the HTML pages.

Authentication is the owner's session (deny by default, see decorators.py); writes
need the CSRF token in the `X-CSRFToken` header.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Flask, jsonify, request
from pydantic import BaseModel, ValidationError


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, details: Any = None) -> None:
        super().__init__(message)
        self.status, self.details = status, details


def body[M: BaseModel](schema: type[M]) -> M:
    """The JSON body validated by `schema`, or a 422 answer listing what is wrong."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Send a JSON object.", 400)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        raise ApiError("Invalid input.", 422, details) from exc


def register_api(app: Flask) -> None:
    from app.api.about_api import about_api
    from app.api.changesets_api import changesets_api
    from app.api.claude_api import claude_api
    from app.api.comments_api import comments_api
    from app.api.folder_api import folder_api
    from app.api.graph_api import graph_api
    from app.api.instances_api import instances_api
    from app.api.jobs_api import jobs_api
    from app.api.planning_api import planning_api
    from app.api.recap_api import recap_api
    from app.api.resources_api import resources_api
    from app.api.settings_api import settings_api
    from app.api.worklinks_api import worklinks_api

    for blueprint in (
        jobs_api,
        settings_api,
        planning_api,
        resources_api,
        comments_api,
        graph_api,
        claude_api,
        instances_api,
        changesets_api,
        about_api,
        recap_api,
        folder_api,
        worklinks_api,
    ):
        app.register_blueprint(blueprint)

    @app.errorhandler(ApiError)
    def _api_error(exc: ApiError):
        payload: dict[str, Any] = {"error": str(exc)}
        if exc.details is not None:
            payload["details"] = exc.details
        return jsonify(payload), exc.status


def api_blueprint(name: str) -> Blueprint:
    return Blueprint(name, __name__, url_prefix="/api")
