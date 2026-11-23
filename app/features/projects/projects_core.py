"""Projects: create, edit, archive, delete / restore / purge, lists and stats (§2.1).

Deleting a project moves its tasks to the trash with it (one batch, one undo).
"""

from __future__ import annotations

import os
import re
import unicodedata
import uuid
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import IO, Any

from sqlalchemy import func, select

from app.core.db_class.base import utcnow
from app.core.db_class.planning import PROJECT_STATUSES, Project, Task
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, ProjectUpdate
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action
from app.features.comments import comments_core
from app.features.resources import resources_core, storage_core
from app.features.tasks import tasks_core
from app.features.tasks.dependencies_core import refresh_derived


class ProjectError(ValueError):
    pass


class ProjectNotFound(ProjectError):
    pass


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:80] or "project"


def _free_slug(wanted: str, exclude: uuid.UUID | None = None) -> str:
    slug, n = wanted, 2
    while True:
        taken = db.session.scalar(select(Project.id).where(Project.slug == slug, Project.id != exclude))
        if taken is None:
            return slug
        slug = f"{wanted[:76]}-{n}"
        n += 1


def get_project(project_id: uuid.UUID, *, deleted: bool = False) -> Project:
    project = db.session.get(Project, project_id)
    if project is None or project.is_deleted != deleted:
        raise ProjectNotFound(
            "This project does not exist." if not deleted else "This project is not in the trash."
        )
    return project


def by_slug(slug: str) -> Project:
    project = db.session.scalar(select(Project).where(Project.slug == slug, Project.deleted_at.is_(None)))
    if project is None:
        raise ProjectNotFound("This project does not exist.")
    return project


def by_folder(folder: str) -> Project | None:
    """The project whose local folder this is (same resolved path; case-insensitive on
    Windows), or None."""

    def norm(path: str) -> str:
        return os.path.normcase(str(Path(path).expanduser().resolve()))

    wanted = norm(folder)
    for project in db.session.scalars(
        select(Project).where(Project.deleted_at.is_(None), Project.local_path.is_not(None))
    ):
        if norm(project.local_path) == wanted:
            return project
    return None


def _changed(project: Project) -> None:
    publish("project.changed", {"id": str(project.id), "name": project.name})


def create(data: ProjectCreate) -> Project:
    values = data.model_dump(mode="json")
    values["slug"] = _free_slug(values["slug"] or slugify(values["name"]))
    with batch():
        project = Project(**values, created_by=current_actor())
        db.session.add(project)
        db.session.flush()
        log_action(
            "project.create",
            target_type="project",
            target_id=project.id,
            diff={k: [None, v] for k, v in values.items() if v not in (None, "", [])},
        )
        _changed(project)
    return project


def update(project_id: uuid.UUID, data: ProjectUpdate) -> Project:
    project = get_project(project_id)
    fields = data.model_dump(mode="json", exclude_unset=True)
    if fields.get("slug", "") is None:
        del fields["slug"]  # left empty in the form: it stays
    slug = fields.get("slug")
    if slug and slug != project.slug and _free_slug(slug, exclude=project.id) != slug:
        raise ProjectError(f"The slug '{fields['slug']}' is already used by another project.")
    if fields.get("name") is None and "name" in fields:
        raise ProjectError("A project needs a name.")
    diff = {
        key: [getattr(project, key), value] for key, value in fields.items() if getattr(project, key) != value
    }
    if not diff:
        return project
    with batch():
        for key in diff:
            setattr(project, key, fields[key])
        log_action("project.update", target_type="project", target_id=project.id, diff=diff)
        if "weight" in diff:
            db.session.flush()
            refresh_derived()
        _changed(project)
    return project


