"""Dependencies between tasks (PROJECT_BRIEF.md §2.3) and what follows from them:
cycle checks, blocked state, how many tasks a task unblocks, and the derived columns.

`blocks` and `follows` edges must stay acyclic (together). Dependencies are links, not
content: removing one deletes the row; the activity log keeps it so undo re-creates it.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import or_, select, update

from app.core.db_class.planning import Dependency, ExternalCondition, Project, Task
from app.core.extensions import db
from app.core.schema.planning import DependencyCreate
from app.core.utils.events import publish
from app.core.utils.graphs import path_between
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.tasks import score_core, workflow

ORDERING_KINDS = ("blocks", "follows")


class DependencyError(ValueError):
    pass


def _live_task(task_id: uuid.UUID) -> Task:
    task = db.session.get(Task, task_id)
    if task is None or task.is_deleted:
        raise DependencyError("This task does not exist.")
    return task


def _ordering_edges() -> dict[uuid.UUID, set[uuid.UUID]]:
    rows = db.session.execute(
        select(Dependency.from_task_id, Dependency.to_task_id).where(Dependency.kind.in_(ORDERING_KINDS))
    )
    edges: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for source, target in rows:
        edges[source].add(target)
    return edges


def add(data: DependencyCreate) -> Dependency:
    source, target = _live_task(data.from_task_id), _live_task(data.to_task_id)
    if source.id == target.id:
        raise DependencyError("A task cannot depend on itself.")
    duplicate = db.session.scalar(
        select(Dependency).where(
            Dependency.from_task_id == source.id,
            Dependency.to_task_id == target.id,
            Dependency.kind == data.kind,
        )
    )
    if duplicate is not None:
        raise DependencyError("This dependency already exists.")
    if data.kind in ORDERING_KINDS:
        cycle = path_between(_ordering_edges(), target.id, source.id)
        if cycle is not None:
            titles = {t.id: t.title for t in db.session.scalars(select(Task).where(Task.id.in_(cycle)))}
            loop = " → ".join(f"“{titles[i]}”" for i in [source.id, *cycle])
            raise DependencyError(f"This would create a cycle: {loop}.")
    with batch():
        dependency = Dependency(**data.model_dump())
        db.session.add(dependency)
        db.session.flush()
        log_action(
            "dependency.create", target_type="dependency", target_id=dependency.id, meta=_snapshot(dependency)
        )
        refresh_derived()
    return dependency


def _snapshot(dependency: Dependency) -> dict[str, str]:
    return {
        "from_task_id": str(dependency.from_task_id),
        "to_task_id": str(dependency.to_task_id),
        "kind": dependency.kind,
        "note": dependency.note,
    }


def remove(dependency_id: uuid.UUID) -> None:
    dependency = db.session.get(Dependency, dependency_id)
    if dependency is None:
        raise DependencyError("This dependency does not exist.")
    with batch():
        log_action(
            "dependency.delete", target_type="dependency", target_id=dependency.id, meta=_snapshot(dependency)
        )
        db.session.delete(dependency)
        db.session.flush()
        refresh_derived()


def _undo_create(row) -> None:
    dependency = db.session.get(Dependency, uuid.UUID(row.target_id))
    if dependency is not None:
        remove(dependency.id)


def _undo_delete(row) -> None:
    add(DependencyCreate(**row.meta))


register_undo("dependency.create", _undo_create)
register_undo("dependency.delete", _undo_delete)


# -- reading ---------------------------------------------------------------------------------


def for_task(task_id: uuid.UUID) -> dict[str, list[tuple[Dependency, Task]]]:
    """Every dependency of a task, grouped as the task page shows them, with the other task."""
    rows = db.session.execute(
        select(Dependency, Task)
        .join(
            Task,
            or_(
                (Dependency.to_task_id == task_id) & (Task.id == Dependency.from_task_id),
                (Dependency.from_task_id == task_id) & (Task.id == Dependency.to_task_id),
            ),
        )
        .where(
            or_(Dependency.from_task_id == task_id, Dependency.to_task_id == task_id),
            Task.deleted_at.is_(None),
        )
    ).all()
    groups: dict[str, list[tuple[Dependency, Task]]] = {
        "blocked_by": [],
        "blocks": [],
        "follows": [],
        "followed_by": [],
        "relates": [],
        "duplicates": [],
    }
    for dependency, other in rows:
        incoming = dependency.to_task_id == task_id
        if dependency.kind == "blocks":
            groups["blocked_by" if incoming else "blocks"].append((dependency, other))
        elif dependency.kind == "follows":
            groups["follows" if incoming else "followed_by"].append((dependency, other))
        else:
            groups[dependency.kind].append((dependency, other))
    return groups


def blocking_chain(task_id: uuid.UUID) -> list[tuple[int, Task]]:
    """Open tasks that block this one, directly or further up, as (depth, task), depth first."""
    rows = db.session.execute(
        select(Dependency.from_task_id, Dependency.to_task_id).where(Dependency.kind == "blocks")
    ).all()
    blockers: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for source, target in rows:
        blockers[target].append(source)
    tasks = {
        t.id: t
        for t in db.session.scalars(select(Task).where(Task.deleted_at.is_(None), Task.is_open.is_(True)))
    }
    chain: list[tuple[int, Task]] = []
    seen: set[uuid.UUID] = set()

    def walk(node: uuid.UUID, depth: int) -> None:
        for blocker in blockers.get(node, ()):
            if blocker in tasks and blocker not in seen:
                seen.add(blocker)
                chain.append((depth, tasks[blocker]))
                walk(blocker, depth + 1)

    walk(task_id, 1)
    return chain


# -- derived columns -------------------------------------------------------------------------


def refresh_derived(today: date | None = None) -> int:
    """Recompute is_open, blocked_by_count, unblocks_count and score for every task.

    `blocked_by_count` counts open blocking tasks and open external conditions.

    Runs after every planning change (a few ms for hundreds of tasks) and daily (deadlines
    and age move with time). Writes only what changed, and keeps `updated_at`: derived
    values are not an edit by the owner. Returns how many tasks changed.
    """
    today = today or date.today()
    weights = get_setting("tasks.score_weights")
    kinds = {s["key"]: s["kind"] for s in workflow.statuses()}
    tasks = list(db.session.scalars(select(Task).where(Task.deleted_at.is_(None))))
    project_weights = dict(db.session.execute(select(Project.id, Project.weight)).all())
    is_open = {t.id: kinds.get(t.status, "open") in workflow.OPEN_KINDS for t in tasks}

    successors: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    blocked_by: dict[uuid.UUID, int] = defaultdict(int)
    for source, target in db.session.execute(
        select(Dependency.from_task_id, Dependency.to_task_id).where(Dependency.kind == "blocks")
    ):
        if source in is_open and target in is_open:
            successors[source].add(target)
            if is_open[source]:
                blocked_by[target] += 1

    for condition in db.session.scalars(
        select(ExternalCondition).where(ExternalCondition.resolved_at.is_(None))
    ):
        if condition.task_id in is_open and condition.is_waiting(today):
            blocked_by[condition.task_id] += 1

    def unblocks(start: uuid.UUID) -> int:
        seen: set[uuid.UUID] = set()
        stack = list(successors.get(start, ()))
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(successors.get(node, ()))
        return sum(1 for node in seen if is_open[node])

    changed = 0
    for task in tasks:
        values: dict[str, Any] = {
            "is_open": is_open[task.id],
            "blocked_by_count": blocked_by[task.id] if is_open[task.id] else 0,
            "unblocks_count": unblocks(task.id) if is_open[task.id] else 0,
        }
        if values["is_open"]:
            score, explain = score_core.compute(
                priority=task.priority,
                importance=task.importance,
                urgency=task.urgency,
                due_on=task.due_on,
                hard_deadline=task.hard_deadline,
                estimate_hours=task.estimate_hours,
                created_on=task.created_at.date(),
                unblocks=values["unblocks_count"],
                project_weight=project_weights.get(task.project_id, 1.0),
                weights=weights,
                today=today,
            )
        else:
            score, explain = 0.0, []
        values |= {"score": score, "score_explain": explain}
        if any(getattr(task, key) != value for key, value in values.items()):
            changed += 1
            db.session.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(**values, updated_at=Task.updated_at)
                .execution_options(synchronize_session="fetch")
            )
    if changed:
        publish("task.derived", {"changed": changed})
    return changed
