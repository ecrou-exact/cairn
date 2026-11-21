"""Jinja filters shared by every template."""

from __future__ import annotations

import json
from typing import Any

from flask import Flask


def pretty_json(value: Any) -> str:
    """Indented JSON as the owner reads it (accents and dashes kept as they are, not escaped).

    Returns plain text, escaped by Jinja like any other value. Inside a
    <script type="application/json"> chain it with `| tojson`, which makes it script-safe.
    """
    return json.dumps(value, indent=2, ensure_ascii=False)


def register_template_filters(app: Flask) -> None:
    app.add_template_filter(pretty_json)
