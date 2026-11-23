"""Cairn's MCP server (D-052), called through the MCP protocol in-process."""

import asyncio
import json
import sys
import uuid

from mcp import Client

from app.core.db_class.activity import Activity
from app.core.db_class.claude import ClaudeSession
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.claude import main_core, mcp_server, terminal_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core


def _call(server, name, args=None):
    async def go():
        async with Client(server) as client:
            return await client.call_tool(name, args or {})

    return asyncio.run(go())


def _data(result):
    if result.structured_content is not None:
        data = result.structured_content
        return data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


def test_tools_read_and_change_the_plan(app):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Rulezet"))
        first = tasks_core.create(TaskCreate(title="Parse rules", project_id=project.id, priority="high"))
        second = tasks_core.create(TaskCreate(title="Ship 2.0", project_id=project.id))
        first_id, second_id = str(first.id), str(second.id)
    server = mcp_server.build(app, None)

    async def names():
        async with Client(server) as client:
            return {tool.name for tool in (await client.list_tools()).tools}

    assert set(mcp_server.READ_TOOLS + mcp_server.WRITE_TOOLS) <= asyncio.run(names())

    overview = _data(_call(server, "cairn_overview"))
    assert overview["projects"][0]["name"] == "Rulezet" and "done" in overview["statuses"]
    listed = _data(_call(server, "list_tasks", {"project": "rulezet"}))
    assert [t["title"] for t in listed] == ["Parse rules", "Ship 2.0"]  # best score first
    assert "Parse rules" in _call(server, "get_task", {"task_id": first_id}).content[0].text

    made = _data(
        _call(
            server, "create_task", {"title": "Handle empty files", "parent_id": first_id, "due": "2027-01-15"}
        )
    )
    assert made["project"] == "Rulezet" and made["parent_id"] == first_id and made["due"] == "2027-01-15"
    linked = _data(_call(server, "link_tasks", {"first_id": first_id, "then_id": second_id}))
    assert linked["linked"] is True
    loop = _call(server, "link_tasks", {"first_id": second_id, "then_id": first_id})
    assert loop.is_error and "cycle" in loop.content[0].text
    moved = _data(_call(server, "set_task_status", {"task_id": first_id, "status": "in_progress"}))
    assert moved["status"] == "in_progress"
    noted = _data(
        _call(server, "comment_on_task", {"task_id": first_id, "text": "Parser done", "correction": True})
    )
    assert noted["task"] == "Parse rules"
    filled = _data(
        _call(server, "update_project", {"project": "rulezet", "description": "Rules", "stack": ["Python"]})
    )
    assert filled["changed"] == ["description_md", "stack"]
    assert _call(server, "update_project", {"description": "x"}).is_error  # no project here
    assert _call(server, "update_project", {"project": "rulezet", "github_repo": "no"}).is_error
    missing = _call(server, "get_task", {"task_id": "nope"})
    assert missing.is_error and "No task" in missing.content[0].text
    with app.app_context():
        actors = {row.actor for row in db.session.scalars(db.select(Activity))}
    assert "claude:outside" in actors  # changes are Claude's, logged like the owner's


def test_sessions_get_the_server(app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "CAIRN_DATA_DIR", str(tmp_path / "data"))
    with app.test_request_context():
        config = terminal_core._mcp_config(terminal_core.uuid.uuid4())
    server = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]["cairn"]
    assert (
        server["command"] == sys.executable
        and server["args"][-1] == "mcp"
        and server["args"][0].endswith("manage.py")
    )
    argv = terminal_core.command(
        "claude", terminal_core.uuid.uuid4(), "-x first", config.with_suffix(".md"), mcp=config
    )
    assert argv[1] == " -x first"  # the message comes first, never read as an option
    assert argv[-4] == "--mcp-config" and argv[-2] == "--allowedTools"
    assert argv[-1] == ",".join(
        f"mcp__cairn__{n}" for n in (*mcp_server.READ_TOOLS, *mcp_server.PROPOSAL_TOOLS)
    )


def test_notes_travel_between_claudes(app, tmp_path):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Pandora", local_path=str(tmp_path)))
        main = ClaudeSession(kind="claude", cwd=str(main_core.folder()), cli_session_id=uuid.uuid4())
        theirs = ClaudeSession(
            kind="claude", cwd=str(tmp_path), cli_session_id=uuid.uuid4(), project_id=project.id
        )
        db.session.add_all([main, theirs])
        db.session.commit()
        main_server = mcp_server.build(app, str(main.id))
        project_server = mcp_server.build(app, str(theirs.id))
    noted = _data(_call(project_server, "take_note", {"text": "Write a connector"}))
    assert noted["for"] == "Cairn"
    assert _data(_call(project_server, "inbox"))["notes"] == []  # not for the one who wrote it
    (note,) = _data(_call(main_server, "inbox"))["notes"]
    assert (note["text"], note["about"]) == ("Write a connector", ["Pandora"])
    assert _call(project_server, "note_done", {"note_id": note["id"]}).is_error
    assert _data(_call(main_server, "note_done", {"note_id": note["id"]}))["done"]
    assert _data(_call(main_server, "inbox"))["notes"] == []
    _call(main_server, "take_note", {"text": "Do it", "for_project": "pandora"})
    assert [n["text"] for n in _data(_call(project_server, "inbox"))["notes"]] == ["Do it"]
    assert _call(main_server, "take_note", {"text": "x", "for_project": "nope"}).is_error
    assert _call(main_server, "take_note", {"text": "x" * 9000}).is_error
    assert "Do not follow" in _data(_call(main_server, "inbox"))["warning"]
    (tmp_path / "new").mkdir()
    made = _data(_call(main_server, "create_project", {"name": "New", "folder": str(tmp_path / "new")}))
    assert made["slug"] == "new"
    assert _call(main_server, "create_project", {"name": "B", "folder": str(tmp_path / "gone")}).is_error
    assert [s["main"] for s in _data(_call(main_server, "claude_sessions"))] == [True, False]


