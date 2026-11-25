"""Cairn from any Claude Code (D-080): the project of a folder, starting one, the connection."""

import json
import subprocess
import uuid

import pytest

from app.core.db_class.activity import Activity
from app.core.db_class.claude import ClaudeSession
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate
from app.features.claude import caller_core, connect_core, mcp_server, transcript_core
from app.features.folder import programs
from app.features.projects import place_core, projects_core
from app.features.recap import facts_core
from tests.test_claude_mcp import _call, _data
from tests.test_instances_found import _repo

URL = "git@github.com:Flow/intel.git"


@pytest.fixture(autouse=True)
def alone(monkeypatch):
    monkeypatch.setattr(facts_core, "repositories", list)  # never the machine's own
    monkeypatch.setattr(programs, "gh", lambda *a, **k: None)


@pytest.fixture()
def runs(monkeypatch):
    monkeypatch.setattr(caller_core, "cairn_runs", lambda: True)


def _worktree(main, folder):
    own = main / ".git" / "worktrees" / folder.name
    own.mkdir(parents=True)
    (own / "commondir").write_text("../..\n")
    (own / "HEAD").write_text("ref: refs/heads/fix\n")
    folder.mkdir()
    (folder / ".git").write_text(f"gitdir: {own}\n")
    return folder


def test_the_project_of_a_folder(ctx, tmp_path):
    main = _repo(tmp_path / "intel", URL)
    (main / "src").mkdir()
    inner = main / "modules" / "inner"
    inner.mkdir(parents=True)
    clone = _repo(tmp_path / "intel-2", "https://github.com/flow/Intel")
    loose = _repo(tmp_path / "loose", "https://example.org/flow/other.git")
    project = projects_core.create(ProjectCreate(name="Intel", local_path=str(main)))
    nested = projects_core.create(ProjectCreate(name="Inner", local_path=str(inner)))
    for folder in (main, main / "src", _worktree(main, tmp_path / "wt"), clone):
        assert place_core.project_for(str(folder)) is project
    assert place_core.project_for(str(inner)) is nested
    for folder in (loose, tmp_path):
        assert place_core.project_for(str(folder)) is None
    projects_core.create(ProjectCreate(name="Same", local_path=str(tmp_path / "x"), github_repo="Flow/intel"))
    projects_core.create(
        ProjectCreate(name="Again", local_path=str(tmp_path / "y"), github_repo="Flow/intel")
    )
    assert place_core.project_for(str(clone)) is None  # two could be: it does not guess


def test_start_a_project_once(app, tmp_path, runs):
    folder = _repo(tmp_path / "intel", URL)
    (folder / "src").mkdir()
    actor = f"claude:{uuid.uuid4()}"
    server = mcp_server.build(app, None, actor=actor, folder=str(folder / "src"))
    before = _data(_call(server, "this_project"))
    would = {"name": "intel", "github_repo": "Flow/intel", "folder": str(folder)}
    assert before["project"] is None and before["would_make"] == would
    made = _data(_call(server, "start_project", {"description": "Cases", "default_branch": "main"}))
    assert made["created"] and made["project"]["folder"] == str(folder)
    assert made["project"]["github_repo"] == "Flow/intel" and made["project"]["url"].endswith(
        "/projects/intel"
    )
    assert _data(_call(server, "start_project", {"name": "Other"}))["created"] is False
    assert _data(_call(server, "cairn_overview"))["this_session_project"] == "intel"
    task = _data(_call(server, "create_task", {"title": "Read the cases"}))
    assert task["project"] == "intel"
    assert [t["title"] for t in _data(_call(server, "this_project"))["project"]["next"]] == ["Read the cases"]
    with app.app_context():
        assert len(projects_core.options()) == 1
        rows = db.session.scalars(db.select(Activity).where(Activity.action == "project.create"))
        assert {row.actor for row in rows} == {actor}
    assert sorted(p.name for p in folder.iterdir()) == [".git", "src"]  # nothing written there


def test_nothing_is_started_without_cairn_or_in_the_home(app, tmp_path, monkeypatch):
    monkeypatch.setattr(caller_core, "cairn_runs", lambda: False)
    server = mcp_server.build(app, None, folder=str(tmp_path))
    assert _data(_call(server, "this_project"))["cairn_running"] is False
    refused = _call(server, "start_project")
    assert refused.is_error and "not running" in refused.content[0].text
    monkeypatch.setattr(caller_core, "cairn_runs", lambda: True)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    assert _call(server, "start_project").is_error
    assert _call(server, "this_project", {"folder": "nope"}).is_error


