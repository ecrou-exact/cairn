"""Changesets (D-071): proposed, tried, approved one by one, applied and undone at once."""

import uuid

import pytest

from app.core.db_class.changeset import Changeset
from app.core.db_class.job import Event
from app.core.db_class.planning import Task
from app.core.extensions import db
from app.core.schema.changesets import ChangesetCreate
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.utils.actor import acting_as
from app.core.utils.history import batch, undo
from app.features.changesets import changesets_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core


@pytest.fixture
def plan(ctx):
    project = projects_core.create(ProjectCreate(name="Pandora"))
    task = tasks_core.create(
        TaskCreate(title="Read it", project_id=project.id, checklist=[{"text": "One", "done": True}])
    )
    return project, task


def _items(task):
    return [
        {
            "op": "create_task",
            "key": "conn",
            "title": "Connector",
            "estimate_hours": 3,
            "reason": "Asked for",
        },
        {"op": "create_task", "key": "sub", "title": "Its tests", "parent": "conn"},
        {"op": "link_tasks", "first": str(task.id), "then": "conn"},
        {"op": "update_task", "task": str(task.id), "priority": "high", "checklist": ["One", "Two"]},
        {"op": "set_status", "task": str(task.id), "status": "in_progress"},
        {"op": "comment", "task": "conn", "text": "From the talk"},
    ]


def _propose(project, items, **more):
    data = ChangesetCreate.model_validate({"title": "Plan the connector", "items": items, **more})
    with acting_as("claude:test"):
        return changesets_core.propose(data, project.id)


def _count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def test_a_proposal_writes_nothing(plan):
    project, task = plan
    tasks = _count(Task)
    changeset = _propose(project, _items(task))
    assert _count(Task) == tasks and db.session.get(Task, task.id).priority == "medium"
    kinds = [e.type for e in db.session.scalars(db.select(Event))]
    assert kinds.count("changeset.changed") == 1
    told = changesets_core.describe(changeset)
    assert [row["needs"] for row in told["items"]] == [[], [0], [0], [], [], [0]]
    status = told["items"][4]["fields"][0]
    assert (status["before"], status["after"]) == ("To do", "In progress")
    assert told["items"][3]["task"]["title"] == "Read it" and told["items"][2]["then"]["new"]


def test_what_is_kept_is_applied_and_undone_at_once(plan):
    project, task = plan
    changeset = _propose(project, _items(task))
    with batch() as batch_id:
        changesets_core.apply(changeset.id, [0, 1, 2, 3, 4, 5])
    made = db.session.scalar(db.select(Task).where(Task.title == "Connector"))
    sub = db.session.scalar(db.select(Task).where(Task.title == "Its tests"))
    assert (made.project_id, made.created_by, made.blocked_by_count) == (project.id, "claude:test", 1)
    assert sub.parent_id == made.id and sub.project_id == project.id
    assert [(i["text"], i["done"]) for i in task.checklist] == [("One", True), ("Two", False)]
    assert (task.status, changeset.status) == ("in_progress", "applied")
    with pytest.raises(changesets_core.ChangesetError, match="already answered"):
        changesets_core.apply(changeset.id, [0])
    undo(batch_id)
    db.session.expire_all()
    assert db.session.get(Task, made.id).is_deleted and task.status == "todo"
    assert db.session.get(Changeset, changeset.id).status == "proposed"


def test_refusing_one_refuses_what_needs_it(plan):
    project, task = plan
    changeset = _propose(project, _items(task))
    changesets_core.apply(changeset.id, [1, 2, 3, 5])  # the connector itself is refused
    assert [item["kept"] for item in changeset.items] == [False, False, False, True, False, False]
    assert task.priority == "high" and task.status == "todo"
    again = _propose(project, [_items(task)[0], _items(task)[1]])
    with pytest.raises(changesets_core.ChangesetError, match="needs a change"):
        changesets_core.apply(again.id, [1])