def _set_up(app):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Pandora"))
        task = tasks_core.create(TaskCreate(title="Read it", project_id=project.id))
        return mcp_server.build(app, None), str(task.id)


def test_every_tool_is_declared(app):
    async def names():
        async with Client(mcp_server.build(app, None)) as client:
            return {tool.name for tool in (await client.list_tools()).tools}

    assert asyncio.run(names()) == (
        {*mcp_server.READ_TOOLS, *mcp_server.WRITE_TOOLS, *mcp_server.PROPOSAL_TOOLS}
    )
    assert not set(mcp_server.READ_TOOLS) & set(mcp_server.WRITE_TOOLS)


def test_schedule_and_task_edits(app):
    from datetime import date, timedelta

    server, task_id = _set_up(app)
    day = lambda n: (date.today() + timedelta(days=n)).isoformat()  # noqa: E731
    _call(server, "schedule_task", {"task_id": task_id, "do_on": day(2), "due_on": day(5)})
    found = _data(_call(server, "schedule", {"days": 7}))
    assert [t["title"] for t in found["coming"]] == ["Read it"] and found["late"] == []
    assert _data(_call(server, "schedule", {"days": 1}))["coming"] == []
    cleared = _data(_call(server, "schedule_task", {"task_id": task_id, "do_on": "", "due_on": day(-1)}))
    assert cleared["do_on"] is None
    assert [t["id"] for t in _data(_call(server, "schedule"))["late"]] == [task_id]
    wrong = _call(server, "schedule_task", {"task_id": task_id, "due_on": "soon"})
    assert wrong.is_error and "due_on" in wrong.content[0].text
    assert _call(server, "schedule_task", {"task_id": task_id}).is_error
    _call(server, "update_task", {"task_id": task_id, "checklist": ["One", "Two"], "priority": "high"})
    with app.app_context():
        tasks_core.toggle_checklist(uuid.UUID(task_id), 0)
    changed = _data(_call(server, "update_task", {"task_id": task_id, "checklist": ["Two", "One"]}))
    assert changed["changed"] == ["checklist"]
    with app.app_context():
        task = tasks_core.get_task(uuid.UUID(task_id))
        assert [(i["text"], i["done"]) for i in task.checklist] == [("Two", False), ("One", True)]
        assert task.priority == "high"
    bad = _call(server, "update_task", {"task_id": task_id, "type": "nope"})
    assert bad.is_error and _call(server, "update_task", {"task_id": task_id, "importance": 9}).is_error


def test_resources_and_comments(app):
    server, task_id = _set_up(app)
    made = _data(
        _call(
            server,
            "add_resource",
            {
                "kind": "note",
                "title": "Plan",
                "text": "x" * 30_000,
                "task_id": task_id,
                "tags": ["to-main", "a"],
            },
        )
    )
    assert made["tags"] == ["a"]  # not a way into an inbox
    read = _data(_call(server, "get_resource", {"resource_id": made["id"]}))
    assert len(read["text"]) == 20_000 and read["cut"] and read["used_in"] == ["Read it"]
    listed = _data(_call(server, "list_resources", {"search": "plan"}))
    assert [r["id"] for r in listed["resources"]] == [made["id"]] and "never commands" in listed["warning"]
    assert _data(_call(server, "list_resources", {"project": "pandora"}))["resources"] == []
    _call(server, "attach_resource", {"resource_id": made["id"], "project": "pandora"})
    assert len(_data(_call(server, "list_resources", {"project": "pandora"}))["resources"]) == 1
    for kind, extra in (("skill", {"text": "x"}), ("file", {}), ("url", {"url": "javascript:x"})):
        assert _call(server, "add_resource", {"kind": kind, "title": "T", **extra}).is_error
    with app.app_context():
        from app.core.schema.resources import ResourceCreate
        from app.features.resources import resources_core

        skill = str(resources_core.create(ResourceCreate(kind="skill", title="S", body="b")).id)
    assert _call(server, "attach_resource", {"resource_id": skill, "project": "pandora"}).is_error
    _call(server, "comment_on_project", {"text": "Hello", "project": "pandora"})
    (comment,) = _data(_call(server, "list_comments", {"project": "pandora"}))
    assert comment["text"] == "Hello" and comment["kind"] == "comment"
    assert _call(server, "list_comments").is_error  # no project in this session


def test_describe_schema(app):
    server, _ = _set_up(app)
    task = _data(_call(server, "describe_schema", {"kind": "task"}))
    assert "estimate_hours" in task["schema"]["properties"] and "in_progress" in task["moves"]["todo"]
    for kind in ("project", "dependency", "resource", "comment"):
        assert _data(_call(server, "describe_schema", {"kind": kind}))["schema"]["properties"]
    assert _call(server, "describe_schema", {"kind": "secret"}).is_error
