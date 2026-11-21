"""Task templates (PROJECT_BRIEF.md §5): recurring shapes of work, from `tasks.templates`."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.db_class.planning import Task
from app.core.schema.planning import DependencyCreate, TaskCreate
from app.core.utils.history import batch
from app.core.utils.settings import get_setting
from app.features.tasks import dependencies_core, tasks_core, workflow


def templates() -> dict[str, dict[str, Any]]:
    return dict(get_setting("tasks.templates"))


def instantiate(key: str, title: str, *, project_id: uuid.UUID | None = None) -> Task:
    """The task, its checklist and subtasks, in one batch; sequential subtasks are chained
    with `follows` so they come one after the other."""
    template = templates().get(key)
    if template is None:
        raise tasks_core.TaskError("This template does not exist.")
    known_types = workflow.types()
    if template["type"] not in known_types or any(s["type"] not in known_types for s in template["subtasks"]):
        raise tasks_core.TaskError("This template uses a task type that no longer exists.")
    with batch():
        task = tasks_core.create(
            TaskCreate(
                title=title.strip() or template["label"],
                project_id=project_id,
                type=template["type"],
                priority=template["priority"],
                tags=template["tags"],
                checklist=[{"text": text, "done": False} for text in template["checklist"]],
                acceptance_md=template["acceptance_md"],
            )
        )
        previous = None
        for step in template["subtasks"]:
            sub = tasks_core.create(TaskCreate(title=step["title"], type=step["type"], parent_id=task.id))
            if template["sequential"] and previous is not None:
                dependencies_core.add(
                    DependencyCreate(from_task_id=previous.id, to_task_id=sub.id, kind="follows")
                )
            previous = sub
    return task
