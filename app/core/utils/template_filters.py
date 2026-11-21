"""Jinja filters shared by every template."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from flask import Flask


def pretty_json(value: Any) -> str:
    """Indented JSON as the owner reads it (accents and dashes kept as they are, not escaped).

    Returns plain text, escaped by Jinja like any other value. Inside a
    <script type="application/json"> chain it with `| tojson`, which makes it script-safe.
    """
    return json.dumps(value, indent=2, ensure_ascii=False)


def relative_day(day: date, today: date | None = None) -> str:
    """Today, Tomorrow, Yesterday, Fri 21 Nov, or 3 Jan 2027 when not this year."""
    today = today or date.today()
    delta = (day - today).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta == -1:
        return "Yesterday"
    if -7 < delta < 7:
        return f"{day:%a %d %b}"
    return f"{day:%d %b}" if day.year == today.year else f"{day:%d %b %Y}"


def register_template_filters(app: Flask) -> None:
    from app.features.tasks import timer_core, workflow

    app.add_template_filter(pretty_json)
    app.add_template_filter(relative_day)
    app.add_template_filter(workflow.label_of, "status_label")
    app.add_template_filter(workflow.kind_of, "status_kind")
    app.add_template_filter(timer_core.format_duration, "duration")
    app.add_template_global(date.today, "today")
    app.add_template_global(timer_core.running, "running_timer")
