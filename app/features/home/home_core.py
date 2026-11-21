"""Data for the Today page: the task to do now and why, what follows, the week ahead, the
projects' pulse, what needs attention, and recent activity told in plain words."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.db_class.planning import Project, Task
from app.core.db_class.resource import Resource
from app.core.extensions import db
from app.features.comments.comments_core import author_label
from app.features.projects import projects_core
from app.features.tasks import tasks_core, timer_core, workflow

# action → (icon, verb). The object is the target's name, looked up when shown.
ACTIONS = {
    "task.create": ("fa-plus", "added"),
    "task.update": ("fa-pen", "changed"),
    "task.delete": ("fa-trash-can", "moved to the trash"),
    "task.restore": ("fa-rotate-left", "restored"),
    "task.recur": ("fa-repeat", "scheduled the next"),
    "project.create": ("fa-folder-plus", "started the project"),
    "project.update": ("fa-pen", "changed the project"),
    "dependency.create": ("fa-link", "linked two tasks"),
    "dependency.delete": ("fa-link-slash", "removed a link"),
    "condition.create": ("fa-hourglass-half", "added a condition to wait for"),
    "condition.resolve": ("fa-check", "saw a condition happen"),
    "resource.create": ("fa-paperclip", "added the resource"),
    "resource.attach": ("fa-paperclip", "attached a resource"),
    "comment.create": ("fa-comment", "commented"),
    "connection.check": ("fa-plug", "checked an account"),
    "auth.login": ("fa-right-to-bracket", "signed in"),
}


def greeting(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    return "Good morning" if 5 <= hour < 12 else "Good afternoon" if hour < 18 else "Good evening"


def reasons(task: Task, limit: int = 3) -> list[str]:
    """The biggest parts of a task's score, in words: why it comes first."""
    parts = sorted((p for p in task.score_explain if p.get("points")), key=lambda p: -p["points"])
    return [f"{p['label']}: {p['detail']}" for p in parts[:limit]]


def week_ahead(today: date | None = None) -> dict[str, Any]:
    """The next seven days, each with the open tasks due that day; and what is already late."""
    today = today or date.today()
    end = today + timedelta(days=6)
    due = list(
        db.session.scalars(
            select(Task)
            .where(
                Task.deleted_at.is_(None),
                Task.is_open.is_(True),
                Task.due_on.is_not(None),
                Task.due_on <= end,
            )
            .order_by(Task.due_on, Task.score.desc())
        )
    )
    days = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        tasks = [t for t in due if t.due_on == day]
        days.append({"date": day, "tasks": tasks, "today": offset == 0, "weekend": day.weekday() >= 5})
    return {"days": days, "late": [t for t in due if t.due_on < today]}


def project_pulse(limit: int = 6) -> list[dict[str, Any]]:
    projects = [p for p in projects_core.options() if p.status == "active"]
    stats = projects_core.stats([p.id for p in projects])
    rows = []
    for project in projects:
        st = stats[project.id]
        total = st["open"] + st["closed"]
        rows.append(
            {
                "project": project,
                **st,
                "total": total,
                "done_pct": round(100 * st["closed"] / total) if total else 0,
            }
        )
    rows.sort(key=lambda r: (-(r["open"] > 0), -r["overdue"], -r["open"]))
    return rows[:limit]


def _names(rows: list[Activity]) -> dict[tuple[str, str], tuple[str, str]]:
    """(target type, id) → (name, url) for the activity rows' targets that still exist."""
    wanted: dict[str, set[uuid.UUID]] = {"task": set(), "project": set(), "resource": set()}
    for row in rows:
        if row.target_type in wanted and row.target_id:
            try:
                wanted[row.target_type].add(uuid.UUID(row.target_id))
            except ValueError:
                continue
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for task in db.session.scalars(select(Task).where(Task.id.in_(wanted["task"]))) if wanted["task"] else []:
        found[("task", str(task.id))] = (task.title, f"/tasks/{task.id}")
    for project in (
        db.session.scalars(select(Project).where(Project.id.in_(wanted["project"])))
        if wanted["project"]
        else []
    ):
        found[("project", str(project.id))] = (project.name, f"/projects/{project.slug}")
    for res in (
        db.session.scalars(select(Resource).where(Resource.id.in_(wanted["resource"])))
        if wanted["resource"]
        else []
    ):
        found[("resource", str(res.id))] = (res.title, f"/resources/{res.id}")
    return found


def recent_activity(limit: int = 12) -> list[dict[str, Any]]:
    """Recent changes told as sentences ("You moved X to Done"); noise (jobs, secrets) left out."""
    rows = list(
        db.session.scalars(
            select(Activity)
            .where(Activity.action.in_(list(ACTIONS)))
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
    )
    names = _names(rows)
    told = []
    for row in rows:
        icon, verb = ACTIONS[row.action]
        name, url = names.get((row.target_type or "", row.target_id or ""), ("", ""))
        after = ""
        if row.action == "task.update" and row.diff and "status" in row.diff:
            verb, after = "moved", f"to {workflow.label_of(row.diff['status'][1])}"
            icon = "fa-arrow-right"
        elif row.action == "task.recur":
            verb, name = "scheduled the next", name and f"“{name}”"
        told.append(
            {
                "when": row.created_at,
                "icon": icon,
                "who": author_label(row.actor),
                "verb": verb,
                "name": name,
                "url": url,
                "after": after,
                "level": row.level,
            }
        )
    return told


def today() -> dict[str, Any]:
    actions = tasks_core.next_actions(limit=8)
    focus = actions[0] if actions else None
    return {
        "focus": focus,
        "focus_reasons": reasons(focus) if focus else [],
        "next_actions": actions[1:],
        "attention": tasks_core.needs_attention(),
        "timer": timer_core.running(),
        "counts": tasks_core.counts_by_state(),
        "pulse": tasks_core.pulse(),
        "greeting": greeting(),
        "week": week_ahead(),
        "projects": project_pulse(),
        "activity": recent_activity(),
    }
