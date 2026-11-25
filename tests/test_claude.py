"""Claude Code in a terminal (D-050): sessions, the terminal round trip, the overview."""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid

import psutil
import pytest

from app.core.schema.claude import OutsideStop, ResumeStart, SessionLink, SessionStart
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.resources import LinkCreate, ResourceCreate
from app.features.claude import limits_core, main_core, skills_core, terminal_core, transcript_core
from app.features.projects import projects_core
from app.features.resources import resources_core
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
        lambda exe, sid, first, rules=None, resume=False, **_: [
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
    assert terminal_core._title(pr, project.name, None) == "PR 42"
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
    read = terminal_core.start_new_project(NewProjectStart(name="Busy", folder=str(tmp_path / "busy")))
    assert read.title == "Read Busy"  # a folder with files is read, not set up
    assert "without changing any file" in _wait_for(read.id, "ARGS")[0].replace("\r\n", "")
    with pytest.raises(terminal_core.TerminalError, match="already the folder"):
        terminal_core.start_new_project(NewProjectStart(name="Again", folder=str(tmp_path / "busy")))
    with pytest.raises(terminal_core.TerminalError, match="full path"):
        terminal_core.start_new_project(NewProjectStart(name="Rel", folder="relative/dir"))

    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path / "transcripts")
    conversation = uuid.uuid4()
    request = ResumeStart(cli_session_id=conversation, cwd=str(folder))
    with pytest.raises(terminal_core.TerminalError, match="no conversation"):
        terminal_core.resume(request)
    stored = tmp_path / "transcripts" / transcript_core.folder_key(str(folder))
    stored.mkdir(parents=True)
    (stored / f"{conversation}.jsonl").write_text("{}", encoding="utf-8")
    resumed = terminal_core.resume(request)
    seen, _ = _wait_for(resumed.id, "ARGS")
    assert "--resume" in seen and str(conversation) in seen
    assert resumed.project_id == projects_core.by_folder(str(folder)).id
    assert terminal_core.resume(request).id == resumed.id  # already open: the same one


def test_launcher_api(app, signed_in, tmp_path, fake_claude):
    project = signed_in.post("/api/projects", json={"name": "Launch", "local_path": str(tmp_path)}).json[
        "project"
    ]
    targets = signed_in.get("/api/claude/targets").json
    assert {p["key"] for p in targets["presets"]} == {"free", "task", "pr", "fix", "review", "fill", "run"}
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


def test_whitespace_keys_reach_the_terminal(app, signed_in, tmp_path, fake_claude):
    project = signed_in.post("/api/projects", json={"name": "Keys", "local_path": str(tmp_path)}).json[
        "project"
    ]
    sid = signed_in.post("/api/claude/sessions", json={"project_id": project["id"]}).json["session"]["id"]
    _wait_for(uuid.UUID(sid), "ARGS")
    for key in ("a", " ", "b", "\r"):  # each its own request, as typed
        sent = signed_in.post(f"/api/claude/sessions/{sid}/input", json={"data": key})
        assert sent.status_code == 200, (key, sent.json)
    seen, _ = _wait_for(uuid.UUID(sid), "GOT a b")
    assert "GOT a b" in seen


def test_stop_returns_while_the_program_is_silent(ctx, tmp_path, fake_claude):
    project = projects_core.create(ProjectCreate(name="Silent", local_path=str(tmp_path)))
    session = terminal_core.start(SessionStart(project_id=project.id))
    _wait_for(session.id, "ARGS")
    pid = session.pid
    stopper = threading.Thread(target=terminal_core.stop, args=(session.id,), daemon=True)
    with ctx.app_context():
        stopper.start()
    stopper.join(10)
    assert not stopper.is_alive()
    deadline = time.monotonic() + 10
    while terminal_core.is_running(session.id) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not terminal_core.is_running(session.id) and not psutil.pid_exists(pid)


