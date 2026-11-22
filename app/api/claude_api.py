"""Claude API (D-050): open Claude Code in a terminal, type in it, resize it, close it; the
overview of every session with its context use."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.claude import NewProjectStart, ResumeStart, SessionStart, TerminalInput, TerminalResize
from app.features.claude import claude_core, terminal_core

claude_api = api_blueprint("claude_api")


def _uuid(name: str) -> uuid.UUID | None:
    raw = request.args.get(name)
    try:
        return uuid.UUID(raw) if raw else None
    except ValueError as exc:
        raise ApiError(f"'{name}' must be an id.", 422) from exc


def _guard(action, *args):
    try:
        return action(*args)
    except terminal_core.TerminalError as exc:
        raise ApiError(str(exc), 409) from exc


@claude_api.get("/claude/sessions")
def list_sessions():
    """Cairn's sessions (`project` or `task` to narrow) and the ones running outside Cairn."""
    return jsonify(claude_core.overview(project_id=_uuid("project"), task_id=_uuid("task")))


@claude_api.post("/claude/sessions")
def start_session():
    session = _guard(terminal_core.start, body(SessionStart))
    return jsonify(session=claude_core.describe(session)), 201


@claude_api.get("/claude/targets")
def targets():
    """What the launcher offers: presets and projects."""
    return jsonify(claude_core.targets())


@claude_api.post("/claude/projects")
def new_project():
    """Create a project and its folder, then Claude Code in it to set it up."""
    session = _guard(terminal_core.start_new_project, body(NewProjectStart))
    return jsonify(session=claude_core.describe(session)), 201


@claude_api.post("/claude/resume")
def resume():
    """Reopen a Claude Code conversation in Cairn (one started outside, or one that ended)."""
    data = body(ResumeStart)
    session = _guard(terminal_core.resume, data.cli_session_id, data.cwd, data.cols, data.rows)
    return jsonify(session=claude_core.describe(session)), 201


@claude_api.post("/claude/sessions/<uuid:session_id>/input")
def type_in(session_id: uuid.UUID):
    _guard(terminal_core.write, session_id, body(TerminalInput).data)
    return jsonify(ok=True)


@claude_api.post("/claude/sessions/<uuid:session_id>/resize")
def resize(session_id: uuid.UUID):
    size = body(TerminalResize)
    _guard(terminal_core.resize, session_id, size.cols, size.rows)
    return jsonify(ok=True)


@claude_api.post("/claude/sessions/<uuid:session_id>/stop")
def stop(session_id: uuid.UUID):
    _guard(terminal_core.stop, session_id)
    return jsonify(ok=True)
