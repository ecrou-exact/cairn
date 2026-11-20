"""Access rules. Every endpoint needs the owner's session unless it is marked `@public`.

Deny by default: `enforce_authentication` runs before every request, so a route
that forgets a decorator is protected anyway (docs/SECURITY.md T1-T2).
"""

from __future__ import annotations

from collections.abc import Callable

from flask import Flask, current_app, jsonify, redirect, request, url_for
from flask_login import current_user

_PUBLIC_ATTR = "_cairn_public"


def public[F: Callable[..., object]](view: F) -> F:
    """Mark a view as reachable without being signed in (login, setup, health)."""
    setattr(view, _PUBLIC_ATTR, True)
    return view


def _is_public(endpoint: str | None) -> bool:
    if endpoint is None or endpoint == "static":
        return True
    view = current_app.view_functions.get(endpoint)
    return bool(view and getattr(view, _PUBLIC_ATTR, False))


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def register_access_rules(app: Flask) -> None:
    from app.features.account.account_core import owner_exists

    @app.before_request
    def enforce_authentication():
        endpoint = request.endpoint
        if not owner_exists() and endpoint not in {"account.setup", "static", "health.health_check"}:
            if _wants_json():
                return jsonify(error="Cairn is not set up yet."), 503
            return redirect(url_for("account.setup"))
        if _is_public(endpoint) or current_user.is_authenticated:
            return None
        if _wants_json():
            return jsonify(error="Authentication required."), 401
        return redirect(url_for("account.login", next=request.full_path if request.method == "GET" else None))