@pytest.fixture
def open_outside(tmp_path, monkeypatch):
    """A process standing in for a Claude Code outside Cairn, registered with a conversation."""
    conversation, folder = uuid.uuid4(), tmp_path / "work"
    folder.mkdir()
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path / "transcripts")
    monkeypatch.setattr(transcript_core, "registry_root", lambda: tmp_path / "registry")
    stored = tmp_path / "transcripts" / transcript_core.folder_key(str(folder))
    stored.mkdir(parents=True)
    (stored / f"{conversation}.jsonl").write_text("{}", encoding="utf-8")
    (stored / f"{uuid.uuid4()}.jsonl").write_text("{}", encoding="utf-8")  # a newer, other conversation
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], cwd=folder)
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry" / f"{process.pid}.json").write_text(
        json.dumps({"pid": process.pid, "sessionId": str(conversation), "startedAt": time.time() * 1000}),
        encoding="utf-8",
    )
    name = psutil.Process.name
    monkeypatch.setattr(  # only this process is a "claude": its parent (these tests) is not
        psutil.Process, "name", lambda self: "claude" if self.pid == process.pid else name(self)
    )
    yield process, conversation, folder
    process.kill()
    process.wait()


def test_a_conversation_open_elsewhere_is_moved_not_doubled(ctx, fake_claude, open_outside):
    process, conversation, folder = open_outside
    assert transcript_core.registered(psutil.Process(process.pid)) == str(conversation)
    request = ResumeStart(cli_session_id=conversation, cwd=str(folder))
    with pytest.raises(terminal_core.TerminalError, match="open in another terminal"):
        terminal_core.resume(request)
    assert process.poll() is None and not terminal_core.sessions()  # refused: nothing touched
    session = terminal_core.resume(request.model_copy(update={"take_over": True}))
    process.wait(5)
    seen, _ = _wait_for(session.id, "ARGS")
    assert str(conversation) in seen


def test_taking_over_never_closes_what_cairn_runs_in(ctx, fake_claude, open_outside, monkeypatch):
    _process, conversation, folder = open_outside
    parent = psutil.Process().ppid()
    monkeypatch.setattr(transcript_core, "open_elsewhere", lambda *_: [parent])
    closed = []
    monkeypatch.setattr(psutil.Process, "terminate", lambda self: closed.append(self.pid))
    with pytest.raises(terminal_core.TerminalError, match="started from this Claude Code"):
        terminal_core.resume(ResumeStart(cli_session_id=conversation, cwd=str(folder), take_over=True))
    assert not closed


def test_a_registration_left_by_a_dead_process_is_ignored(open_outside, tmp_path):
    process, conversation, _ = open_outside
    path = tmp_path / "registry" / f"{process.pid}.json"
    path.write_text(json.dumps({"sessionId": str(conversation), "startedAt": 1000}), encoding="utf-8")
    assert transcript_core.registered(psutil.Process(process.pid)) is None  # the pid was reused
    path.write_text("not json", encoding="utf-8")
    assert transcript_core.registered(psutil.Process(process.pid)) is None


def test_a_free_session_is_linked_later(ctx, tmp_path, fake_claude):
    folder = tmp_path / "pandora"
    folder.mkdir()
    (folder / "README.md").write_text("Pandora")
    session = terminal_core.start(SessionStart(folder=str(folder)))
    assert session.project_id is None and session.title == "pandora"
    linked, reader = terminal_core.link(session.id, SessionLink(name="Pandora", read=True))
    project = projects_core.by_folder(str(folder))
    assert linked.project_id == project.id == reader.project_id and reader.id != session.id
    with pytest.raises(terminal_core.TerminalError, match="already the folder"):
        terminal_core.link(session.id, SessionLink(name="Twice"))
    other = projects_core.create(ProjectCreate(name="Other"))
    assert terminal_core.link(session.id, SessionLink(project_id=other.id))[0].project_id == other.id
    assert terminal_core._last_link(session.cli_session_id) == (other, None)  # kept when resumed
    assert terminal_core.link(session.id, SessionLink())[0].project_id is None
    with pytest.raises(ValueError):
        SessionStart(folder=str(folder), project_id=other.id)
    with pytest.raises(terminal_core.TerminalError, match="full path"):
        terminal_core.start(SessionStart(folder="pandora"))


def test_an_outside_session_can_be_stopped(ctx, open_outside):
    process, conversation, _ = open_outside
    found = next(s for s in transcript_core.outside_sessions(set()) if s["pid"] == process.pid)
    assert found["cli_session_id"] == str(conversation)
    with pytest.raises(terminal_core.TerminalError, match="no longer running"):  # a reused pid
        terminal_core.stop_outside(OutsideStop(pid=process.pid, started=found["started"] - 60))
    assert process.poll() is None
    terminal_core.stop_outside(OutsideStop(pid=process.pid, started=found["started"]))
    process.wait(5)


