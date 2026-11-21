from datetime import date, timedelta

from sqlalchemy import func, select

from app.core.db_class.planning import Task
from app.core.extensions import db
from app.core.schema.planning import Recurrence, TaskCreate, TaskUpdate
from app.core.utils import history
from app.core.utils.history import batch
from app.features.tasks import quickadd_core, recurrence_core, tasks_core

WEEKLY = {"every": 1, "unit": "week", "anchor": "due"}


def test_shift_and_describe():
    assert recurrence_core.shift(date(2026, 1, 31), 1, "month") == date(2026, 2, 28)
    assert recurrence_core.shift(date(2024, 2, 29), 1, "year") == date(2025, 2, 28)
    assert recurrence_core.shift(date(2026, 11, 30), 3, "month") == date(2027, 2, 28)
    assert recurrence_core.describe({"every": 2, "unit": "week", "anchor": "done"}) == (
        "Every 2 weeks, after it is done"
    )


def test_next_dates_keep_rhythm_and_spacing():
    today = date(2026, 11, 21)
    on_time = recurrence_core.next_dates(
        WEEKLY, start_on=date(2026, 11, 20), do_on=None, due_on=date(2026, 11, 23), today=today
    )
    assert on_time == {"start_on": date(2026, 11, 27), "do_on": None, "due_on": date(2026, 11, 30)}
    late = recurrence_core.next_dates(
        WEEKLY, start_on=None, do_on=None, due_on=date(2026, 11, 2), today=today
    )
    assert late["due_on"] == date(2026, 11, 23)  # still a Monday, the next one after today
    after_done = recurrence_core.next_dates(
        {"every": 3, "unit": "day", "anchor": "done"},
        start_on=None,
        do_on=None,
        due_on=date(2026, 11, 1),
        today=today,
    )
    assert after_done["due_on"] == date(2026, 11, 24)
    undated = recurrence_core.next_dates(WEEKLY, start_on=None, do_on=None, due_on=None, today=today)
    assert undated["due_on"] == date(2026, 11, 28)


def test_done_creates_the_next_occurrence_once_and_undo_removes_it(ctx):
    due = date.today() + timedelta(days=2)
    task = tasks_core.create(
        TaskCreate(
            title="Weekly release check",
            due_on=due,
            estimate_hours=1,
            tags=["release"],
            checklist=[{"text": "read the changelog", "done": True}],
            recurrence=Recurrence(unit="week"),
        )
    )
    with batch() as done_batch:
        tasks_core.set_status(task.id, "done")
    following = db.session.get(Task, task.next_occurrence_id)
    assert following.title == task.title and following.due_on == due + timedelta(weeks=1)
    assert following.checklist == [{"text": "read the changelog", "done": False}]
    assert following.recurrence == {"every": 1, "unit": "week", "anchor": "due"} and following.is_open

    tasks_core.set_status(task.id, "todo")
    tasks_core.set_status(task.id, "done")  # reopened and done again: no second copy
    assert db.session.scalar(select(func.count()).select_from(Task).where(Task.deleted_at.is_(None))) == 2

    history.undo(done_batch)  # the first "done": its occurrence goes too
    assert db.session.get(Task, following.id).is_deleted


def test_cancelled_does_not_repeat_and_null_stops_it(ctx):
    task = tasks_core.create(TaskCreate(title="Water the plants", recurrence=Recurrence(unit="day", every=3)))
    tasks_core.update(task.id, TaskUpdate(recurrence=None))
    assert task.recurrence is None
    tasks_core.update(task.id, TaskUpdate.model_validate({"recurrence": {"unit": "month"}}))
    assert task.recurrence == {"every": 1, "unit": "month", "anchor": "due"}
    tasks_core.set_status(task.id, "cancelled")
    assert task.next_occurrence_id is None


def test_quick_add_understands_repeats(ctx):
    for text, rule in (
        ("check backups weekly", {"every": 1, "unit": "week", "anchor": "due"}),
        ("release check every 2 weeks #release", {"every": 2, "unit": "week", "anchor": "due"}),
        ("arroser les plantes tous les jours", {"every": 1, "unit": "day", "anchor": "due"}),
        ("facture chaque mois", {"every": 1, "unit": "month", "anchor": "due"}),
    ):
        parsed = quickadd_core.parse(text)
        assert parsed.recurrence == rule, text
        assert "every" not in parsed.title.split() and "weekly" not in parsed.title.split()
    assert quickadd_core.parse("read every page").recurrence is None
    task = quickadd_core.quick_add("pay rent monthly by friday")
    assert task.recurrence["unit"] == "month" and task.title == "pay rent"


def test_form_and_page(app, signed_in):
    response = signed_in.post(
        "/tasks/new",
        data={"title": "Standup notes", "type": "feature", "priority": "medium", "repeat_unit": "day",
              "repeat_every": "1", "repeat_anchor": "done", "due_on": date.today().isoformat()},
    )  # fmt: skip
    assert response.status_code == 302
    with app.app_context():
        task = db.session.scalar(select(Task).where(Task.title == "Standup notes"))
        assert task.recurrence == {"every": 1, "unit": "day", "anchor": "done"}
        task_id = task.id
    page = signed_in.get(f"/tasks/{task_id}")
    assert b"Every day, after it is done" in page.data
    assert signed_in.get(f"/tasks/{task_id}/edit").status_code == 200
    signed_in.post(f"/tasks/{task_id}/status", data={"status": "done"})
    assert b"Next one created for" in signed_in.get(f"/tasks/{task_id}").data
