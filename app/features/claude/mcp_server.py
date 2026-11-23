"""Cairn's MCP server (D-052): Claude Code, opened from Cairn, sees and changes the plan.

Claude Code starts it over stdio for each session Cairn opens (`--mcp-config`, written next
to the rules file): `python manage.py mcp`, with `CAIRN_MCP_SESSION` naming the session.
Every tool calls the same core functions as the pages and the API (one implementation per
behaviour); changes are made as `claude:<session>`, logged and undoable like the owner's.
Reading tools are allowed up front in that session; changes go through Claude Code's own
permission prompt, so the owner approves them in the terminal.

Built on `mcp` 2.x (`mcp.server.mcpserver.MCPServer`; FastMCP's successor).
"""

from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Any, Literal

from flask import Flask
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.comments import CommentCreate
from app.core.schema.planning import DependencyCreate, ProjectUpdate, TaskCreate
from app.core.utils.actor import acting_as
from app.features.comments import comments_core
from app.features.projects import projects_core
from app.features.tasks import brief_core, dependencies_core, tasks_core, workflow

SERVER_NAME = "cairn"
READ_TOOLS = ("cairn_overview", "list_tasks", "get_task", "next_tasks")
WRITE_TOOLS = ("update_project", "create_task", "set_task_status", "link_tasks", "comment_on_task")

INSTRUCTIONS = (
    "Cairn is the owner's planning workspace: projects, tasks with dependencies, a score that "
    "says what to do next. Use these tools to read the plan and to keep it true as you work: "
    "move the task you work on to its new status, create the follow-up tasks you discover, "
    "link what blocks what, leave a comment with what you did. Ids are UUIDs; a project can "
    "also be named by its name or slug."
)


class CairnToolError(ValueError):
    pass


def _task_line(task: Task) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "title": task.title,
        "project": task.project.name if task.project else None,
        "status": task.status,
        "priority": task.priority,
        "due": task.due_on.isoformat() if task.due_on else None,
        "score": round(task.score),
        "blocked": task.is_open and task.blocked_by_count > 0,
        "unblocks": task.unblocks_count,
        "parent_id": str(task.parent_id) if task.parent_id else None,
    }


def _project(ref: str | None) -> Project | None:
    """A project by id, slug or name (case-insensitive); None for no reference."""
    if not ref:
        return None
    try:
        found = db.session.get(Project, uuid.UUID(ref))
    except ValueError:
        found = db.session.scalar(
            select(Project).where(
                Project.deleted_at.is_(None),
                (Project.slug == ref.lower()) | (func.lower(Project.name) == ref.lower()),
            )
        )
    if found is None or found.is_deleted:
        raise CairnToolError(f"No project “{ref}”. Call cairn_overview to see the projects.")
    return found


def _task(ref: str) -> Task:
    try:
        return tasks_core.get_task(uuid.UUID(ref))
    except (ValueError, tasks_core.TaskNotFound) as exc:
        raise CairnToolError(f"No task with id “{ref}”. Use list_tasks to find it.") from exc