def test_usage_left_comes_from_the_status_line(ctx, tmp_path, monkeypatch):
    monkeypatch.setitem(ctx.config, "CAIRN_DATA_DIR", str(tmp_path))
    (tmp_path / "claude").mkdir()
    assert limits_core.limits() == {"at": None, "windows": []}
    later = time.time() + 3600
    given = {
        "rate_limits": {
            "five_hour": {"used_percentage": 23.5, "resets_at": later},
            "seven_day": {"used_percentage": 41, "resets_at": time.time() - 5},
        },
        "session_id": "private",
    }
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(json.dumps({"statusLine": {"command": "echo MINE; cat"}}))
    done = subprocess.run(  # noqa: S603
        [sys.executable, limits_core.statusline.__file__, str(limits_core.limits_file())],
        input=json.dumps(given).encode(),
        capture_output=True,
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
        check=True,
    )
    if shutil.which("bash"):
        assert b"MINE" in done.stdout and b"rate_limits" in done.stdout  # the owner's own still runs
    (only,) = limits_core.limits()["windows"]  # the other window was reset since
    assert (only["key"], only["used"], only["left"]) == ("five_hour", 24, 76)
    assert "private" not in limits_core.limits_file().read_text()


def test_free_pages_and_api(signed_in, tmp_path, fake_claude):
    made = signed_in.post("/api/claude/sessions", json={"folder": str(tmp_path)})
    assert made.status_code == 201 and made.json["session"]["project"] is None
    sid = made.json["session"]["id"]
    assert b"Free: link to a project" in signed_in.get(f"/claude/sessions/{sid}").data
    assert b"free, no project" in signed_in.get("/claude").data
    opened = signed_in.post("/claude/sessions", data={"folder": str(tmp_path)})
    assert opened.status_code == 302 and "/claude/sessions/" in opened.location
    linked = signed_in.post(f"/claude/sessions/{sid}/link", data={"name": "Fresh", "folder": str(tmp_path)})
    assert linked.status_code == 302
    sessions = {s["id"]: s for s in signed_in.get("/api/claude/sessions").json["sessions"]}
    assert sessions[sid]["project"]["name"] == "Fresh"
    gone = signed_in.post(f"/api/claude/sessions/{sid}/link", json={"project_id": str(uuid.uuid4())})
    assert gone.status_code == 409
    assert signed_in.post("/api/claude/outside/stop", json={"pid": 2, "started": 0}).status_code == 409


def test_library_skills_reach_the_sessions(ctx, tmp_path, fake_claude, monkeypatch):
    source = tmp_path / "review"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: review\ndescription: Reviews\n---\nLook closely.")
    (source / "notes.md").write_text("more")
    (tmp_path / "secret").write_text("no")
    if sys.platform != "win32":
        (source / "link").symlink_to(tmp_path / "secret")
    mine = projects_core.create(ProjectCreate(name="Mine", local_path=str(tmp_path)))
    other = projects_core.create(ProjectCreate(name="Other"))
    create = resources_core.create
    everywhere = create(ResourceCreate(kind="skill", title="Review: code", path=str(source)))
    ours = create(
        ResourceCreate(kind="skill", title="House style", body="Be brief.", description_md="How: we write"),
        LinkCreate(target_type="project", target_id=mine.id),
    )
    create(
        ResourceCreate(kind="skill", title="Theirs", body="x"),
        LinkCreate(target_type="project", target_id=other.id),
    )
    assert skills_core.for_session(mine, None) == [ours, everywhere]
    assert skills_core.for_session(None, None) == [everywhere]
    with pytest.raises(resources_core.ResourceError, match=r"no SKILL\.md"):
        create(ResourceCreate(kind="skill", title="Bad", path=str(tmp_path)))
    with pytest.raises(ValueError, match="folder, or write"):
        ResourceCreate(kind="skill", title="Empty")

    given = []
    fake = terminal_core.command
    monkeypatch.setattr(
        terminal_core, "command", lambda *a, **k: (given.append(k["skills"]), fake(*a, **k))[1]
    )
    session = terminal_core.start(SessionStart(project_id=mine.id))
    (plugin,) = given
    assert json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())["name"] == "cairn-skills"
    assert {p.name for p in (plugin / "skills" / "review-code").iterdir()} == {"SKILL.md", "notes.md"}
    written = (plugin / "skills" / "house-style" / "SKILL.md").read_text()
    assert (
        written.startswith('---\nname: house-style\ndescription: "How: we write"\n---')
        and "Be brief." in written
    )
    terminal_core.close_all()
    assert not plugin.exists() and source.is_dir() and not terminal_core.is_running(session.id)
    (source / "SKILL.md").unlink()  # gone since: the session opens without it
    assert not (
        skills_core.write_plugin(tmp_path / "again", [everywhere]) / "skills" / "review-code"
    ).exists()


