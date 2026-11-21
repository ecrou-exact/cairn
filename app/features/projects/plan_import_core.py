"""Import a plan (a project and its tasks) from JSON, in one batch.

Format::

    {"project": {<ProjectCreate fields>},
     "tasks": [{"key": "graph", "title": "...", <TaskCreate fields>,
                "parent": "<key>", "blocked_by": ["<key>", ...]}]}

Idempotent: the project is matched by slug, tasks by title inside the project; what
already exists is left as it is, so a plan can be imported again after it grew. The
planning intake (Phase 6) builds on the same path.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.planning import DependencyCreate, ProjectCreate, TaskCreate
from app.core.utils.history import batch
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, tasks_core

PLAN_KEYS = {"key", "parent", "blocked_by"}


class PlanError(ValueError):
    pass


def import_plan(plan: dict[str, Any]) -> dict[str, int]:
    """Returns counts: tasks created, tasks already there, dependencies added."""
    project_data = ProjectCreate.model_validate(plan.get("project") or {})
    entries = plan.get("tasks") or []
    keys = [entry.get("key") for entry in entries]
    if len(set(keys)) != len(keys) or None in keys:
        raise PlanError("Every task needs a unique key.")
    for entry in entries:
        for ref in [entry.get("parent"), *entry.get("blocked_by", [])]:
            if ref is not None and ref not in keys:
                raise PlanError(f"Task '{entry['key']}' refers to an unknown key '{ref}'.")
    counts = {"created": 0, "existing": 0, "dependencies": 0}
    with batch():
        slug = project_data.slug or projects_core.slugify(project_data.name)
        project = db.session.scalar(select(Project).where(Project.slug == slug, Project.deleted_at.is_(None)))
        if project is None:
            project = projects_core.create(project_data.model_copy(update={"slug": slug}))
        existing = {
            t.title: t
            for t in db.session.scalars(
                select(Task).where(Task.project_id == project.id, Task.deleted_at.is_(None))
            )
        }
        made: dict[str, Task] = {}
        for entry in entries:  # parents must come before their subtasks in the file
            fields = {k: v for k, v in entry.items() if k not in PLAN_KEYS}
            if entry["title"] in existing:
                made[entry["key"]] = existing[entry["title"]]
                counts["existing"] += 1
                continue
            parent = entry.get("parent")
            if parent is not None and parent not in made:
                raise PlanError(f"Task '{entry['key']}' comes before its parent '{parent}' in the plan.")
            data = TaskCreate.model_validate(
                fields | {"project_id": project.id, "parent_id": made[parent].id if parent else None}
            )
            made[entry["key"]] = tasks_core.create(data)
            counts["created"] += 1
        for entry in entries:
            for ref in entry.get("blocked_by", []):
                try:
                    dependencies_core.add(
                        DependencyCreate(from_task_id=made[ref].id, to_task_id=made[entry["key"]].id)
                    )
                    counts["dependencies"] += 1
                except dependencies_core.DependencyError as exc:
                    if "already exists" not in str(exc):  # linked by an earlier import: fine
                        raise PlanError(f"Task '{entry['key']}': {exc}") from exc
    return counts
