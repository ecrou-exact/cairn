from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.db_class.planning import Dependency, Project, Task
from app.core.extensions import db
from app.core.schema.planning import DependencyCreate, ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate
from app.core.utils import history
from app.core.utils.actor import acting_as
from app.features.projects import projects_core
from app.features.tasks import dependencies_core, quickadd_core, tasks_core, timer_core
from app.features.tasks.dependencies_core import DependencyError
from app.features.tasks.tasks_core import TaskError


def _task(title="Task", **kw):
    return tasks_core.create(TaskCreate(title=title, **kw))


def _blocks(a, b):
    return dependencies_core.add(DependencyCreate(from_task_id=a.id, to_task_id=b.id))


def _last_batch():
    return db.session.scalar(
        select(Activity.batch_id)
        .where(Activity.batch_id.is_not(None))
        .order_by(Activity.created_at.desc())
        .limit(1)
    )


# -- projects --------------------------------------------------------------------------------


def test_project_slug_is_unique_and_derived(ctx):
    first = projects_core.create(ProjectCreate(name="Rulezet Core"))
    second = projects_core.create(ProjectCreate(name="Rulezet  core!"))
    assert (first.slug, second.slug) == ("rulezet-core", "rulezet-core-2")
    with pytest.raises(projects_core.ProjectError):
        projects_core.update(second.id, ProjectUpdate(slug="rulezet-core"))


def test_project_delete_takes_its_tasks_and_undo_brings_them_back(ctx):
    project = projects_core.create(ProjectCreate(name="Cairn"))
    parent = _task("Parent", project_id=project.id)
    _task("Child", parent_id=parent.id)
    assert projects_core.delete(project.id) == 2
    assert all(t.is_deleted for t in db.session.scalars(select(Task)))
    history.undo(_last_batch())
    assert not project.is_deleted and not any(t.is_deleted for t in db.session.scalars(select(Task)))


# -- tasks -----------------------------------------------------------------------------------


def test_create_defaults_and_history(ctx):
    with acting_as("claude:run-1"):
        task = _task("  Fix   login  ", tags=["#Bug", "bug", "auth"])
    assert (task.title, task.status, task.tags, task.created_by) == (
        "Fix login",
        "todo",
        ["bug", "auth"],
        "claude:run-1",
    )
    entry = db.session.scalars(select(Activity).where(Activity.action == "task.create")).one()
    assert entry.actor == "claude:run-1" and entry.diff["title"] == [None, "Fix login"]


def test_unknown_type_and_status_are_refused(ctx):
    with pytest.raises(TaskError):
        _task(type="nope")
    with pytest.raises(TaskError):
        _task(status="nope")


def test_workflow_transitions(ctx):
    task = _task()
    with pytest.raises(TaskError, match="cannot go from To do to In review"):
        tasks_core.set_status(task.id, "in_review")
    tasks_core.set_status(task.id, "in_progress")
    tasks_core.set_status(task.id, "done")
    assert task.completed_at is not None and not task.is_open and task.score == 0
    tasks_core.set_status(task.id, "todo")
    assert task.completed_at is None and task.is_open


def test_subtasks_follow_project_and_refuse_cycles(ctx):
    project = projects_core.create(ProjectCreate(name="P"))
    parent = _task("Parent", project_id=project.id)
    child = _task("Child", parent_id=parent.id)
    grandchild = _task("Grandchild", parent_id=child.id)
    assert child.project_id == project.id
    with pytest.raises(TaskError, match="under itself"):
        tasks_core.update(parent.id, TaskUpdate(parent_id=grandchild.id))
    assert [t.title for t in tasks_core.ancestors(grandchild)] == ["Parent", "Child"]


def test_delete_restore_purge(ctx):
    parent = _task("Parent")
    child = _task("Child", parent_id=parent.id)
    other = _task("Other")
    _blocks(child, other)
    assert tasks_core.delete(parent.id) == 2
    with pytest.raises(TaskError, match="parent"):
        tasks_core.restore(child.id)
    assert tasks_core.restore(parent.id) == 2
    tasks_core.delete(parent.id)
    tasks_core.purge(parent.id)
    assert db.session.get(Task, child.id) is None and db.session.scalar(select(Dependency)) is None
    assert other.blocked_by_count == 0


def test_undo_update_restores_every_field(ctx):
    task = _task("Before", due_on=date(2026, 12, 1), tags=["a"])
    tasks_core.update(task.id, TaskUpdate(title="After", due_on=None, tags=["b"], status="in_progress"))
    batch_id = _last_batch()
    assert history.is_undoable(batch_id)
    history.undo(batch_id)
    assert (task.title, task.due_on, task.tags, task.status) == ("Before", date(2026, 12, 1), ["a"], "todo")
    with pytest.raises(history.UndoError):
        history.undo(batch_id)


# -- dependencies ----------------------------------------------------------------------------


def test_blocked_state_unblocks_count_and_score(ctx):
    a, b, c = _task("A"), _task("B"), _task("C")
    _blocks(a, b)
    _blocks(b, c)
    assert (a.unblocks_count, b.blocked_by_count, c.blocked_by_count) == (2, 1, 1)
    assert a.score > b.score  # unblocking two tasks counts
    tasks_core.set_status(a.id, "in_progress")
    tasks_core.set_status(a.id, "done")
    assert b.blocked_by_count == 0 and c.blocked_by_count == 1
    assert [t.title for _, t in dependencies_core.blocking_chain(c.id)] == ["B"]