def test_context_window_is_the_one_claude_code_reports(ctx, tmp_path, monkeypatch):
    monkeypatch.setitem(ctx.config, "CAIRN_DATA_DIR", str(tmp_path))
    (tmp_path / "claude").mkdir()
    assert transcript_core._window("claude-opus-5-5", 1000) == 200_000
    statusline = limits_core.statusline
    size = {"model": {"id": "claude-opus-5-5[1m]"}, "context_window": {"context_window_size": 1_000_000}}
    statusline.keep({**size, "rate_limits": {"five_hour": {"used_percentage": 5}}}, limits_core.limits_file())
    statusline.keep(size, limits_core.limits_file())  # no usage yet in a new session: the last one stays
    assert transcript_core._window("claude-opus-5-5", 1000) == 1_000_000
    assert limits_core.limits()["windows"][0]["used"] == 5
    old = {"rate_limits": {"five_hour": {"used_percentage": 3}}}  # an idle session, with older numbers
    statusline.keep(old, limits_core.limits_file())
    assert limits_core.limits()["windows"][0]["used"] == 5


def test_main_claude_opens_once_and_takes_up_its_conversation(ctx, tmp_path, fake_claude, monkeypatch):
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path / "transcripts")
    first = main_core.open_main()
    assert main_core.is_main(first) and first.project_id is None
    assert main_core.open_main().id == first.id  # already open
    _wait_for(first.id, "ARGS")
    kept = transcript_core.transcript_path(first.cwd, str(first.cli_session_id))
    conversation = first.cli_session_id
    terminal_core.close_all()
    kept.parent.mkdir(parents=True)
    kept.write_text("{}", encoding="utf-8")
    again = main_core.open_main()
    assert again.cli_session_id == conversation
    assert "--resume" in _wait_for(again.id, "ARGS")[0]
    assert "main Claude" in main_core.rules(again.cwd) and "take_note" in main_core.rules("/elsewhere")


def test_main_claude_opens_only_with_the_web_server(app, monkeypatch):
    started = []

    def _thread(**options):
        if options["name"] == "claude-main":
            started.append(options)
        return _NoThread()

    monkeypatch.setattr(main_core.threading, "Thread", _thread)
    for web, reload, serving, expected in (
        (None, None, None, 0),  # worker, MCP server, migrations
        ("1", "1", None, 0),  # the auto-reload watcher
        ("1", "1", "true", 1),
        ("1", None, None, 2),
    ):
        for name, value in (("CAIRN_WEB", web), ("CAIRN_RELOAD", reload), ("WERKZEUG_RUN_MAIN", serving)):
            monkeypatch.setenv(name, value) if value else monkeypatch.delenv(name, raising=False)
        main_core.open_with_cairn(app)
        assert len(started) == expected


class _NoThread:
    def start(self):
        pass


def test_main_claude_page(signed_in, fake_claude):
    assert b"Open Cairn" in signed_in.get("/claude").data
    assert "/claude/sessions/" in signed_in.post("/claude/main").location
    page = signed_in.get("/claude").data
    assert b"every project" in page and b"Open Cairn" not in page


