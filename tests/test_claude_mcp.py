"""Cairn's MCP server (D-052), called through the MCP protocol in-process."""

import asyncio
import json
import sys

from mcp import Client

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.claude import mcp_server, terminal_core
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
    assert argv[-1] == ",".join(f"mcp__cairn__{n}" for n in mcp_server.READ_TOOLS)  # writes still ask
