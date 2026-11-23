"""Search across projects, tasks and resources, for the command palette and pickers."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import String, cast, func, or_, select

from app.core.db_class.planning import Project, Task
from app.core.db_class.resource import Resource
from app.core.db_class.worklink import WorkLink
from app.core.extensions import db
from app.core.utils.listing import escape_like

PULL = re.compile(r"(?:github\.com/[\w.-]+/[\w.-]+/(?:pull|issues)/|#)(\d{1,7})\b|^(\d{1,7})$")
HEX = re.compile(r"^[0-9a-f]{6,32}$")


def _task_matches(query: str, pattern: str) -> list[Any]:
    """A task by its title or description; its id (whole or its first characters); a pull request,
    issue, branch, commit or folder linked to it, or to one of its subtasks' parents (D-086)."""
    found: list[Any] = [
        Task.title.ilike(pattern, escape="\\"),
        Task.description_md.ilike(pattern, escape="\\"),
    ]
    raw = query.strip().lower().replace("-", "")
    if HEX.match(raw):
        if len(raw) == 32:
            found.append(Task.id == uuid.UUID(raw))
        else:
            found.append(func.replace(cast(Task.id, String), "-", "").like(f"{raw}%"))
    linked = [WorkLink.ref.ilike(pattern, escape="\\")]
    if number := PULL.search(query.strip()):
        linked.append(WorkLink.ref.like(f"%#{number[1] or number[2]}"))
    if HEX.match(raw):
        linked.append(WorkLink.ref.like(f"{raw}%"))
    found.append(
        Task.id.in_(
            select(WorkLink.target_id).where(
                WorkLink.target_type == "task", WorkLink.deleted_at.is_(None), or_(*linked)
            )
        )
    )
    return found


def search(query: str, *, limit: int = 8, open_only: bool = False) -> dict[str, list[Any]]:
    """Projects, tasks and resources whose name, title (or address, file name) contains
    `query` (case-insensitive, literal); tasks also by description, id and the work linked to them."""
    query = " ".join(query.split())[:100]
    if not query:
        return {"projects": [], "tasks": [], "resources": []}
    pattern = f"%{escape_like(query)}%"
    projects = list(
        db.session.scalars(
            select(Project)
            .where(
                Project.deleted_at.is_(None),
                or_(Project.name.ilike(pattern, escape="\\"), Project.slug.ilike(pattern, escape="\\")),
            )
            .order_by(func.lower(Project.name))
            .limit(limit)
        )
    )
    task_query = select(Task).where(Task.deleted_at.is_(None), or_(*_task_matches(query, pattern)))
    if open_only:
        task_query = task_query.where(Task.is_open.is_(True))
    tasks = list(db.session.scalars(task_query.order_by(Task.is_open.desc(), Task.score.desc()).limit(limit)))
    resources = list(
        db.session.scalars(
            select(Resource)
            .where(
                Resource.deleted_at.is_(None),
                or_(
                    Resource.title.ilike(pattern, escape="\\"),
                    Resource.url.ilike(pattern, escape="\\"),
                    Resource.original_name.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(Resource.updated_at.desc())
            .limit(limit)
        )
    )
    return {"projects": projects, "tasks": tasks, "resources": resources}


def parent_titles(tasks: list[Task]) -> dict[Any, str]:
    """The title of each found subtask's parent, by its id."""
    wanted = {t.parent_id for t in tasks if t.parent_id}
    if not wanted:
        return {}
    return dict(db.session.execute(select(Task.id, Task.title).where(Task.id.in_(wanted))).all())
