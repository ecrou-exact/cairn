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
def fake_claude(app, monkeypatch, tmp_path):
    monkeypatch.setitem(app.config, "CAIRN_DATA_DIR", str(tmp_path / "data"))  # never the real data folder
    monkeypatch.setattr(terminal_core.connections_core, "claude_code_path", lambda: sys.executable)
    monkeypatch.setattr(
        terminal_core,
        "command",
        lambda exe, sid, first, rules=None, resume=False, mcp=None: [
            exe,
            "-c",
            FAKE,
            "--resume" if resume else "--session-id",
            str(sid),
            str(rules),
            *([first] if first else []),
        ],
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


def test_transcript_gives_the_last_steps(tmp_path, monkeypatch, ctx):
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path)
    cwd, sid = str(tmp_path / "repo"), str(uuid.uuid4())
    folder = tmp_path / transcript_core.folder_key(cwd)
    folder.mkdir()
    at = "2026-11-22T13:00:00Z"
    lines = [
        {"type": "user", "timestamp": at, "message": {"content": "Fix   the parser"}},
        {"type": "user", "timestamp": at, "message": {"content": "<command-name>/clear</command-name>"}},
        {
            "type": "assistant",
            "timestamp": at,
            "message": {
                "content": [
                    {"type": "text", "text": "Looking at it."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": str(tmp_path / "repo" / "a.py")},
                    },
                    {"type": "tool_use", "name": "mcp__cairn__set_task_status", "input": {}},
                ]
            },
        },
        {"type": "user", "timestamp": at, "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
    ]
    (folder / f"{sid}.jsonl").write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    usage = transcript_core.session_usage(cwd, sid)
    assert [(e["who"], e["label"]) for e in usage.events] == [
        ("you", "Fix the parser"),  # commands Claude Code records as user turns are left out
        ("claude", "Looking at it."),
        ("claude", "Reading a.py"),  # paths inside the folder are shown relative to it
        ("claude", "Cairn: set task status"),
    ]
    assert (usage.now, usage.now_icon) == ("Cairn: set task status", "fa-layer-group")
    assert transcript_core.describe_tool("Bash", {"command": "ls", "description": "List files"}, cwd) == (
        "fa-terminal",
        "List files",
    )
    assert transcript_core.describe_tool("Odd", "not a dict", cwd) == ("fa-gear", "Odd")


def test_host_is_the_closest_editor_or_terminal(monkeypatch):
    class Fake:
        def __init__(self, chain):
            self.chain = chain

        def parent(self):
            return Fake(self.chain[1:]) if len(self.chain) > 1 else None

        def name(self):
            return self.chain[0]

    chain = ["claude.exe", "bash", "Code.exe", "explorer.exe"]
    monkeypatch.setattr(transcript_core.psutil, "Process", lambda pid: Fake(chain))
    assert transcript_core.host_of(1) == "VS Code"  # an editor wins over the shell inside it
    chain[:] = ["claude", "zsh", "launchd"]
    assert transcript_core.host_of(1) == "zsh"
    chain[:] = ["claude"]
    assert transcript_core.host_of(1) == "a terminal"


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


def test_presets_build_the_first_message_and_title(ctx, tmp_path):
    project = projects_core.create(ProjectCreate(name="Cairn", local_path=str(tmp_path)))
    task = tasks_core.create(TaskCreate(title="Parser", project_id=project.id))
    pr = SessionStart(project_id=project.id, preset="pr", detail="https://github.com/o/r/pull/42")
    assert "https://github.com/o/r/pull/42" in terminal_core._first_message(pr, None)
    assert "wait for my go" in terminal_core._first_message(pr, None)
    assert terminal_core._title(pr, project, None) == "PR 42"
    fix = SessionStart(task_id=task.id, preset="fix", detail="crash on empty file")
    message = terminal_core._first_message(fix, task)
    assert "crash on empty file" in message and "“Parser”" in message
    assert terminal_core._first_message(SessionStart(project_id=project.id), None) is None
    with pytest.raises(ValueError, match="pull request"):
        SessionStart(project_id=project.id, preset="pr", detail="not a url")
    with pytest.raises(ValueError, match="describe the bug"):
        SessionStart(project_id=project.id, preset="fix")
    with pytest.raises(ValueError, match="pick the task"):
        SessionStart(project_id=project.id, preset="task")


def test_rules_reach_every_session(app, ctx, tmp_path, fake_claude):
    project = projects_core.create(
        ProjectCreate(name="Rulezet", local_path=str(tmp_path), claude_instructions_md="Use pytest -q.")
    )
    session = terminal_core.start(SessionStart(project_id=project.id, preset="review"))
    seen, _ = _wait_for(session.id, "ARGS")
    rules = next(part for part in seen.split("'") if part.endswith(".md"))
    from pathlib import Path

    text = Path(rules).read_text(encoding="utf-8")
    assert "No AI attribution" in text and "Use pytest -q." in text


def test_new_project_and_resume(ctx, tmp_path, fake_claude, monkeypatch):
    from app.core.schema.claude import NewProjectStart

    folder = tmp_path / "fresh"
    session = terminal_core.start_new_project(
        NewProjectStart(name="Fresh", folder=str(folder), description="A CLI")
    )
    assert folder.is_dir() and session.title == "Set up Fresh"
    assert projects_core.by_folder(str(folder)).name == "Fresh"
    (tmp_path / "busy").mkdir()
    (tmp_path / "busy" / "x.txt").write_text("x")
    with pytest.raises(terminal_core.TerminalError, match="not empty"):
        terminal_core.start_new_project(NewProjectStart(name="Busy", folder=str(tmp_path / "busy")))
    with pytest.raises(terminal_core.TerminalError, match="full path"):
        terminal_core.start_new_project(NewProjectStart(name="Rel", folder="relative/dir"))

    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path / "transcripts")
    conversation = uuid.uuid4()
    with pytest.raises(terminal_core.TerminalError, match="no conversation"):
        terminal_core.resume(conversation, str(folder))
    stored = tmp_path / "transcripts" / transcript_core.folder_key(str(folder))
    stored.mkdir(parents=True)
    (stored / f"{conversation}.jsonl").write_text("{}", encoding="utf-8")
    resumed = terminal_core.resume(conversation, str(folder))
    seen, _ = _wait_for(resumed.id, "ARGS")
    assert "--resume" in seen and str(conversation) in seen
    assert resumed.project_id == projects_core.by_folder(str(folder)).id
    assert terminal_core.resume(conversation, str(folder)).id == resumed.id  # already open: the same one