def delete(project_id: uuid.UUID) -> int:
    """Move the project and all its tasks to the trash; returns the number of tasks moved."""
    project = get_project(project_id)
    when = utcnow()
    with batch():
        roots = list(
            db.session.scalars(
                select(Task).where(
                    Task.project_id == project.id, Task.deleted_at.is_(None), Task.parent_id.is_(None)
                )
            )
        )
        moved = 0
        for root in roots:
            for task in [root, *tasks_core._descendants(root, deleted_at=None)]:
                tasks_core._delete_one(task, when)
                moved += 1
        # Subtasks whose parent is in another project stay where they are.
        for task in db.session.scalars(
            select(Task).where(Task.project_id == project.id, Task.deleted_at.is_(None))
        ):
            tasks_core._delete_one(task, when)
            moved += 1
        project.deleted_at = when
        log_action(
            "project.delete",
            target_type="project",
            target_id=project.id,
            diff={"deleted_at": [None, when.isoformat()]},
        )
        _changed(project)
        db.session.flush()
        refresh_derived()
    return moved


def restore(project_id: uuid.UUID) -> int:
    project = get_project(project_id, deleted=True)
    with batch():
        when = project.deleted_at
        log_action(
            "project.restore",
            target_type="project",
            target_id=project.id,
            diff={"deleted_at": [when.isoformat(), None]},
        )
        project.deleted_at = None
        tasks = list(
            db.session.scalars(select(Task).where(Task.project_id == project.id, Task.deleted_at == when))
        )
        for task in tasks:
            tasks_core._restore_one(task)
        _changed(project)
        db.session.flush()
        refresh_derived()
    return len(tasks)


IMAGE_MAX_BYTES = 10 * 1024 * 1024


def set_image(project_id: uuid.UUID, stream: IO[bytes]) -> Project:
    """The project's picture, a square without metadata; it replaces its icon everywhere."""
    project = get_project(project_id)
    name = storage_core.store_square(stream, IMAGE_MAX_BYTES)
    try:
        with batch():
            old, project.image_name = project.image_name, name
            log_action("project.image", target_type="project", target_id=project.id)
            _changed(project)
    except BaseException:
        storage_core.remove(name)
        raise
    if old:
        storage_core.remove(old)
    return project


def remove_image(project_id: uuid.UUID) -> Project:
    """Back to the icon."""
    project = get_project(project_id)
    old = project.image_name
    if old:
        with batch():
            project.image_name = None
            log_action("project.image_removed", target_type="project", target_id=project.id)
            _changed(project)
        storage_core.remove(old)
    return project


def purge(project_id: uuid.UUID) -> None:
    project = get_project(project_id, deleted=True)
    roots = list(
        db.session.scalars(select(Task).where(Task.project_id == project.id, Task.parent_id.is_(None)))
    )
    for task in roots:
        if task.is_deleted:
            tasks_core.purge(task.id)
    left = db.session.scalar(select(func.count()).select_from(Task).where(Task.project_id == project.id))
    if left:
        raise ProjectError("Some of its tasks are not in the trash or live under another project's tasks.")
    log_action(
        "project.purge",
        target_type="project",
        target_id=project.id,
        meta={"name": project.name},
        level="warning",
    )
    resources_core.forget_targets("project", [project.id])
    comments_core.forget_targets("project", [project.id])
    image = project.image_name
    db.session.delete(project)
    db.session.commit()
    if image:
        storage_core.remove(image)


def _undo_create(row) -> None:
    project = db.session.get(Project, uuid.UUID(row.target_id))
    if project is not None and not project.is_deleted:
        has_tasks = db.session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project.id, Task.deleted_at.is_(None))
        )
        if has_tasks:
            raise ProjectError("Tasks were added to this project since: delete it instead.")
        project.deleted_at = utcnow()
        log_action(
            "project.delete",
            target_type="project",
            target_id=project.id,
            diff={"deleted_at": [None, project.deleted_at.isoformat()]},
        )
        _changed(project)


def _undo_update(row) -> None:
    old = {key: values[0] for key, values in row.diff.items()}
    update(uuid.UUID(row.target_id), ProjectUpdate.model_validate(old))


