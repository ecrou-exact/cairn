"""Links between projects (D-044): `from_project` passes before `to_project`.

They decide the order of the plan of projects (Projects page); they never block tasks.
Like task dependencies they are links, not content: removing one deletes the row, and the
activity log keeps it so undo re-creates it. They must stay acyclic.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import or_, select

from app.core.db_class.planning import Project, ProjectLink
from app.core.extensions import db
from app.core.schema.planning import ProjectLinkCreate
from app.core.utils.events import publish
from app.core.utils.graphs import path_between
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action


class ProjectLinkError(ValueError):
    pass


def _live(project_id: uuid.UUID) -> Project:
    project = db.session.get(Project, project_id)
    if project is None or project.is_deleted:
        raise ProjectLinkError("This project does not exist.")
    return project


def _edges() -> dict[uuid.UUID, set[uuid.UUID]]:
    edges: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for source, target in db.session.execute(select(ProjectLink.from_project_id, ProjectLink.to_project_id)):
        edges[source].add(target)
    return edges


def _snapshot(link: ProjectLink) -> dict[str, str]:
    return {
        "from_project_id": str(link.from_project_id),
        "to_project_id": str(link.to_project_id),
        "note": link.note,
    }


def _changed(*projects: Project) -> None:
    for project in projects:
        publish("project.changed", {"id": str(project.id), "name": project.name})


def add(data: ProjectLinkCreate) -> ProjectLink:
    first, then = _live(data.from_project_id), _live(data.to_project_id)
    if first.id == then.id:
        raise ProjectLinkError("A project cannot pass before itself.")
    duplicate = db.session.scalar(
        select(ProjectLink).where(
            ProjectLink.from_project_id == first.id, ProjectLink.to_project_id == then.id
        )
    )
    if duplicate is not None:
        raise ProjectLinkError(f"“{first.name}” already passes before “{then.name}”.")
    loop = path_between(_edges(), then.id, first.id)
    if loop is not None:
        names = {p.id: p.name for p in db.session.scalars(select(Project).where(Project.id.in_(loop)))}
        cycle = " → ".join(f"“{names[i]}”" for i in [first.id, *loop])
        raise ProjectLinkError(f"This would create a cycle: {cycle}.")
    with batch():
        link = ProjectLink(**data.model_dump())
        db.session.add(link)
        db.session.flush()
        log_action("project_link.create", target_type="project_link", target_id=link.id, meta=_snapshot(link))
        _changed(first, then)
    return link


def remove(link_id: uuid.UUID) -> None:
    link = db.session.get(ProjectLink, link_id)
    if link is None:
        raise ProjectLinkError("This link does not exist.")
    projects = [
        p
        for p in (db.session.get(Project, link.from_project_id), db.session.get(Project, link.to_project_id))
        if p
    ]
    with batch():
        log_action("project_link.delete", target_type="project_link", target_id=link.id, meta=_snapshot(link))
        db.session.delete(link)
        db.session.flush()
        _changed(*projects)


def _undo_create(row) -> None:
    if db.session.get(ProjectLink, uuid.UUID(row.target_id)) is not None:
        remove(uuid.UUID(row.target_id))


def _undo_delete(row) -> None:
    add(ProjectLinkCreate(**row.meta))


register_undo("project_link.create", _undo_create)
register_undo("project_link.delete", _undo_delete)


def for_project(project_id: uuid.UUID) -> dict[str, list[tuple[ProjectLink, Project]]]:
    """The projects that pass before this one (`before`) and after it (`after`)."""
    rows = db.session.execute(
        select(ProjectLink, Project)
        .join(
            Project,
            or_(
                (ProjectLink.to_project_id == project_id) & (Project.id == ProjectLink.from_project_id),
                (ProjectLink.from_project_id == project_id) & (Project.id == ProjectLink.to_project_id),
            ),
        )
        .where(Project.deleted_at.is_(None))
    ).all()
    groups: dict[str, list[tuple[ProjectLink, Project]]] = {"before": [], "after": []}
    for link, other in rows:
        groups["before" if link.to_project_id == project_id else "after"].append((link, other))
    return groups
