"""A Claude on a task keeps its checklist and subtasks true (D-098)."""

from app.core.schema.claude import SessionStart
from app.core.schema.planning import TaskCreate
from app.features.claude import mcp_server, terminal_core
from app.features.tasks import tasks_core
from tests.test_claude_mcp import _call, _data


def test_tick_and_the_brief(app):
    with app.app_context():
        task = tasks_core.create(
            TaskCreate(title="Tree", checklist=[{"text": "Draw it"}, {"text": "Test it"}])
        )
        task_id = str(task.id)
        message = terminal_core._first_message(SessionStart(task_id=task.id, preset="task"), task)
    assert "tick_checklist" in message and task_id in message and "subtask" in message
    server = mcp_server.build(app, None)
    done = _data(_call(server, "tick_checklist", {"task_id": task_id, "item": "draw it"}))
    assert done["left"] == ["Test it"]
    assert _data(_call(server, "tick_checklist", {"task_id": task_id, "item": "2"}))["left"] == []
    assert _call(server, "tick_checklist", {"task_id": task_id, "item": "nope"}).is_error
    with app.app_context():
        assert all(item["done"] for item in tasks_core.get_task(task.id).checklist)
    assert "tick_checklist" in mcp_server.WRITE_TOOLS