def test_cycles_are_refused_with_the_loop(ctx):
    a, b, c = _task("A"), _task("B"), _task("C")
    _blocks(a, b)
    dependencies_core.add(DependencyCreate(from_task_id=b.id, to_task_id=c.id, kind="follows"))
    with pytest.raises(DependencyError, match="“C” → “A” → “B” → “C”"):
        _blocks(c, a)
    dependencies_core.add(
        DependencyCreate(from_task_id=c.id, to_task_id=a.id, kind="relates")
    )  # not ordering
    with pytest.raises(DependencyError, match="itself"):
        _blocks(a, a)
    with pytest.raises(DependencyError, match="already"):
        _blocks(a, b)


def test_dependency_removal_is_undoable(ctx):
    a, b = _task("A"), _task("B")
    dependency = _blocks(a, b)
    dependencies_core.remove(dependency.id)
    assert b.blocked_by_count == 0
    history.undo(_last_batch())
    assert b.blocked_by_count == 1


def test_next_actions_and_attention(ctx):
    today = date.today()
    blocker = _task("Blocker", priority="low")
    blocked = _task("Blocked", priority="critical")
    _blocks(blocker, blocked)
    _task("Later", do_on=today + timedelta(days=3))
    urgent = _task("Urgent", priority="critical", due_on=today - timedelta(days=2))
    soon = _task("Soon", due_on=today + timedelta(days=1), hard_deadline=True)
    waiting = _task("Waiting on nothing", status="blocked")
    titles = [t.title for t in tasks_core.next_actions()]
    assert titles[0] == "Urgent" and "Blocked" not in titles and "Later" not in titles
    assert "Waiting on nothing" not in titles
    radar = {task.title: key for key, _, task in tasks_core.needs_attention()}
    assert radar[urgent.title] == "overdue" and radar[soon.title] == "due_soon"
    assert radar[waiting.title] == "unblocked"


# -- quick add -------------------------------------------------------------------------------


def test_quick_add_parses_the_brief_example(ctx):
    projects_core.create(ProjectCreate(name="Rulezet"))
    today = date(2026, 11, 18)  # a Wednesday
    parsed = quickadd_core.parse(
        "fix login bug for rulezet by friday #bug !high ~2h @claude #auth !hard", today
    )
    assert parsed.title == "fix login bug"
    assert parsed.project.slug == "rulezet" and parsed.due_on == date(2026, 11, 20) and parsed.hard_deadline
    assert (parsed.type, parsed.tags, parsed.priority, parsed.estimate_hours, parsed.assignee) == (
        "bug",
        ["auth"],
        "high",
        2.0,
        "claude",
    )


@pytest.mark.parametrize(
    ("text", "due", "do"),
    [
        ("a by tomorrow", date(2026, 11, 19), None),
        ("a due in 3 days", date(2026, 11, 21), None),
        ("a by next week", date(2026, 11, 23), None),
        ("a by end of month", date(2026, 11, 30), None),
        ("a by 2026-12-24", date(2026, 12, 24), None),
        ("a by 3/1", date(2027, 1, 3), None),
        ("a on vendredi", None, date(2026, 11, 20)),
        ("a today", None, date(2026, 11, 18)),
        ("work on login", None, None),
    ],
)
def test_quick_add_dates(ctx, text, due, do):
    parsed = quickadd_core.parse(text, date(2026, 11, 18))
    assert (parsed.due_on, parsed.do_on) == (due, do)


def test_quick_add_keeps_unknown_words_in_the_title(ctx):
    parsed = quickadd_core.parse("ask for help on monday-ish #9999-not-a-type")
    assert parsed.title == "ask for help on monday-ish" and parsed.project is None
    assert parsed.tags == ["9999-not-a-type"]
    with pytest.raises(TaskError):
        quickadd_core.quick_add("#bug !high")


def test_similar_tasks(ctx):
    _task("Fix the login bug on mobile")
    assert quickadd_core.similar_tasks("fix the login bug on mobile!")
    assert not quickadd_core.similar_tasks("Write release notes")


# -- time tracking ---------------------------------------------------------------------------


def test_timer_starts_work_and_adds_time(ctx):
    first, second = _task("First"), _task("Second")
    timer_core.start(first.id)
    assert first.status == "in_progress" and timer_core.running()[1].id == first.id
    timer_core.start(second.id)  # switching stops the first timer
    assert timer_core.running()[1].id == second.id and len(timer_core.entries(first.id)) == 1
    tasks_core.set_status(second.id, "done")  # closing a task stops its timer
    assert timer_core.running() is None
    assert timer_core.format_duration(3720) == "1 h 02" and timer_core.format_duration(59) == "0 min"


def test_project_weight_multiplies_score(ctx):
    heavy = projects_core.create(ProjectCreate(name="Heavy", weight=2))
    light = projects_core.create(ProjectCreate(name="Light"))
    a, b = _task("A", project_id=heavy.id), _task("B", project_id=light.id)
    assert a.score == pytest.approx(b.score * 2, abs=0.2)
    assert any(item["factor"] == "project" for item in a.score_explain)
    assert db.session.scalar(select(Project).where(Project.slug == "heavy")).weight == 2


def test_failed_undo_changes_nothing(ctx):
    a = _task("A")
    tasks_core.update(a.id, TaskUpdate(title="B"))
    tasks_core.update(a.id, TaskUpdate(title="C"))
    first = db.session.scalars(
        select(Activity.batch_id).where(Activity.action == "task.update").order_by(Activity.created_at)
    ).first()
    project = projects_core.create(ProjectCreate(name="P"))
    tasks_core.update(a.id, TaskUpdate(project_id=project.id))
    projects_core.delete(project.id)  # the task is in the trash now: undoing its rename must fail
    with pytest.raises(TaskError):
        history.undo(first)
    assert a.title == "C" and a.is_deleted  # the failed undo left everything as it was
