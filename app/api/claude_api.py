"""Claude API (D-050): open Claude Code in a terminal, type in it, resize it, close it; the
overview of every session with its context use."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.claude import (
    CurrentPage,
    NewProjectStart,
    OutsideStop,
    ResumeStart,
    SessionLink,
    SessionStart,
    TerminalInput,
    TerminalResize,
)
from app.features.claude import claude_core, live_core, main_core, terminal_core, tools_core
from app.features.projects import projects_core

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
    except (terminal_core.TerminalError, projects_core.ProjectError) as exc:
        raise ApiError(str(exc), 409) from exc


@claude_api.get("/claude/sessions")
def list_sessions():
    """Cairn's sessions (`project` or `task` to narrow) and the ones running outside Cairn."""
    return jsonify(claude_core.overview(project_id=_uuid("project"), task_id=_uuid("task")))


@claude_api.post("/claude/sessions")
def start_session():
    session = _guard(terminal_core.start, body(SessionStart))
    return jsonify(session=claude_core.describe(session)), 201


@claude_api.get("/claude/live")
def live():
    """What every running Claude is doing, as a graph; `session`: one of them, in full."""
    return jsonify(live_core.graph(request.args.get("session") or None))


@claude_api.get("/claude/main")
def main_session():
    """Cairn's own Claude, if it runs."""
    session = main_core.running()
    return jsonify(session=claude_core.describe(session) if session else None)


@claude_api.post("/claude/main/restart")
def restart_main():
    """Close Cairn's own Claude and open it again on its conversation."""
    return jsonify(session=claude_core.describe(_guard(main_core.restart_main)))


@claude_api.post("/claude/main/stop")
def stop_main():
    _guard(main_core.stop_main)
    return jsonify(session=None)


@claude_api.post("/claude/page")
def current_page():
    """The page in front of the owner (what "here" means to Cairn's Claude)."""
    main_core.set_page(body(CurrentPage))
    return jsonify(ok=True)


@claude_api.post("/claude/main")
def open_main():
    """Cairn's own Claude: the one running, or opened now."""
    return jsonify(session=claude_core.describe(_guard(main_core.open_main)))


@claude_api.get("/claude/tasks")
def tasks_at_work():
    """The tasks a running Claude is on (the plan's graph lights them)."""
    return jsonify(tasks=live_core.at_work())


@claude_api.get("/claude/tools")
def tools():
    """What Claude can use, and what it used; `q`, `kind` (cairn, claude, server, skill)."""
    kind = request.args.get("kind", "")
    if kind and kind not in tools_core.KINDS:
        raise ApiError("'kind' must be one of: " + ", ".join(tools_core.KINDS), 422)
    return jsonify(tools_core.overview(request.args.get("q", "")[:100], kind))


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
    session = _guard(terminal_core.resume, data)
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


@claude_api.post("/claude/sessions/<uuid:session_id>/link")
def link(session_id: uuid.UUID):
    """Link a session to a project, a new project for a folder, or none."""
    session, reader = _guard(terminal_core.link, session_id, body(SessionLink))
    return jsonify(
        session=claude_core.describe(session), reader=claude_core.describe(reader) if reader else None
    )


@claude_api.post("/claude/outside/stop")
def stop_outside():
    """Close a Claude Code running outside Cairn."""
    _guard(terminal_core.stop_outside, body(OutsideStop))
    return jsonify(ok=True)
