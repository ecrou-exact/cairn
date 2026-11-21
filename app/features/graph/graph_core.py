"""The plan as a graph (PROJECT_BRIEF.md §4): tasks as nodes; dependencies and subtasks as edges.

Returned in Pivotick's raw shape (`{nodes: [{id, data}], edges: [{id, from, to, data}]}`),
with everything a card needs already resolved (labels, colours, relative dates), so the
browser only draws.

The **critical path** is the chain of open tasks linked by `blocks` with the most work
left (estimate minus time spent; an unestimated task counts as one hour and is flagged):
the work that decides when the last of them can be done.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select

from app.core.db_class.planning import Dependency, Task
from app.core.extensions import db
from app.core.utils.template_filters import relative_day
from app.features.tasks import workflow

UNKNOWN_HOURS = 1.0

# The plan is drawn left to right on a grid of cards (graph units = CSS px at zoom 1).
CARD_W, CARD_H = 224, 96
COL_GAP, ROW_GAP = 104, 30
ORDERING = ("blocks", "follows")


def _barycentre(tid, column, position, neighbours, rank) -> float:
    """Mean row of the cards a card is linked to in other columns (its own row if none)."""
    linked = [position[n] for n in neighbours[tid] if rank[n] != column]
    return sum(linked) / len(linked) if linked else position[tid]


def plan_layout(
    tasks: dict[uuid.UUID, Task],
    ordering: list[tuple[uuid.UUID, uuid.UUID]],
    parents: dict[uuid.UUID, uuid.UUID] | None = None,
) -> dict[uuid.UUID, tuple[float, float]]:
    """Where each card goes: a column per step of the plan, read from left to right.

    `ordering` lists (first, then) pairs among `tasks`; `parents` maps a shown subtask to its
    shown parent. A task stands right of everything that must come first: what blocks it or
    comes before it, what blocks its parent tasks (a subtask cannot start before its parent
    can), and its own subtasks (a parent is done when they are). Rows group a column by
    project, then a few sweeps place each card near the cards it is linked to.
    """
    parents = parents or {}
    before: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for first, then in ordering:
        before[then].add(first)
    for child, parent in parents.items():
        before[parent].add(child)

    def inherited(task_id: uuid.UUID) -> set[uuid.UUID]:
        found, parent, seen = set(before[task_id]), parents.get(task_id), set()
        while parent is not None and parent not in seen:
            seen.add(parent)
            found |= {b for b in before[parent] if b != task_id and parents.get(b) != parent}
            parent = parents.get(parent)
        return found

    preds = {tid: {p for p in inherited(tid) if p in tasks and p != tid} for tid in tasks}
    rank = dict.fromkeys(tasks, 0)
    for _ in range(len(tasks)):  # longest path; stops early, and is bounded if data loops
        changed = False
        for tid, ps in preds.items():
            best = max((rank[p] + 1 for p in ps), default=0)
            if best > rank[tid]:
                rank[tid], changed = best, True
        if not changed:
            break

    columns: dict[int, list[uuid.UUID]] = defaultdict(list)
    for tid, r in rank.items():
        columns[r].append(tid)

    def base_key(tid: uuid.UUID):
        task = tasks[tid]
        return (task.project.name.lower() if task.project else "~", -task.score, task.title.lower())

    for col in columns.values():
        col.sort(key=base_key)
    neighbours: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for tid, ps in preds.items():
        for p in ps:
            neighbours[tid].add(p)
            neighbours[p].add(tid)
    for _sweep in range(4):  # barycentre ordering, alternating left-to-right and back
        order = sorted(columns) if _sweep % 2 == 0 else sorted(columns, reverse=True)
        position = {tid: i for col in columns.values() for i, tid in enumerate(col)}
        for c in order:
            columns[c].sort(
                key=lambda tid, c=c, pos=position: (_barycentre(tid, c, pos, neighbours, rank), base_key(tid))
            )
            position.update({tid: i for i, tid in enumerate(columns[c])})

    tallest = max((len(col) for col in columns.values()), default=0)
    placed = {}
    for c, col in columns.items():
        offset = (tallest - len(col)) * (CARD_H + ROW_GAP) / 2  # columns centred on one axis
        for i, tid in enumerate(col):
            placed[tid] = (c * (CARD_W + COL_GAP), offset + i * (CARD_H + ROW_GAP))
    return placed


def _remaining(task: Task) -> tuple[float, bool]:
    if task.estimate_hours is None:
        return UNKNOWN_HOURS, True
    return max(task.estimate_hours - task.tracked_seconds / 3600, 0.0), False


def critical_path(
    tasks: dict[uuid.UUID, Task],
    blocks: list[tuple[uuid.UUID, uuid.UUID]],
    remaining=None,
) -> dict[str, Any]:
    """Longest chain of open tasks along `blocks` edges, by remaining hours (the graph is
    acyclic: dependencies_core refuses cycles). `remaining(task)` → (hours, unknown)."""
    remaining = remaining or _remaining
    open_ids = {tid for tid, task in tasks.items() if task.is_open}
    successors: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    indegree: dict[uuid.UUID, int] = {tid: 0 for tid in open_ids}
    for source, target in blocks:
        if source in open_ids and target in open_ids:
            successors[source].append(target)
            indegree[target] += 1
    order, queue = [], [tid for tid, deg in indegree.items() if deg == 0]
    while queue:
        node = queue.pop()
        order.append(node)
        for nxt in successors[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    best: dict[uuid.UUID, float] = {}
    previous: dict[uuid.UUID, uuid.UUID | None] = {}
    for node in order:
        hours = remaining(tasks[node])[0]
        if node not in best:
            best[node], previous[node] = hours, None
        for nxt in successors[node]:
            candidate = best[node] + remaining(tasks[nxt])[0]
            if candidate > best.get(nxt, -1.0):
                best[nxt], previous[nxt] = candidate, node
    if not best:
        return {"nodes": [], "hours": 0.0, "unknown": 0}
    end = max(best, key=lambda tid: (best[tid], str(tid)))
    chain: list[uuid.UUID] = []
    cursor: uuid.UUID | None = end
    while cursor is not None:
        chain.append(cursor)
        cursor = previous[cursor]
    chain.reverse()
    if len(chain) < 2:
        return {"nodes": [], "hours": 0.0, "unknown": 0}
    return {
        "nodes": [str(tid) for tid in chain],
        "hours": round(best[end], 1),
        "unknown": sum(1 for tid in chain if remaining(tasks[tid])[1]),
    }


def _due_state(task: Task, today: date) -> str:
    if not task.due_on or not task.is_open:
        return ""
    if task.due_on < today:
        return "late"
    return "soon" if (task.due_on - today).days <= 3 else ""


def _node(
    task: Task, types: dict, statuses: dict, today: date, critical: set[str], at: tuple[float, float]
) -> dict[str, Any]:
    info = types.get(task.type, {"label": task.type, "icon": "fa-circle"})
    status = statuses.get(task.status, {"label": task.status, "kind": "open"})
    project = task.project
    return {
        "id": str(task.id),
        # Pinned: the plan's columns are computed here, Pivotick only draws them.
        "x": at[0],
        "y": at[1],
        "fx": at[0],
        "fy": at[1],
        "data": {
            "label": task.title,
            "url": f"/tasks/{task.id}",
            "type": task.type,
            "typeLabel": info["label"],
            "typeIcon": info["icon"],
            "status": task.status,
            "statusLabel": status["label"],
            "statusKind": status["kind"],
            "next": [
                {"key": key, "label": statuses[key]["label"], "kind": statuses[key]["kind"]}
                for key in workflow.allowed_next(task.status)
                if key in statuses
            ],
            "priority": task.priority,
            "due": task.due_on.isoformat() if task.due_on else None,
            "dueText": relative_day(task.due_on, today) if task.due_on else "",
            "dueState": _due_state(task, today),
            "hardDeadline": task.hard_deadline,
            "project": project.name if project else "",
            "projectId": str(project.id) if project else "",
            "projectColor": project.color if project else "slate",
            "projectIcon": project.icon if project else "fa-inbox",
            "score": round(task.score),
            "open": task.is_open,
            "blocked": task.is_open and task.blocked_by_count > 0,
            "unblocks": task.unblocks_count,
            "estimate": task.estimate_hours,
            "tags": task.tags[:4],
            "critical": str(task.id) in critical,
        },
    }


def _scope(project_id: uuid.UUID | None) -> dict[uuid.UUID, Task]:
    query = select(Task).where(Task.deleted_at.is_(None))
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    return {task.id: task for task in db.session.scalars(query)}


def _breadcrumb(project, root: Task | None) -> list[dict[str, str]]:
    trail = [{"label": "All projects", "url": "/graph"}]
    if project is not None:
        trail.append({"label": project.name, "url": f"/graph?project={project.id}"})
    if root is not None:
        chain, node, seen = [], root, set()
        while node is not None and node.id not in seen:
            seen.add(node.id)
            chain.append(node)
            node = db.session.get(Task, node.parent_id) if node.parent_id else None
        trail += [{"label": t.title, "url": f"/graph?root={t.id}"} for t in reversed(chain)]
    return trail


def graph_data(
    project_id: uuid.UUID | None = None,
    *,
    root_id: uuid.UUID | None = None,
    include_closed: bool = False,
    level: str = "top",
) -> dict[str, Any]:
    """The plan at one level, as Pivotick data.

    - no root, `level="top"`: the top-level tasks (the cases of each project);
    - no root, `level="all"`: every task, subtasks linked to their parent;
    - a root with subtasks: its direct subtasks;
    - a root without: the task and the tasks it is linked to (its neighbourhood).

    Dependencies between deeper tasks are lifted to the cards shown, so a link between two
    subtasks of different cases appears between those cases.
    """
    root = db.session.get(Task, root_id) if root_id else None
    if root is not None and root.is_deleted:
        root = None
    project = root.project if root is not None else None
    if project is None and project_id is not None:
        from app.core.db_class.planning import Project

        project = db.session.get(Project, project_id)
    tasks = _scope(None if root is not None else project_id)
    if root is not None and root.id not in tasks:
        tasks[root.id] = root
    deps = (
        list(
            db.session.scalars(
                select(Dependency).where(
                    Dependency.from_task_id.in_(list(tasks)), Dependency.to_task_id.in_(list(tasks))
                )
            )
        )
        if tasks
        else []
    )
    children: dict[uuid.UUID, list[Task]] = defaultdict(list)
    for task in tasks.values():
        if task.parent_id in tasks:
            children[task.parent_id].append(task)

    def visible(task: Task) -> bool:
        return include_closed or task.is_open

    if root is not None and children[root.id]:
        mode, shown_ids = "children", [t.id for t in children[root.id] if visible(t)]
    elif root is not None:
        mode = "around"
        linked = {d.from_task_id for d in deps if d.to_task_id == root.id}
        linked |= {d.to_task_id for d in deps if d.from_task_id == root.id}
        shown_ids = [root.id, *[t for t in linked if visible(tasks[t])]]
    elif level == "all":
        mode, shown_ids = "all", [t.id for t in tasks.values() if visible(t)]
    else:
        mode = "top"
        shown_ids = [
            t.id for t in tasks.values() if visible(t) and (t.parent_id is None or t.parent_id not in tasks)
        ]
    shown = {tid: tasks[tid] for tid in shown_ids}

    def rep(task_id: uuid.UUID) -> uuid.UUID | None:
        """The card standing for a task at this level: itself, or its nearest shown ancestor."""
        seen = set()
        node = tasks.get(task_id)
        while node is not None and node.id not in seen:
            if node.id in shown:
                return node.id
            if mode in ("around",):
                return None
            seen.add(node.id)
            node = tasks.get(node.parent_id) if node.parent_id else None
        return None

    lifted: dict[tuple[uuid.UUID, uuid.UUID, str], list[Dependency]] = defaultdict(list)
    for dep in deps:
        a, b = rep(dep.from_task_id), rep(dep.to_task_id)
        if a is not None and b is not None and a != b:
            lifted[(a, b, dep.kind)].append(dep)

    def remaining(task: Task) -> tuple[float, bool]:
        hours, unknown = _remaining(task)
        if mode == "all" or not children[task.id]:
            return hours, unknown
        if task.estimate_hours is None:  # a case without its own estimate is the sum of its parts
            hours, unknown = 0.0, False
        stack = list(children[task.id])
        while stack:  # a case weighs the work left in all its open subtasks
            child = stack.pop()
            if child.is_open:
                more, missing = _remaining(child)
                hours, unknown = hours + more, unknown or missing
            stack.extend(children[child.id])
        return hours, unknown

    path = critical_path(shown, [(a, b) for (a, b, kind) in lifted if kind == "blocks"], remaining)
    on_path = set(path["nodes"])
    path_edges = set(zip(path["nodes"], path["nodes"][1:], strict=False))
    parents = {t.id: t.parent_id for t in shown.values() if mode == "all" and t.parent_id in shown}
    places = plan_layout(shown, [(a, b) for (a, b, kind) in lifted if kind in ORDERING], parents)

    today = date.today()
    types, statuses = workflow.types(), workflow.status_map()
    nodes = []
    for task in shown.values():
        node = _node(task, types, statuses, today, on_path, places[task.id])
        kids = children[task.id]
        node["data"]["children"] = len(kids)
        node["data"]["childrenDone"] = sum(1 for k in kids if not k.is_open)
        node["data"]["drill"] = f"/graph?root={task.id}" if kids and mode != "all" else ""
        node["data"]["isRoot"] = root is not None and task.id == root.id
        nodes.append(node)
    edges = [
        {
            "id": f"dep-{a}-{b}-{kind}",
            "from": str(a),
            "to": str(b),
            "data": {
                "kind": kind,
                "note": group[0].note if len(group) == 1 else f"{len(group)} links between their subtasks",
                "count": len(group),
                "critical": kind == "blocks" and (str(a), str(b)) in path_edges,
            },
        }
        for (a, b, kind), group in lifted.items()
    ]
    edges += [
        {
            "id": f"sub-{child}",
            "from": str(parent),
            "to": str(child),
            "data": {"kind": "subtask", "note": "", "count": 1, "critical": False},
        }
        for child, parent in parents.items()
    ]
    steps = max((x for x, _ in places.values()), default=0) // (CARD_W + COL_GAP) + 1 if places else 0
    return {
        "mode": mode,
        "nodes": nodes,
        "edges": edges,
        "critical": path,
        "steps": int(steps),
        "breadcrumb": _breadcrumb(project, root),
    }