def test_what_cannot_work_never_reaches_the_owner(plan):
    project, task = plan
    other = tasks_core.create(TaskCreate(title="Other", project_id=project.id))
    for items, says in (
        (
            [
                {"op": "link_tasks", "first": str(task.id), "then": str(other.id)},
                {"op": "link_tasks", "first": str(other.id), "then": str(task.id)},
            ],
            "item 2",
        ),
        ([{"op": "set_status", "task": str(task.id), "status": "in_review"}], "cannot go from"),
        ([{"op": "set_status", "task": str(uuid.uuid4()), "status": "done"}], "item 1"),
        ([{"op": "comment", "task": "nokey", "text": "x"}], "neither a task"),
        ([{"op": "create_task", "key": "a", "title": "A", "project": "Nowhere"}], "no project"),
        ([{"op": "create_task", "key": "a", "title": "A", "type": "nope"}], "item 1"),
    ):
        with pytest.raises(changesets_core.ChangesetError, match=says):
            _propose(project, items)
    assert _count(Changeset) == 0 and task.status == "todo"
    for bad in (
        [],
        [{"op": "delete_task", "task": "x"}],
        [{"op": "create_task", "key": "a", "title": "A"}] * 2,
        [{"op": "update_task", "task": "x", "claude_instructions_md": "x"}],
        [{"op": "update_task", "task": "x", "reason": "none"}],
    ):
        with pytest.raises(ValueError):
            ChangesetCreate.model_validate({"title": "T", "items": bad})


def test_the_plan_may_have_changed_since(plan):
    project, task = plan
    changeset = _propose(project, _items(task))
    tasks_core.delete(task.id)
    db.session.commit()
    with pytest.raises(changesets_core.ChangesetError, match="changed since"):
        changesets_core.apply(changeset.id, [0, 3])
    db.session.expire_all()
    assert db.session.get(Changeset, changeset.id).status == "proposed"
    assert db.session.scalar(db.select(Task).where(Task.title == "Connector")) is None  # all or nothing


def test_pages_api_and_tool(app, signed_in):
    from app.features.claude import mcp_server
    from tests.test_claude_mcp import _call, _data

    project = signed_in.post("/api/projects", json={"name": "Pandora"}).json["project"]
    server = mcp_server.build(app, None)
    assert mcp_server.PROPOSAL_TOOLS == ("propose_changeset",)
    items = [
        {"op": "create_task", "key": "a", "title": "<b>A</b>", "project": "pandora"},
        {"op": "create_task", "key": "b", "title": "B", "project": "pandora"},
    ]
    made = _data(_call(server, "propose_changeset", {"title": "Two tasks", "items": items}))
    wrong = _call(server, "propose_changeset", {"title": "T", "items": [{"op": "create_task", "key": "A"}]})
    assert wrong.is_error and "title" in wrong.content[0].text
    page = signed_in.get(made["review"]).data
    assert b"&lt;b&gt;A&lt;/b&gt;" in page and b"Dismiss everything" in page
    assert b"Two tasks" in signed_in.get("/changesets").data and b"Two tasks" in signed_in.get("/claude").data
    assert signed_in.post(f"{made['review']}/apply", data={}).status_code == 302  # nothing kept
    state = _data(_call(server, "changeset_state", {"changeset_id": made["id"]}))
    assert state["status"] == "proposed"
    done = signed_in.post(f"/api/changesets/{made['id']}/apply", json={"keep": [1]})
    assert done.status_code == 200 and done.json["changeset"]["kept"] == 1
    assert _data(_call(server, "changeset_state", {"changeset_id": made["id"]}))["kept"] == [2]
    assert signed_in.post(f"/api/changesets/{made['id']}/dismiss").status_code == 409
    assert signed_in.get("/api/changesets?status=applied").json["total"] == 1
    again = _data(_call(server, "propose_changeset", {"title": "More", "items": items[:1]}))
    signed_in.post(f"/changesets/{again['id']}/dismiss")
    assert signed_in.get(f"/api/changesets/{again['id']}").json["changeset"]["status"] == "dismissed"
    assert signed_in.get(f"/changesets/{uuid.uuid4()}").status_code == 404
    titles = [t["title"] for t in signed_in.get(f"/api/tasks?project={project['slug']}").json["items"]]
    assert titles == ["B"]