def test_launcher_api(app, signed_in, tmp_path, fake_claude):
    project = signed_in.post("/api/projects", json={"name": "Launch", "local_path": str(tmp_path)}).json[
        "project"
    ]
    targets = signed_in.get("/api/claude/targets").json
    assert {p["key"] for p in targets["presets"]} == {"free", "task", "pr", "fix", "review"}
    assert any(p["id"] == project["id"] and p["folder"] for p in targets["projects"])
    made = signed_in.post(
        "/api/claude/projects", json={"name": "Brand new", "folder": str(tmp_path / "brand-new")}
    )
    assert made.status_code == 201 and made.json["session"]["project"]["name"] == "Brand new"
    bad = signed_in.post(
        "/api/claude/sessions", json={"project_id": project["id"], "preset": "pr", "detail": "x"}
    )
    assert bad.status_code == 422
    page = signed_in.get("/tasks").data
    assert b"<cn-claude-launch>" in page and b"data-claude-launch" in page


def test_claude_starts_as_a_fresh_session(monkeypatch):
    for key in (
        "CLAUDECODE",
        "CLAUDE_CODE_CHILD_SESSION",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_MESSAGING_TOKEN",
        "CLAUDE_PID",
    ):
        monkeypatch.setenv(key, "parent")
    monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")  # the owner's own setting stays
    env = terminal_core._environment()
    assert not {
        k
        for k in env
        if k.upper().startswith(
            ("CLAUDECODE", "CLAUDE_CODE_CHILD", "CLAUDE_CODE_SESSION", "CLAUDE_CODE_MESSAGING", "CLAUDE_PID")
        )
    }
    assert env["CLAUDE_CODE_USE_BEDROCK"] == "1" and env["TERM"] == "xterm-256color"
