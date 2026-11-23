"""Clear the ended sessions (D-092); run a task's branch (D-091)."""

import uuid

from app.core.db_class.claude import ClaudeSession
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.history import batch, undo
from app.features.claude import claude_core, terminal_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core
from app.features.worklinks import worklinks_core


def _session(status):
    row = ClaudeSession(cwd="/w", cli_session_id=uuid.uuid4(), kind="claude", status=status)
    db.session.add(row)
    db.session.commit()
    return row


def test_ended_sessions_are_cleared_and_come_back(ctx):
    ended, running = _session("ended"), _session("running")
    with batch() as batch_id:
        assert claude_core.clear_ended() == 1
    assert ended.deleted_at is not None and running.deleted_at is None
    undo(batch_id)
    assert ended.deleted_at is None
    assert claude_core.clear_ended() == 1 and claude_core.clear_ended() == 0


def test_the_pages(app, signed_in, tmp_path, monkeypatch):
    with app.app_context():
        _session("ended")
        project = projects_core.create(ProjectCreate(name="Loo", local_path=str(tmp_path)))
        task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
        worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind="branch", ref="tree"))
        task_id = str(task.id)
    assert "Clear ended sessions" in signed_in.get("/claude").data.decode()
    assert b"1 ended session cleared;" in signed_in.post("/claude/clean", follow_redirects=True).data
    assert signed_in.post("/api/claude/clean").json == {"cleared": 0}
    started = []
    monkeypatch.setattr(
        terminal_core, "start", lambda data: started.append(data) or type("S", (), {"id": "x"})()
    )
    assert "Run with Claude" in signed_in.get(f"/tasks/{task_id}?tab=git").data.decode()
    signed_in.post(f"/tasks/{task_id}/run", data={"branch": "tree"})
    assert started[0].preset == "run" and "`tree`" in started[0].detail and started[0].worktree is False
    refused = signed_in.post(f"/tasks/{task_id}/run", data={"folder": "/"}, follow_redirects=True)
    assert b"not a copy of the project" in refused.data
