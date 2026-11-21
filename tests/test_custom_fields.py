import pytest
from sqlalchemy import select

from app.core.db_class.planning import Task
from app.core.extensions import db
from app.core.schema.planning import TaskCreate, TaskUpdate
from app.core.utils.settings import SettingError, set_setting
from app.features.tasks import brief_core, tasks_core

FIELDS = {
    "target_version": {"label": "Target version", "type": "text"},
    "points": {"label": "Story points", "type": "number"},
    "freeze": {"label": "Code freeze", "type": "date"},
    "spec": {"label": "Spec", "type": "url"},
    "risk": {"label": "Risk", "type": "select", "options": ["low", "high"]},
}


def test_definitions_are_typed(ctx):
    with pytest.raises(SettingError):
        set_setting("tasks.custom_fields", {"risk": {"label": "Risk", "type": "select"}})
    with pytest.raises(SettingError):
        set_setting("tasks.custom_fields", {"Bad Key": {"label": "x", "type": "text"}})
    set_setting("tasks.custom_fields", FIELDS)


def test_values_are_checked_and_cleaned(ctx):
    set_setting("tasks.custom_fields", FIELDS)
    task = tasks_core.create(
        TaskCreate(
            title="Ship v2",
            custom={
                "target_version": " 2.0 ",
                "points": "5",
                "freeze": "2026-12-01",
                "risk": "high",
                "spec": "",
            },
        )
    )
    assert task.custom == {"target_version": "2.0", "points": 5.0, "freeze": "2026-12-01", "risk": "high"}
    assert "- Story points: 5" in brief_core.task_brief(task) and "- Risk: high" in brief_core.task_brief(
        task
    )
    for bad, message in (
        ({"points": "five"}, "must be a number"),
        ({"freeze": "next week"}, "must be a date"),
        ({"spec": "javascript:alert(1)"}, "web address"),
        ({"risk": "medium"}, "one of: low, high"),
        ({"nope": "x"}, "no custom field 'nope'"),
    ):
        with pytest.raises(tasks_core.TaskError, match=message):
            tasks_core.update(task.id, TaskUpdate(custom=bad))
    tasks_core.update(task.id, TaskUpdate(custom={"points": 8}))
    assert task.custom == {"points": 8.0}


def test_form_and_page(app, signed_in):
    with app.app_context():
        set_setting("tasks.custom_fields", FIELDS)
    data = {"title": "Freeze", "type": "feature", "priority": "medium", "custom__risk": "low",
            "custom__spec": "https://example.org/spec", "custom__points": "3"}  # fmt: skip
    assert signed_in.post("/tasks/new", data=data).status_code == 302
    with app.app_context():
        task = db.session.scalar(select(Task).where(Task.title == "Freeze"))
        assert task.custom == {"risk": "low", "spec": "https://example.org/spec", "points": 3.0}
        task_id = task.id
    page = signed_in.get(f"/tasks/{task_id}")
    assert b"Story points" in page.data and b"example.org" in page.data
    form = signed_in.get(f"/tasks/{task_id}/edit")
    assert b'name="custom__points"' in form.data and b'value="3"' in form.data
    bad = signed_in.post(f"/tasks/{task_id}/edit", data={**data, "custom__risk": "huge"})
    assert bad.status_code == 422 and b"Risk must be one of" in bad.data
    assert signed_in.get(f"/api/tasks/{task_id}").json["custom"]["risk"] == "low"


def test_without_definitions_the_form_points_to_settings(app, signed_in):
    assert b"Custom task fields" in signed_in.get("/tasks/new").data