def _undo_delete(row) -> None:
    project = db.session.get(Project, uuid.UUID(row.target_id))
    if project is not None and project.is_deleted:
        log_action(
            "project.restore",
            target_type="project",
            target_id=project.id,
            diff={"deleted_at": [project.deleted_at.isoformat(), None]},
        )
        project.deleted_at = None
        _changed(project)


def _undo_restore(row) -> None:
    project = db.session.get(Project, uuid.UUID(row.target_id))
    if project is not None and not project.is_deleted:
        project.deleted_at = utcnow()
        log_action(
            "project.delete",
            target_type="project",
            target_id=project.id,
            diff={"deleted_at": [None, project.deleted_at.isoformat()]},
        )
        _changed(project)


register_undo("project.create", _undo_create)
register_undo("project.update", _undo_update)
register_undo("project.delete", _undo_delete)
register_undo("project.restore", _undo_restore)


# -- reading ---------------------------------------------------------------------------------


def list_spec() -> ListSpec:
    return ListSpec(
        sortable={
            # by owner then name on GitHub (ecrou-exact/…, rulezet/…); those with no repository last
            "repo": func.lower(func.coalesce(Project.github_repo, "~" + Project.name)),
            "name": func.lower(Project.name),
            "created": Project.created_at,
            "updated": Project.updated_at,
            "status": Project.status,
        },
        default_sort="repo",
        default_direction="asc",
        tiebreak=Project.id,
        searchable=(Project.name, Project.slug, Project.description_md, Project.github_repo),
        filters=(
            FilterSpec(
                "status", "Status", Project.status, tuple((s, s.capitalize()) for s in PROJECT_STATUSES)
            ),
        ),
        views=("cards", "table"),
    )


def list_projects(args: Mapping[str, Any]) -> ListPage:
    """Starred projects first, whatever the sort; hidden ones only when asked (`hidden=1`, D-089)."""
    shown = args.get("hidden") == "1"
    query = (
        select(Project)
        .where(Project.deleted_at.is_(None), Project.hidden.is_(shown))
        .order_by(Project.starred.desc())
    )
    return run_list(list_spec(), query, args)


def pinned() -> list[Project]:
    """The projects pinned in the menu."""
    return list(
        db.session.scalars(
            select(Project)
            .where(Project.deleted_at.is_(None), Project.pinned.is_(True))
            .order_by(func.lower(Project.name))
        )
    )


def stats(project_ids: list[uuid.UUID], today: date | None = None) -> dict[uuid.UUID, dict[str, Any]]:
    """Open, done, blocked and overdue counts and the next due date, per project."""
    today = today or date.today()
    found: dict[uuid.UUID, dict[str, Any]] = {
        pid: {"open": 0, "closed": 0, "blocked": 0, "overdue": 0, "next_due": None} for pid in project_ids
    }
    if not project_ids:
        return found
    rows = db.session.execute(
        select(Task.project_id, Task.is_open, Task.blocked_by_count, Task.due_on).where(
            Task.project_id.in_(project_ids), Task.deleted_at.is_(None)
        )
    )
    for pid, is_open, blocked, due in rows:
        entry = found[pid]
        if not is_open:
            entry["closed"] += 1
            continue
        entry["open"] += 1
        entry["blocked"] += 1 if blocked else 0
        if due is not None:
            entry["overdue"] += 1 if due < today else 0
            if due >= today and (entry["next_due"] is None or due < entry["next_due"]):
                entry["next_due"] = due
    return found


def options() -> list[Project]:
    """Live projects for pickers, active ones first."""
    return list(
        db.session.scalars(
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by((Project.status == "archived").asc(), func.lower(Project.name))
        )
    )


def deleted_projects() -> list[Project]:
    return list(
        db.session.scalars(
            select(Project).where(Project.deleted_at.is_not(None)).order_by(Project.deleted_at.desc())
        )
    )


def hidden_count() -> int:
    return (
        db.session.scalar(select(func.count()).where(Project.deleted_at.is_(None), Project.hidden.is_(True)))
        or 0
    )
