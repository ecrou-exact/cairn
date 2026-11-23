"""The main Claude opens a project's Claude and hands it work (D-068)."""

import threading
import time
import uuid
from datetime import timedelta

import pytest

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeRequest, ClaudeSession
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.claude import handover_core, main_core, mcp_server, terminal_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core
from tests.test_claude import _wait_for, fake_claude  # noqa: F401 (a fixture)


@pytest.fixture
def main(ctx, fake_claude):  # noqa: F811
    session = ClaudeSession(kind="claude", cwd=str(main_core.folder()), cli_session_id=uuid.uuid4())
    db.session.add(session)
    db.session.commit()
    return session


def _answered(request):
    handover_core.serve_pending()
    return handover_core.wait(request.id, seconds=0)


def test_work_is_handed_to_a_projects_claude(main, tmp_path):
    project = projects_core.create(ProjectCreate(name="Pandora", local_path=str(tmp_path)))
    task = tasks_core.create(TaskCreate(title="Write the connector", project_id=project.id))
    done = _answered(handover_core.ask(main, project, task, "Only the reading part."))
    assert done.status == "opened"
    session = terminal_core.get(done.session_id)
    assert (session.project_id, session.task_id) == (project.id, task.id)
    seen, _ = _wait_for(session.id, "reading part")
    assert "Write the connector" in seen  # the task's brief
    again = _answered(handover_core.ask(main, project, None, "More"))
    assert again.status == "refused" and "already open" in again.error  # never typed into


def test_only_the_main_claude_and_within_limits(main, tmp_path, monkeypatch):
    project = projects_core.create(ProjectCreate(name="P", local_path=str(tmp_path)))
    other = tasks_core.create(TaskCreate(title="Elsewhere"))
    theirs = ClaudeSession(
        kind="claude", cwd=str(tmp_path), cli_session_id=uuid.uuid4(), project_id=project.id
    )
    db.session.add(theirs)
    db.session.commit()
    for session in (theirs, None):
        with pytest.raises(handover_core.HandoverError, match="Only Cairn's main"):
            handover_core.ask(session, project, None, "x")
    for task, work in ((other, "x"), (None, "  "), (None, "x" * 7001)):
        with pytest.raises(handover_core.HandoverError):
            handover_core.ask(main, project, task, work)
    loose = projects_core.create(ProjectCreate(name="Loose"))
    with pytest.raises(handover_core.HandoverError, match="no local folder"):
        handover_core.ask(main, loose, None, "x")
    assert len("x" * handover_core.WORK_LIMIT + handover_core.PREAMBLE) <= 8000

    old = handover_core.ask(main, project, None, "x")
    old.created_at = utcnow() - timedelta(minutes=5)
    db.session.commit()
    assert "too long ago" in _answered(old).error
    monkeypatch.setattr(handover_core, "get_setting", lambda key: 0)
    assert "already open" in _answered(handover_core.ask(main, project, None, "x")).error
    unanswered = handover_core.wait(handover_core.ask(main, project, None, "x").id, seconds=0)
    assert unanswered.status == "refused" and handover_core.serve_pending() == 0  # not opened later
    claimed = handover_core.ask(main, project, None, "x")
    claimed.status = "opening"
    db.session.commit()
    assert handover_core.serve_pending() == 0  # never opened twice
    assert not [r for r in db.session.scalars(db.select(ClaudeRequest)) if r.status == "opened"]


def test_the_tool_asks_and_waits(app, main, tmp_path):
    from tests.test_claude_mcp import _call, _data

    project = projects_core.create(ProjectCreate(name="Pandora", local_path=str(tmp_path)))
    server, project_id = mcp_server.build(app, str(main.id)), project.id
    assert "open_project_claude" in mcp_server.WRITE_TOOLS  # so Claude Code asks, in every mode
    answers = []

    def call():
        answers.append(_call(server, "open_project_claude", {"project": "pandora", "work": "Read it"}))

    asking = threading.Thread(target=call)
    asking.start()
    deadline = time.monotonic() + 10
    while asking.is_alive() and time.monotonic() < deadline:
        handover_core.serve_pending()
        db.session.rollback()
        time.sleep(0.2)
    asking.join(15)
    assert "/claude/sessions/" in _data(answers[0])["url"]
    db.session.expire_all()
    opened = [s for s in terminal_core.sessions() if s.project_id == project_id]
    assert len(opened) == 1
