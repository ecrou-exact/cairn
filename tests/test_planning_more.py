import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.db_class.planning import Dependency, Project, Task
from app.core.extensions import db
from app.core.schema.planning import BulkEdit, DependencyCreate, ProjectCreate, TaskCreate
from app.core.utils import history
from app.core.utils.settings import set_setting
from app.features.projects import projects_core
from app.features.projects.plan_import_core import PlanError, import_plan
from app.features.tasks import dependencies_core, risk_core, tasks_core, templates_core

ROADMAP = Path(__file__).resolve().parent.parent / "docs" / "roadmap.json"


def _task(title, **kw):
    return tasks_core.create(TaskCreate(title=title, **kw))


def test_bulk_edit_is_one_undoable_batch(ctx):
    a, b, c = _task("A", tags=["x"]), _task("B"), _task("C", status="backlog")
    with history.batch() as batch_id:
        changed, skipped = tasks_core.bulk_edit(
            BulkEdit(task_ids=[a.id, b.id, c.id], status="in_review", add_tags=["sprint"])
        )
    # backlog → in_review and todo → in_review are not allowed: only tags change there
    assert changed == 0 and len(skipped) == 3
    with history.batch() as batch_id:
        changed, skipped = tasks_core.bulk_edit(
            BulkEdit(task_ids=[a.id, b.id, c.id], priority="high", add_tags=["sprint"])
        )
    assert (changed, skipped) == (3, [])
    assert a.tags == ["x", "sprint"] and c.priority == "high"
    history.undo(batch_id)
    assert a.tags == ["x"] and c.priority == "medium" and b.priority == "medium"


def test_bulk_delete_takes_subtasks_once(ctx):
    parent = _task("Parent")
    child = _task("Child", parent_id=parent.id)
    changed, skipped = tasks_core.bulk_edit(BulkEdit(task_ids=[parent.id, child.id], delete=True))
    assert (changed, skipped) == (2, []) and child.is_deleted


def test_deadline_risk_counts_the_chain(ctx):
    set_setting("tasks.capacity", {"hours_per_day": 4, "work_days": [0, 1, 2, 3, 4, 5, 6]})
    today = date(2026, 11, 23)
    design = _task("Design", estimate_hours=6)
    build = _task("Build", estimate_hours=5, due_on=today + timedelta(days=1))  # 8 h left: 2 days × 4 h
    dependencies_core.add(DependencyCreate(from_task_id=design.id, to_task_id=build.id))
    _task("Unestimated blocker")
    risk = risk_core.risk_of(build.id, today)
    assert (risk.needed_hours, risk.available_hours, risk.chain_size, risk.short_by) == (11, 8, 2, 3)
    assert risk_core.risk_of(design.id, today) is None  # no due date
    tasks_core.update(design.id, tasks_core.TaskUpdate(estimate_hours=1))
    assert risk_core.risk_of(build.id, today) is None
    assert risk_core.available_hours(date(2026, 11, 29), date(2026, 11, 23)) == 28


def test_weekends_are_not_working_time(ctx):
    monday = date(2026, 11, 23)
    assert risk_core.available_hours(monday + timedelta(days=6), monday) == 5 * 6


def test_template_makes_a_chained_task(ctx):
    project = projects_core.create(ProjectCreate(name="Cairn"))
    task = templates_core.instantiate("release", "Release 0.2", project_id=project.id)
    subtasks = tasks_core.subtasks(task.id)
    assert task.type == "release" and len(task.checklist) == 4 and len(subtasks) == 4
    assert all(sub.project_id == project.id for sub in subtasks)
    assert (
        db.session.scalar(select(func.count()).select_from(Dependency).where(Dependency.kind == "follows"))
        == 3
    )
    with pytest.raises(tasks_core.TaskError):
        templates_core.instantiate("nope", "x")


def test_cairn_roadmap_imports_and_reimports(ctx):
    plan = json.loads(ROADMAP.read_text(encoding="utf-8"))
    first = import_plan(plan)
    assert first["created"] == len(plan["tasks"]) and first["dependencies"] > 10
    again = import_plan(plan)
    assert again == {"created": 0, "existing": len(plan["tasks"]), "dependencies": 0}
    project = db.session.scalar(select(Project).where(Project.slug == "cairn"))
    graph = db.session.scalar(select(Task).where(Task.title == "Phase 4 — Graph (Pivotick)"))
    assert graph.project_id == project.id and graph.blocked_by_count == 1
    assert tasks_core.next_actions(limit=50)  # something is actionable right away


def test_plan_errors(ctx):
    with pytest.raises(PlanError, match="unknown key"):
        import_plan({"project": {"name": "P"}, "tasks": [{"key": "a", "title": "A", "blocked_by": ["zz"]}]})
    with pytest.raises(PlanError, match="before its parent"):
        import_plan(
            {
                "project": {"name": "P"},
                "tasks": [{"key": "a", "title": "A", "parent": "b"}, {"key": "b", "title": "B"}],
            }
        )
    with pytest.raises(PlanError, match="cycle"):
        import_plan(
            {
                "project": {"name": "Q"},
                "tasks": [
                    {"key": "a", "title": "A", "blocked_by": ["b"]},
                    {"key": "b", "title": "B", "blocked_by": ["a"]},
                ],
            }
        )
    assert db.session.scalar(select(Project).where(Project.slug == "q")) is None  # all or nothing


def test_bulk_and_template_pages(app, signed_in):
    with app.app_context():
        ids = [str(_task(f"T{i}").id) for i in range(3)]
    response = signed_in.post(
        "/tasks/bulk", data={"action": "priority", "priority": "critical", "task_ids": ids}
    )
    assert response.status_code == 302
    page = signed_in.get("/tasks").data
    assert b"3 tasks changed" in page and b'id="bulk-form"' in page and b"data-autosubmit" in page
    none = signed_in.post(
        "/tasks/bulk", data={"action": "priority", "priority": "low"}, follow_redirects=True
    )
    assert b"Select at least one task" in none.data
    assert signed_in.post("/tasks/bulk", data={"action": "drop", "task_ids": ids}).status_code == 400
    signed_in.post(f"/tasks/{ids[0]}/priority", data={"priority": "low"})
    created = signed_in.post("/tasks/from-template", data={"template": "feature", "title": "Saved views"})
    assert created.status_code == 302
    detail = signed_in.get(created.location).data
    assert b"Write the spec" in detail and b"Saved views" in detail