def build(app: Flask, session_id: str | None) -> MCPServer:
    """The MCP server for one Claude session, working inside `app`."""
    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    actor = f"claude:{session_id}" if session_id else "claude:outside"

    def run(work):
        with app.app_context(), acting_as(actor):
            try:
                return work()
            except (
                CairnToolError,
                projects_core.ProjectError,
                tasks_core.TaskError,
                tasks_core.TaskNotFound,
                dependencies_core.DependencyError,
                comments_core.CommentError,
            ) as exc:
                raise ToolError(str(exc)) from exc  # a deliberate refusal: Claude gets the reason

    def session_project() -> Project | None:
        if not session_id:
            return None
        row = db.session.get(ClaudeSession, uuid.UUID(session_id))
        return db.session.get(Project, row.project_id) if row and row.project_id else None

    @server.tool()
    def cairn_overview() -> dict[str, Any]:
        """The plan at a glance: this session's project, every project with what is open,
        blocked and late, and the five tasks to do next. Start here."""

        def work():
            here = session_project()
            stats = projects_core.stats([p.id for p in projects_core.options()])
            projects = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "slug": p.slug,
                    "folder": p.local_path,
                    "open": stats[p.id]["open"],
                    "blocked": stats[p.id]["blocked"],
                    "late": stats[p.id]["overdue"],
                }
                for p in projects_core.options()
            ]
            return {
                "this_session_project": here.name if here else None,
                "projects": projects,
                "next_tasks": [_task_line(t) for t in tasks_core.next_actions(limit=5)],
                "statuses": [s["key"] for s in workflow.statuses()],
            }

        return run(work)

    @server.tool()
    def list_tasks(
        project: str | None = None,
        state: Literal["open", "actionable", "blocked", "overdue", "closed"] | None = "open",
        search: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Tasks, best score first. `project`: id, slug or name (default: this session's
        project, if any). `state`: open (default), actionable, blocked, overdue, closed.
        `search`: words in the title or description."""

        def work():
            chosen = _project(project) or session_project()
            args = {"sort": "score", "dir": "desc", "per_page": str(max(1, min(limit, 100)))}
            if state:
                args["state"] = state
            if search:
                args["q"] = search
            page = tasks_core.list_tasks(args, project_id=chosen.id if chosen else None)
            return [_task_line(t) for t in page.items]

        return run(work)

    @server.tool()
    def get_task(task_id: str) -> str:
        """A task's full brief (Markdown): description, acceptance criteria, checklist,
        instructions and corrections for Claude, dependencies, resources."""
        return run(lambda: brief_core.task_brief(_task(task_id)))

    @server.tool()
    def next_tasks(project: str | None = None, limit: int = 7) -> list[dict[str, Any]]:
        """What to do now: actionable tasks (open, not blocked, not waiting), best score
        first, in one project or everywhere."""

        def work():
            chosen = _project(project)
            return [
                _task_line(t)
                for t in tasks_core.next_actions(
                    limit=max(1, min(limit, 30)), project_id=chosen.id if chosen else None
                )
            ]

        return run(work)

    @server.tool()
    def update_project(
        project: str | None = None,
        description: str | None = None,
        stack: list[str] | None = None,
        tags: list[str] | None = None,
        github_repo: str | None = None,
        default_branch: str | None = None,
    ) -> dict[str, Any]:
        """Fill or correct a project after reading it (default: this session's project): what it
        is (Markdown), its stack, tags, GitHub repository (owner/name) and main branch. Only what
        you give changes."""

        def work():
            chosen = _project(project) or session_project()
            if chosen is None:
                raise CairnToolError(
                    "This session has no project yet: say which, or ask the owner to link it."
                )
            given = {
                "description_md": description,
                "stack": stack,
                "tags": tags,
                "github_repo": github_repo,
                "default_branch": default_branch,
            }
            try:
                data = ProjectUpdate(**{key: value for key, value in given.items() if value is not None})
            except ValidationError as exc:
                raise CairnToolError(
                    "; ".join(f"{err['loc'][0] if err['loc'] else ''}: {err['msg']}" for err in exc.errors())
                ) from exc
            updated = projects_core.update(chosen.id, data)
            return {"id": str(updated.id), "name": updated.name, "changed": sorted(data.model_fields_set)}

        return run(work)

    @server.tool()
    def create_task(
        title: str,
        project: str | None = None,
        parent_id: str | None = None,
        description: str = "",
        priority: Literal["critical", "high", "medium", "low"] = "medium",
        due: str | None = None,
        estimate_hours: float | None = None,
    ) -> dict[str, Any]:
        """Create a task (a follow-up, a bug found on the way, a subtask with `parent_id`).
        `project` defaults to this session's project; `due` is YYYY-MM-DD."""

        def work():
            chosen = _project(project) or session_project()
            parent = _task(parent_id) if parent_id else None
            task = tasks_core.create(
                TaskCreate(
                    title=title,
                    description_md=description,
                    project_id=(parent.project_id if parent else None) or (chosen.id if chosen else None),
                    parent_id=parent.id if parent else None,
                    priority=priority,
                    due_on=date.fromisoformat(due) if due else None,
                    estimate_hours=estimate_hours,
                )
            )
            return _task_line(task)

        return run(work)

    @server.tool()
    def set_task_status(task_id: str, status: str) -> dict[str, Any]:
        """Move a task to another status (see cairn_overview for the statuses; the workflow
        decides which moves are allowed): e.g. in_progress when you start, done when finished."""
        return run(lambda: _task_line(tasks_core.set_status(_task(task_id).id, status)))

    @server.tool()
    def link_tasks(
        first_id: str, then_id: str, kind: Literal["blocks", "follows", "relates"] = "blocks"
    ) -> dict[str, Any]:
        """Say that `first_id` must be done before `then_id` (kind blocks), comes before it
        (follows), or is related. Refused if it would create a loop."""

        def work():
            first, then = _task(first_id), _task(then_id)
            dependencies_core.add(DependencyCreate(from_task_id=first.id, to_task_id=then.id, kind=kind))
            return {"linked": True, "first": first.title, "then": then.title, "kind": kind}

        return run(work)

    @server.tool()
    def comment_on_task(task_id: str, text: str, correction: bool = False) -> dict[str, Any]:
        """Leave a comment on a task (Markdown): what you did, what is left. `correction`:
        a lesson every later Claude run on this task should get."""

        def work():
            task = _task(task_id)
            comment = comments_core.create(
                CommentCreate(
                    target_type="task",
                    target_id=task.id,
                    kind="correction" if correction else "comment",
                    body_md=text,
                )
            )
            return {"comment_id": str(comment.id), "task": task.title}

        return run(work)

    return server


def serve() -> None:
    """`python manage.py mcp`: the server over stdio, for the session named in the env."""
    from app import create_app

    app = create_app()
    build(app, os.environ.get("CAIRN_MCP_SESSION")).run("stdio")
