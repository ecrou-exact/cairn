"""Versioned static URLs (Rulezet pattern): `url_for('static', …)` adds `?v=<mtime>`,
so static files can be cached for good and still change on update.

They carry no session: Flask would add `Vary: Cookie`, and a browser whose session cookie
changed since would ask for every stylesheet again before it can draw a page (D-057)."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, request
from flask.sessions import SecureCookieSessionInterface


class PageSessions(SecureCookieSessionInterface):
    def save_session(self, app, session, response) -> None:
        if request.endpoint != "static":
            super().save_session(app, session, response)


def register_static_versions(app: Flask) -> None:
    app.session_interface = PageSessions()
    static_root = Path(app.static_folder or "")

    @app.url_defaults
    def _add_version(endpoint: str, values: dict) -> None:
        if endpoint != "static" or "filename" not in values:
            return
        path = static_root / values["filename"]
        if path.is_file():
            values["v"] = int(path.stat().st_mtime)

    @app.after_request
    def _cache_static(response):
        if request.endpoint == "static" and request.args.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
