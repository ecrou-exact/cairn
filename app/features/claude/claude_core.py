"""The Claude overview (D-050): every Claude Code session on this machine, where it runs,
how full its context is. Cairn's own sessions (with their terminal) and the ones started
outside Cairn (seen by their process)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.utils.settings import get_setting
from app.features.claude import limits_core, main_core, terminal_core, transcript_core
from app.features.projects import place_core


def _project_chip(project: Project) -> dict[str, str]:
    return {
        "id": str(project.id),
        "name": project.name,
        "slug": project.slug,
        "color": project.color,
        "icon": project.icon,
        "image_url": project.image_url,
    }


def describe(session: ClaudeSession) -> dict[str, Any]:
    project = db.session.get(Project, session.project_id) if session.project_id else None
    task = db.session.get(Task, session.task_id) if session.task_id else None
    usage = (
        transcript_core.session_usage(session.cwd, str(session.cli_session_id))
        if session.kind == "claude"
        else transcript_core.Usage()
    )
    from app.features.instances import instances_core  # instances build on this module

    running = terminal_core.is_running(session.id)
    return {
        "id": str(session.id),
        "kind": session.kind,
        "port": session.port,
        "ports": instances_core.listening_ports(session.pid)
        if running and session.kind == "instance"
        else [],
        "url": f"/claude/sessions/{session.id}",
        "title": usage.title or session.title,
        "label": session.title,
        "main": main_core.is_main(session),
        "cwd": session.cwd,
        "cli_session_id": str(session.cli_session_id),
        "status": session.status,
        "running": running,
        "started": session.created_at.isoformat(),
        "ended": session.ended_at.isoformat() if session.ended_at else None,
        "exit_code": session.exit_code,
        "end_reason": session.end_reason,
        "project": _project_chip(project) if project else None,
        "task": {"id": str(task.id), "title": task.title} if task else None,
        "usage": usage.as_dict(),
        "log": terminal_core.preview(session.id) if running and session.kind == "instance" else [],
    }


def ended_log(session: ClaudeSession) -> str:
    """The end of an instance's log, once it has ended (colours left out)."""
    if session.kind != "instance" or terminal_core.is_running(session.id):
        return ""
    from app.features.instances import survivor  # instances build on this module

    text = terminal_core.ANSI.sub("", survivor.tail(session.id)) if survivor.available() else ""
    return text.replace("\r\n", "\n")


def outside() -> list[dict[str, Any]]:
    """The Claude Codes running outside Cairn, with the project of their folder."""
    sessions = transcript_core.outside_sessions(terminal_core.running_pids())
    for session in sessions:
        project = place_core.project_for(session["cwd"])
        session["project"] = _project_chip(project) if project else None
    return sessions


def overview(*, project_id: uuid.UUID | None = None, task_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Cairn's sessions (of a project or a task, or all) and the ones running outside Cairn: all
    of them, or the project's."""
    rows = terminal_core.sessions(project_id=project_id, task_id=task_id)
    mine = [describe(row) for row in rows]
    instances = [
        describe(row)
        for row in terminal_core.sessions(kind="instance", project_id=project_id, limit=30)
        if terminal_core.is_running(row.id)
    ]
    if task_id:
        found = []
    elif project_id:  # the project's own Claude Codes of the owner's terminals, whatever the copy (D-082)
        found = [s for s in outside() if s["project"] and s["project"]["id"] == str(project_id)]
    else:
        found = outside()
    return {
        "sessions": mine,
        "outside": found,
        "instances": instances,
        "limits": limits_core.limits(),
        "notes": main_core.waiting(),
        "running": sum(1 for s in mine if s["running"]) + len(found),
    }


def targets() -> dict[str, Any]:
    """What the launcher offers: the presets, and the projects (with whether Claude can open
    in their folder)."""
    projects = db.session.scalars(
        select(Project)
        .where(Project.deleted_at.is_(None), Project.status != "archived")
        .order_by(Project.name)
    )
    return {
        "limits": limits_core.limits(),
        "worktrees": bool(get_setting("claude.worktrees")),
        "presets": [{"key": key, **info} for key, info in terminal_core.PRESET_INFO.items()],
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "color": p.color,
                "icon": p.icon,
                "folder": p.local_path or "",
                "edit": f"/projects/{p.slug}/edit",
            }
            for p in projects
        ],
    }


# -- clean up (D-092) -----------------------------------------------------------------------------


def clear_ended() -> int:
    """Take the ended Claude sessions and log terminals off Cairn's pages, in one undoable step.
    Their conversations stay on the machine: Claude Code keeps them, `claude --resume` finds them."""
    from app.core.db_class.base import utcnow
    from app.core.utils.history import batch
    from app.core.utils.logger import log_action

    rows = list(
        db.session.scalars(
            select(ClaudeSession).where(
                ClaudeSession.deleted_at.is_(None),
                ClaudeSession.kind.in_(("claude", "log")),
                ClaudeSession.status == "ended",
            )
        )
    )
    rows = [row for row in rows if not terminal_core.is_running(row.id)]
    if not rows:
        return 0
    with batch():
        now = utcnow()
        for row in rows:
            row.deleted_at = now
        log_action("claude.clear_ended", target_type="claude", meta={"sessions": [str(r.id) for r in rows]})
    return len(rows)


def _undo_clear(row) -> None:
    for raw in (row.meta or {}).get("sessions", []):
        found = db.session.get(ClaudeSession, uuid.UUID(raw))
        if found is not None:
            found.deleted_at = None


def _register() -> None:
    from app.core.utils.history import register_undo

    register_undo("claude.clear_ended", _undo_clear)


_register()
