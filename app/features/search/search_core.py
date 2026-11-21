"""Search across projects, tasks and resources, for the command palette and pickers."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select

from app.core.db_class.planning import Project, Task
from app.core.db_class.resource import Resource
from app.core.extensions import db
from app.core.utils.listing import escape_like


def search(query: str, *, limit: int = 8, open_only: bool = False) -> dict[str, list[Any]]:
    """Projects, tasks and resources whose name, title (or address, file name) contains
    `query` (case-insensitive, literal)."""
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
    task_query = select(Task).where(Task.deleted_at.is_(None), Task.title.ilike(pattern, escape="\\"))
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
