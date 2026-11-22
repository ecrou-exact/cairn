"""Claude Code in a terminal (D-050): sessions, the terminal round trip, the overview."""

import json
import sys
import time
import uuid

import pytest

from app.core.schema.claude import SessionStart
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.claude import terminal_core, transcript_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core

# Stands in for `claude`: prints its arguments, echoes one line typed in, then exits.
FAKE = "import sys; print('ARGS', sys.argv[1:]); line = input(); print('GOT', line)"


@pytest.fixture
def fake_claude(monkeypatch):
    monkeypatch.setattr(terminal_core.connections_core, "claude_code_path", lambda: sys.executable)
    monkeypatch.setattr(
        terminal_core,
        "command",
        lambda exe, sid, first: [exe, "-c", FAKE, "--session-id", str(sid), *([first] if first else [])],
    )


def _wait_for(session_id, needle, timeout=20.0):
    after, seen = 0, ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunks, ended = terminal_core.output(session_id, after, wait=0.5)
        if chunks:
            after = chunks[-1][0]
            seen += "".join(text for _, text in chunks)
        if needle in seen or ended:
            return seen, ended
    return seen, False


def test_session_runs_in_the_project_folder_and_ends(ctx, tmp_path, fake_claude):
    project = projects_core.create(ProjectCreate(name="Rulezet", local_path=str(tmp_path)))
    task = tasks_core.create(TaskCreate(title="Fix the parser", project_id=project.id))
    session = terminal_core.start(SessionStart(task_id=task.id, with_brief=True))
    assert (session.cwd, session.status, session.project_id) == (str(tmp_path), "running", project.id)
    seen, _ = _wait_for(session.id, "ARGS")
    assert "--session-id" in seen and "Fix the parser" in seen  # the brief is the first message
    terminal_core.write(session.id, "hello\r")
    seen, _ = _wait_for(session.id, "GOT hello")
    assert "GOT hello" in seen
    deadline = time.monotonic() + 20
    while terminal_core.is_running(session.id) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not terminal_core.is_running(session.id)
    from app.core.extensions import db

    db.session.expire_all()
    assert terminal_core.get(session.id).status == "ended"
    with pytest.raises(terminal_core.TerminalError, match="not running"):
        terminal_core.write(session.id, "x")


def test_where_claude_may_run(ctx, tmp_path, fake_claude):
    no_folder = projects_core.create(ProjectCreate(name="No folder"))
    with pytest.raises(terminal_core.TerminalError, match="local folder"):
        terminal_core.start(SessionStart(project_id=no_folder.id))
    gone = projects_core.create(ProjectCreate(name="Gone", local_path=str(tmp_path / "missing")))
    with pytest.raises(terminal_core.TerminalError, match="does not exist"):
        terminal_core.start(SessionStart(project_id=gone.id))
    loose = tasks_core.create(TaskCreate(title="No project"))
    with pytest.raises(terminal_core.TerminalError, match="project first"):
        terminal_core.start(SessionStart(task_id=loose.id))
    with pytest.raises(ValueError):
        SessionStart(project_id=no_folder.id, with_brief=True)


def test_transcript_gives_the_context_in_use(tmp_path, monkeypatch, ctx):
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path)
    cwd, sid = "C:\\Work\\my_repo", str(uuid.uuid4())
    folder = tmp_path / "C--Work-my-repo"
    folder.mkdir()
    lines = [
        {"type": "ai-title", "aiTitle": "Parser fixes", "sessionId": sid},
        {
            "type": "assistant",
            "message": {
                "model": "claude-opus-5-5",
                "usage": {
                    "input_tokens": 1000,
                    "cache_read_input_tokens": 49000,
                    "cache_creation_input_tokens": 0,
                },
            },
        },
        "not json",
    ]
    (folder / f"{sid}.jsonl").write_text(
        "\n".join(entry if isinstance(entry, str) else json.dumps(entry) for entry in lines), encoding="utf-8"
    )
    usage = transcript_core.session_usage(cwd, sid)
    assert (usage.context_tokens, usage.window, usage.percent, usage.title, usage.model) == (
        50000,
        200000,
        25.0,
        "Parser fixes",
        "claude-opus-5-5",
    )
    (folder / f"{sid}.jsonl").write_text(
        json.dumps({"type": "assistant", "message": {"model": "m", "usage": {"input_tokens": 300000}}}),
        encoding="utf-8",
    )
    assert transcript_core.session_usage(cwd, sid).window == 1_000_000  # past 200k: the next size
    assert transcript_core.session_usage(cwd, "missing").transcript is False


def test_claude_pages_and_api(app, signed_in, tmp_path, fake_claude):
    project = signed_in.post("/api/projects", json={"name": "Vitrine", "local_path": str(tmp_path)}).json[
        "project"
    ]
    started = signed_in.post("/api/claude/sessions", json={"project_id": project["id"]})
    assert started.status_code == 201
    sid = started.json["session"]["id"]
    page = signed_in.get(f"/claude/sessions/{sid}")
    csp = page.headers["Content-Security-Policy"]
    assert page.status_code == 200 and b"<cn-terminal" in page.data and "style-src-elem 'self' 'nonce-" in csp
    assert "unsafe-inline" not in csp.split("style-src-elem")[1].split(";")[0]
    assert "script-src 'self'" in csp
    stream = signed_in.get(f"/claude/sessions/{sid}/stream?after=0")
    assert stream.mimetype == "text/event-stream"
    assert signed_in.post(f"/api/claude/sessions/{sid}/input", json={"data": "hi\r"}).status_code == 200
    assert signed_in.post(
        f"/api/claude/sessions/{sid}/resize", json={"cols": 100, "rows": 30}
    ).status_code in (200, 409)
    assert signed_in.post(f"/api/claude/sessions/{sid}/input", json={}).status_code == 422
    overview = signed_in.get("/api/claude/sessions").json
    assert any(s["id"] == sid for s in overview["sessions"]) and "outside" in overview
    assert b"Claude sessions" in signed_in.get("/claude").data
    assert b"Open Claude in this project" in signed_in.get(f"/projects/{project['slug']}?tab=claude").data
    assert (
        signed_in.post(
            "/api/claude/sessions", json={"project_id": project["id"], "task_id": project["id"]}
        ).status_code
        == 422
    )
    assert signed_in.post(f"/api/claude/sessions/{uuid.uuid4()}/stop").status_code == 409
