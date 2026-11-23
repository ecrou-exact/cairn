"""Work linked to a project or a task (D-083)."""

from __future__ import annotations

import uuid

from flask import jsonify

from app.api import ApiError, api_blueprint, body
from app.core.schema.worklinks import WorkLinkCreate
from app.features.worklinks import worklinks_core

worklinks_api = api_blueprint("worklinks_api")


@worklinks_api.get("/<any(project, task):target_type>s/<uuid:target_id>/work")
def list_links(target_type: str, target_id: uuid.UUID):
    """Its own links, what Cairn made for it, and what comes from its parents and project."""
    try:
        return jsonify(worklinks_core.for_target(target_type, target_id))
    except worklinks_core.WorkLinkError as exc:
        raise ApiError(str(exc), 404) from exc


@worklinks_api.post("/work-links")
def add_link():
    try:
        link = worklinks_core.add(body(WorkLinkCreate))
    except worklinks_core.WorkLinkError as exc:
        raise ApiError(str(exc), 404) from exc
    return jsonify(id=str(link.id)), 201


@worklinks_api.delete("/work-links/<uuid:link_id>")
def remove_link(link_id: uuid.UUID):
    try:
        worklinks_core.remove(link_id)
    except worklinks_core.WorkLinkError as exc:
        raise ApiError(str(exc), 404) from exc
    return "", 204
