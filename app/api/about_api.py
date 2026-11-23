"""What Cairn is built with (D-074)."""

from __future__ import annotations

from flask import jsonify, request

from app.api import api_blueprint
from app.features.about import about_core

about_api = api_blueprint("about_api")


@about_api.get("/built-with")
def built_with():
    """Cairn's parts with their version and licence; `q`, `group`."""
    return jsonify(about_core.built_with(request.args.get("q", "")[:100], request.args.get("group", "")))
