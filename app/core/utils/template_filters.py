"""Jinja filters shared by every template."""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from flask import Flask
from flask_login import current_user


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


def filesize(size: int | None) -> str:
    if size is None:
        return ""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def host(url: str | None) -> str:
    """The site of an address, without `www.`: `github.com`."""
    name = urlsplit(url or "").hostname or ""
    return name.removeprefix("www.")


def register_template_filters(app: Flask) -> None:
    from app.features.about import about_core
    from app.features.claude import main_core
    from app.features.comments import comments_core
    from app.features.projects import projects_core
    from app.features.resources import resources_core
    from app.features.tasks import recurrence_core, timer_core, workflow

    app.add_template_filter(pretty_json)
    app.add_template_filter(filesize)
    app.add_template_filter(recurrence_core.describe, "recurrence")
    app.add_template_filter(comments_core.author_label, "author")
    app.add_template_filter(host)
    app.add_template_filter(resources_core.icon_of, "resource_icon")
    app.add_template_filter(resources_core.KIND_LABELS.get, "kind_label")
    app.add_template_filter(relative_day)
    app.add_template_filter(workflow.label_of, "status_label")
    app.add_template_filter(workflow.kind_of, "status_kind")
    app.add_template_filter(workflow.allowed_next, "next_statuses")
    app.add_template_filter(timer_core.format_duration, "duration")
    app.add_template_global(date.today, "today")
    app.add_template_filter(lambda value: (value, value), "pair")
    app.add_template_test(lambda condition: condition.is_waiting(date.today()), "is_waiting_today")
    app.add_template_global(timer_core.running, "running_timer")
    app.add_template_global(main_core.dock_open, "dock_open")

    @app.context_processor
    def _shell() -> dict[str, Any]:
        about = {"version": about_core.version(), "source": about_core.SOURCE, "license": about_core.LICENSE}
        return {
            "cairn": about,
            "dock": current_user.is_authenticated,
            "pinned_projects": projects_core.pinned() if current_user.is_authenticated else [],
        }  # the main Claude beside the page (D-063)
