"""Claude pages (D-050): the overview of every Claude Code session, a session's terminal,
and the stream of its output."""

from __future__ import annotations

import json
import secrets
import time
import uuid

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from app.core.schema.claude import SessionStart
from app.core.security.headers import csp_terminal
from app.core.utils.events import latest_event_id
from app.core.utils.web import FormErrors, local_path, validate
from app.features.claude import claude_core, terminal_core

claude = Blueprint("claude", __name__)

KEEP_ALIVE = 15.0


def with_terminal_csp(response, nonce: str):
    response.headers["Content-Security-Policy"] = csp_terminal(nonce)
    return response


@claude.get("/claude")
def index():
    after = latest_event_id()
    return render_template("claude/index.html", overview=claude_core.overview(), events_after=after)


@claude.get("/claude/sessions/<uuid:session_id>")
def session(session_id: uuid.UUID):
    try:
        row = terminal_core.get(session_id)
    except terminal_core.TerminalError:
        abort(404)
    nonce = secrets.token_urlsafe(16)
    page = render_template(
        "claude/session.html",
        session=claude_core.describe(row),
        nonce=nonce,
        events_after=latest_event_id(),
    )
    return with_terminal_csp(make_response(page), nonce)


def _stream(session_id: uuid.UUID, after: int, lifetime: float):
    """`id: <seq>` + `data: {"t": text}` per batch of output; `event: end` once it has ended.
    The stream closes after `lifetime` and the browser resumes with Last-Event-ID."""
    yield f"retry: 1500\nid: {after}\n: connected\n\n"
    started = last = time.monotonic()
    while True:
        chunks, ended = terminal_core.output(session_id, after, wait=1.0 if lifetime else 0.0)
        if chunks:
            after = chunks[-1][0]
            yield f"id: {after}\ndata: {json.dumps({'t': ''.join(text for _, text in chunks)})}\n\n"
            last = time.monotonic()
        if ended:
            yield "event: end\ndata: {}\n\n"
            return
        now = time.monotonic()
        if now - started >= lifetime:
            return
        if now - last >= KEEP_ALIVE:
            yield ": keep-alive\n\n"
            last = now


@claude.get("/claude/sessions/<uuid:session_id>/stream")
def stream(session_id: uuid.UUID):
    raw = request.headers.get("Last-Event-ID") or request.args.get("after") or "0"
    after = int(raw) if raw.isdigit() else 0
    body = _stream(session_id, after, float(current_app.config["SSE_LIFETIME_SECONDS"]))
    return Response(
        stream_with_context(body),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@claude.post("/claude/sessions")
def start():
    """Open Claude Code from a project's or a task's Claude tab (form)."""
    values = {key: request.form.get(key) or None for key in ("project_id", "task_id")}
    values["with_brief"] = request.form.get("with_brief") == "1"
    back = local_path(request.form.get("next")) or url_for("claude.index")
    try:
        session = terminal_core.start(validate(SessionStart, values))
    except FormErrors as exc:
        flash(" ".join(exc.errors.values()), "danger")
        return redirect(back)
    except terminal_core.TerminalError as exc:
        flash(str(exc), "danger")
        return redirect(back)
    return redirect(url_for("claude.session", session_id=session.id))


@claude.post("/claude/sessions/<uuid:session_id>/stop")
def stop(session_id: uuid.UUID):
    try:
        terminal_core.stop(session_id)
    except terminal_core.TerminalError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("claude.session", session_id=session_id))


@claude.post("/claude/resume")
def resume():
    """Open a conversation found on the machine in Cairn's terminal (form)."""
    try:
        session = terminal_core.resume(
            uuid.UUID(request.form.get("cli_session_id", "")), request.form.get("cwd", "")
        )
    except (ValueError, terminal_core.TerminalError) as exc:
        flash(
            str(exc)
            if isinstance(exc, terminal_core.TerminalError)
            else "This conversation id is not valid.",
            "danger",
        )
        return redirect(url_for("claude.index"))
    return redirect(url_for("claude.session", session_id=session.id))
