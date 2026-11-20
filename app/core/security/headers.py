"""Security headers on every response (PROJECT_BRIEF.md §11, docs/SECURITY.md T4).

The CSP allows no inline script or style and no eval. Trusted Types are sent
report-only for now: Bootstrap and Pivotick still assign HTML through the DOM,
and enforcement is switched on once every library is checked (Phase 11).
"""

from __future__ import annotations

from flask import Flask, Response

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
)
TRUSTED_TYPES_REPORT_ONLY = "require-trusted-types-for 'script'; trusted-types vitrine cairn"

HEADERS = {
    "Content-Security-Policy": CSP,
    "Content-Security-Policy-Report-Only": TRUSTED_TYPES_REPORT_ONLY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _apply(response: Response) -> Response:
        for name, value in HEADERS.items():
            response.headers.setdefault(name, value)
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "no-store")
        return response