def test_dock_on_every_page(signed_in, fake_claude):
    page = signed_in.get("/tasks").data
    assert b"<cn-claude-dock" in page and b"cn-dock-open" in page  # opens with Cairn by default
    signed_in.set_cookie("cn_dock", "closed")
    assert b'class="cn-dock-open"' not in signed_in.get("/tasks").data
    assert signed_in.get("/api/claude/main").json["session"] is None
    first = signed_in.post("/api/claude/main").json["session"]["id"]
    panel = signed_in.get(f"/claude/sessions/{first}/panel")
    csp = panel.headers["Content-Security-Policy"]
    assert "frame-ancestors 'self'" in csp and panel.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "script-src 'self'" in csp and b"<cn-terminal" in panel.data
    full = signed_in.get(f"/claude/sessions/{first}")
    assert b"<cn-claude-dock" not in full.data  # its terminal is the page
    assert "frame-ancestors 'none'" in full.headers["Content-Security-Policy"]
    again = signed_in.post("/api/claude/main/restart").json["session"]["id"]
    assert again != first
    assert signed_in.post("/api/claude/main/stop").json["session"] is None
    deadline = time.monotonic() + 10
    while signed_in.get("/api/claude/main").json["session"] and time.monotonic() < deadline:
        time.sleep(0.1)
    assert signed_in.get("/api/claude/main").json["session"] is None


def test_claude_knows_the_page_in_front(app, signed_in):
    with app.app_context():
        assert main_core.current_page() == {"page": None}
    project = signed_in.post("/api/projects", json={"name": "Pandora"}).json["project"]
    task = signed_in.post("/api/tasks", json={"title": "Read it", "project_id": project["id"]}).json["task"]
    for path, key, name in (
        (f"/projects/{project['slug']}?tab=plan", "project", "Pandora"),
        (f"/tasks/{task['id']}", "task", "Read it"),
    ):
        sent = signed_in.post("/api/claude/page", json={"path": path, "title": "x"})
        assert sent.status_code == 200
        with app.app_context():
            found = main_core.current_page()
        assert found["page"] == path and name in found[key].values()
    for bad in ("https://evil.example", "//evil.example", ""):
        assert signed_in.post("/api/claude/page", json={"path": bad}).status_code == 422


def test_main_claude_may_work_on_cairn(ctx, tmp_path):
    assert str(main_core.code_folder()) in main_core.rules(str(main_core.folder()))
    argv = terminal_core.command("claude", uuid.uuid4(), None, add_dir=tmp_path, mcp=tmp_path / "m")
    assert argv[argv.index("--add-dir") + 1] == str(tmp_path) and argv[-2] == "--allowedTools"


def test_nothing_of_cairn_reaches_what_it_starts(ctx, monkeypatch):
    for key in ("CAIRN_SECRET_KEY", "CAIRN_MASTER_KEY", "CAIRN_DATABASE_URL", "CAIRN_WEB", "cairn_lower"):
        monkeypatch.setenv(key, "x")
    assert not [key for key in terminal_core._environment() if key.upper().startswith("CAIRN_")]


def test_writing_in_cairn_follows_the_mode_and_private_files_are_refused(ctx, tmp_path):
    from app.features.claude import mcp_server, session_settings

    code = main_core.code_folder().as_posix().lstrip("/")
    plain = session_settings.permissions(str(tmp_path))
    main = session_settings.permissions(str(main_core.folder()))
    assert f"Read(//{code}/.env)" in plain["deny"] and plain["deny"] == main["deny"]
    assert not [rule for rule in plain["ask"] + main["ask"] if rule.startswith("mcp__cairn__")]  # D-101
    assert f"Edit(//{code}/**)" in main["ask"] and "Bash(git push *)" in main["ask"]
    assert f"Edit(//{code}/**)" not in plain["ask"]
    assert not set(mcp_server.READ_TOOLS) & set(mcp_server.WRITE_TOOLS)
    assert plain["allow"] == []


def test_the_owner_can_let_cairn_writes_through(ctx, tmp_path):
    from app.core.utils.settings import set_setting
    from app.features.claude import session_settings

    set_setting("claude.cairn_writes_allowed", True)
    allowed = session_settings.permissions(str(tmp_path))["allow"]
    assert "mcp__cairn__create_task" in allowed and "mcp__cairn__list_tasks" not in allowed
    main = session_settings.permissions(str(main_core.folder()))
    assert "Bash(git push *)" in main["ask"]  # still asked


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_data_folder_is_private(tmp_path):
    from app import keep_private

    folder = tmp_path / "data"
    folder.mkdir(mode=0o755)
    keep_private(folder)
    assert folder.stat().st_mode & 0o077 == 0
