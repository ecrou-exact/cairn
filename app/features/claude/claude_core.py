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
from app.features.claude import limits_core, main_core, terminal_core, transcript_core
from app.features.projects import projects_core


def _project_chip(project: Project) -> dict[str, str]:
    return {
        "id": str(project.id),
        "name": project.name,
        "slug": project.slug,
        "color": project.color,
        "icon": project.icon,
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


def outside() -> list[dict[str, Any]]:
    """The Claude Codes running outside Cairn, with the project of their folder."""
    sessions = transcript_core.outside_sessions(terminal_core.running_pids())
    for session in sessions:
        project = projects_core.by_folder(session["cwd"])
        session["project"] = _project_chip(project) if project else None
    return sessions


def overview(*, project_id: uuid.UUID | None = None, task_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Cairn's sessions (of a project or a task, or all) and, for the full view, the ones
    running outside Cairn."""
    rows = terminal_core.sessions(project_id=project_id, task_id=task_id)
    mine = [describe(row) for row in rows]
    instances = [
        describe(row)
        for row in terminal_core.sessions(kind="instance", project_id=project_id, limit=30)
        if terminal_core.is_running(row.id)
    ]
    found = [] if project_id or task_id else outside()
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
