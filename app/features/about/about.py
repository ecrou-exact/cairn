"""What Cairn is built with (D-074)."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from app.features.about import about_core

about = Blueprint("about", __name__)


@about.get("/built-with")
def built_with():
    q, group = request.args.get("q", "")[:100], request.args.get("group", "")
    found = about_core.built_with(q, group)
    if group not in found["groups"]:
        group = ""
        found = about_core.built_with(q)
    return render_template("about/built_with.html", found=found, q=q, group=group)