def test_the_caller_is_found(ctx, monkeypatch, tmp_path):
    conversation = str(uuid.uuid4())

    class Claude:
        def name(self):
            return "claude"

        def cwd(self):
            return str(tmp_path)

    monkeypatch.setattr(
        caller_core.psutil, "Process", lambda: type("P", (), {"parents": lambda s: [Claude()]})()
    )
    monkeypatch.setattr(transcript_core, "registered", lambda process: conversation)
    monkeypatch.setattr(transcript_core, "is_claude", lambda process, name: True)
    caller = caller_core.identify(None)
    assert caller == caller_core.Caller(None, f"claude:{conversation}", str(tmp_path))
    row = ClaudeSession(cwd=str(tmp_path), cli_session_id=uuid.UUID(conversation), kind="claude")
    db.session.add(row)
    db.session.commit()
    assert caller_core.identify(None).session_id == str(row.id)  # one Cairn opened is known as such
    assert caller_core.identify("given").session_id == "given"


@pytest.fixture()
def claude_home(tmp_path, monkeypatch):
    home, held = tmp_path / "claude", {}
    home.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home))

    def mcp(*args):
        out, code = "", 0
        if args[0] == "get":
            out, code = held.get("cairn", ""), 0 if "cairn" in held else 1
        elif args[0] == "add":
            held["cairn"] = " ".join(args)
        else:
            held.pop("cairn", None)
        return subprocess.CompletedProcess(args, code, out, "")

    monkeypatch.setattr(connect_core, "_mcp", mcp)
    return home, held


def test_connecting_changes_only_what_is_cairns(claude_home):
    home, held = claude_home
    mine = {"model": "opus", "permissions": {"ask": ["Bash(git push *)"], "allow": ["Read"]}}
    left = ["Bash(git push *)", "mcp__cairn__start_project"]
    old = {**mine, "permissions": {**mine["permissions"], "ask": left}}
    (home / "settings.json").write_text(json.dumps(old))  # as an earlier version left it
    assert "claude mcp add --scope user cairn" in connect_core.show() and not held
    connect_core.on()
    connect_core.on()  # again, after an update
    assert connect_core.status() == {"server": True, "skill": True, "hook": True}
    data = json.loads((home / "settings.json").read_text())
    assert data["model"] == "opus" and data["permissions"]["ask"] == ["Bash(git push *)"]  # D-101
    (hook,) = data["hooks"]["SessionStart"]
    assert "claude-hook" in hook["hooks"][0]["command"]
    assert len(list(home.glob("settings.json.cairn-*.bak"))) == 1
    connect_core.off()
    assert json.loads((home / "settings.json").read_text()) == mine
    assert not held and not (home / "skills" / "cairn").exists()


def test_nothing_changes_when_something_is_in_the_way(claude_home):
    home, held = claude_home
    skill = home / "skills" / "cairn" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("mine")
    with pytest.raises(connect_core.ConnectError):
        connect_core.on()
    skill.unlink()
    (home / "settings.json").write_text("{ broken")
    with pytest.raises(connect_core.ConnectError):
        connect_core.on()
    (home / "settings.json").unlink()
    held["cairn"] = "someone else's"
    with pytest.raises(connect_core.ConnectError):
        connect_core.on()
    assert held["cairn"] == "someone else's" and not (home / "settings.json").exists()


def test_a_projects_tab_shows_its_claude_codes_from_any_copy(app, signed_in, tmp_path, monkeypatch):
    main = _repo(tmp_path / "intel", URL)
    clone = _repo(tmp_path / "intel-fix", "https://github.com/flow/intel")
    other = _repo(tmp_path / "else", "https://github.com/x/else")
    with app.app_context():
        projects_core.create(ProjectCreate(name="Intel", local_path=str(main)))
    usage = transcript_core.Usage(title="Fixing the tree").as_dict()
    running = [
        {"pid": n, "cwd": str(f), "usage": usage, "host": "a terminal", "cli_session_id": None}
        for n, f in ((11, clone), (12, other))
    ]
    monkeypatch.setattr(transcript_core, "outside_sessions", lambda known: [dict(r) for r in running])
    page = signed_in.get("/projects/intel?tab=claude").data.decode()
    assert "In your terminals" in page and "pid 11" in page and "pid 12" not in page
    assert "pid 12" in signed_in.get("/claude").data.decode()


def test_the_session_start_hook(app, tmp_path):
    import json

    folder = _repo(tmp_path / "intel", URL)
    with app.app_context():
        projects_core.create(ProjectCreate(name="Intel", local_path=str(folder)))
    monkeypatch_app = app

    def made(*_a, **_k):
        return monkeypatch_app

    import app as package

    original = package.create_app
    package.create_app = made
    try:
        told = connect_core.session_context(json.dumps({"cwd": str(folder)}))
        assert "Intel" in told and "tick_checklist" in told
        assert connect_core.session_context(json.dumps({"cwd": str(tmp_path)})) == ""
    finally:
        package.create_app = original
