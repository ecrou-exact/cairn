"""The live graph of the Claude sessions (D-059): facts from transcripts, agents, processes."""

import json
import os
import subprocess
import sys
import time
import uuid

import pytest

from app.features.claude import live_core, transcript_core

AT = "2026-11-23T10:00:0{}Z"


def _use(call_id, name, n=1, **data):
    block = {"type": "tool_use", "id": call_id, "name": name, "input": data}
    return {"type": "assistant", "timestamp": AT.format(n), "message": {"content": [block]}}


def _result(call_id, error=False, **result):
    block = {"type": "tool_result", "tool_use_id": call_id, "content": "x", "is_error": error}
    entry = {"type": "user", "timestamp": AT.format(2), "message": {"content": [block]}}
    return {**entry, "toolUseResult": result} if result else entry


def _ask(text, kind="human"):
    return {"type": "user", "timestamp": AT.format(0), "origin": {"kind": kind}, "message": {"content": text}}


def _ended(task_id):
    text = f"<task-notification><task-id>{task_id}</task-id><status>completed</status></task-notification>"
    return {"type": "queue-operation", "content": text}


def _read(entries, **options):
    return live_core.read_conversation([json.dumps(e) for e in entries] + ["cut {"], "/repo", **options)


def test_only_what_followed_the_last_request_is_shown():
    talk = _read(
        [
            _ask("First"),
            _use("a", "Read", file_path="/repo/old.py"),
            _ask("Fix it"),
            _ask("<task-notification>x", kind="task-notification"),
            _use("b", "Edit", file_path="/repo/new.py"),
            _result("b", error=True),
            _use("c", "Bash", command="sleep 9", description="Wait"),
            {**_use("z", "Bash", command="x"), "isSidechain": True},
        ]
    )
    assert talk.prompt == "Fix it"
    assert [(c.label, c.done, c.failed) for c in talk.calls] == [
        ("Editing new.py", True, True),
        ("Wait", False, False),  # no result yet: running now
    ]


def test_background_tasks_last_until_their_end():
    started = [
        _use("a", "Bash", description="Server"),
        _result("a", backgroundTaskId="t1"),
        _use("b", "Bash", description="Build"),
        _result("b", backgroundTaskId="t2"),
    ]
    assert set(_read(started).background) == {"t1", "t2"}
    assert [c.label for c in _read([*started, _ended("t2")]).background.values()] == ["Server"]


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """One session on a fake machine: a live process of its own, a transcript and agents."""
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path / "projects")
    cwd, conversation = str(tmp_path / "pandora"), str(uuid.uuid4())
    transcript = transcript_core.transcript_path(cwd, conversation)
    agents = transcript.with_suffix("") / "subagents"
    agents.mkdir(parents=True)
    entries = [
        _ask("Look around"),
        _use("s", "Skill", skill="review"),
        _result("s"),
        _use("ag", "Agent", description="Scout"),
        _use("e", "Edit", file_path=cwd + "/a.py"),
        _result("e"),
        _use("m", "mcp__cairn__list_tasks"),
        _result("m"),
        _use("r", "Bash", description="Run the tests"),
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    def agent(name, meta, entries, age=0.0):
        (agents / f"agent-{name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        path = agents / f"agent-{name}.jsonl"
        path.write_text("\n".join(json.dumps({**e, "isSidechain": True}) for e in entries), encoding="utf-8")
        os.utime(path, (time.time() - age, time.time() - age))

    agent(
        "one",
        {"agentType": "Explore", "description": "Scout", "toolUseId": "ag"},
        [_use("g", "Grep", pattern="x"), _use("sub", "Agent", description="Deeper")],
    )
    agent("two", {"agentType": "Plan", "description": "Deeper", "toolUseId": "sub"}, [])
    agent("cut", {"agentType": "Plan", "description": "Cut long ago"}, [], age=3600)
    session = {
        "key": "k",
        "pid": None,
        "cwd": cwd,
        "conversation": conversation,
        "title": "Pandora",
        "where": "in Cairn",
        "project": None,
        "usage": transcript_core.Usage(last_activity=time.time(), model="claude-opus-5-5").as_dict(),
        "started": time.time() - 7200,
        "open": "/claude/sessions/x",
        "task": None,
    }
    monkeypatch.setattr(live_core, "_running", lambda: [session])
    return session


def test_overview_shows_what_is_alive(ctx, machine):
    found = live_core.graph()
    cards = {n["id"]: n["data"] for n in found["nodes"]}
    kinds = sorted(d["kind"] for d in cards.values())
    assert kinds == ["agent", "agent", "running", "running", "session", "skill"]
    assert cards["k"]["prompt"] == "Look around" and cards["k"]["state"] == "working"
    assert cards["k/a/agent-one"]["parent"] == "k"
    assert cards["k/a/agent-two"]["parent"] == "k/a/agent-one"  # started by the first agent
    assert "k/a/agent-cut" not in cards  # an agent silent for an hour is not at work
    assert cards["k/t/r"]["label"] == "Run the tests" and cards["k/t/r"]["live"]
    assert {e["from"] for e in found["edges"]} <= set(cards) and len(found["edges"]) == len(cards) - 1
    places = {(n["fx"], n["fy"]) for n in found["nodes"]}
    assert len(places) == len(cards)  # no card on another


def test_a_session_in_full(ctx, machine):
    cards = {n["id"]: n["data"] for n in live_core.graph("k")["nodes"]}
    assert cards["k/file/" + machine["cwd"] + "/a.py"]["label"] == "a.py"
    assert cards["k/server/cairn"]["state"] == "1×"
    assert cards["k"]["drill"] is None
    assert live_core.graph("other")["nodes"] == []


def test_a_waiting_session_has_nothing_running(ctx, machine, monkeypatch):
    monkeypatch.setattr(transcript_core, "registered_status", lambda pid: "idle")
    cards = [n["data"] for n in live_core.graph()["nodes"]]
    assert next(d for d in cards if d["kind"] == "session")["state"] == "waiting"
    assert "Run the tests" not in {d["label"] for d in cards}  # cut short, not running


def test_processes_show_what_runs_and_hide_options(monkeypatch):
    monkeypatch.setattr(live_core, "SETTLED", -1.0)
    code = "import time; time.sleep(60)"
    child = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", code, "serve", "--token=secret", "KEY=secret"]
    )
    try:
        found = next(p for p in live_core._processes(os.getpid()) if p["pid"] == child.pid)
        assert "serve" in found["label"] and "secret" not in found["label"]
    finally:
        child.kill()
        child.wait()


def test_page_and_api(signed_in, machine):
    page = signed_in.get("/claude/live")
    assert page.status_code == 200 and b"data-live-graph" in page.data
    assert "style-src-attr" in page.headers["Content-Security-Policy"]
    data = signed_in.get("/api/claude/live?session=k").json
    assert data["sessions"] == 1 and data["nodes"]
    assert b"Live graph" in signed_in.get("/claude").data


def test_tasks_claude_is_on(app, ctx, tmp_path, monkeypatch):
    from app.core.db_class.claude import ClaudeSession
    from app.core.extensions import db
    from app.core.schema.planning import ProjectCreate, TaskCreate
    from app.features.claude import terminal_core
    from app.features.projects import projects_core
    from app.features.tasks import tasks_core

    project = projects_core.create(ProjectCreate(name="P", local_path=str(tmp_path)))
    case = tasks_core.create(TaskCreate(title="Case", project_id=project.id))
    inside = tasks_core.create(TaskCreate(title="Inside", project_id=project.id, parent_id=case.id))
    row = ClaudeSession(
        kind="claude", cwd=str(tmp_path), cli_session_id=uuid.uuid4(), project_id=project.id, pid=None
    )
    db.session.add(row)
    db.session.commit()
    monkeypatch.setattr(terminal_core, "is_running", lambda session_id: True)
    assert live_core.at_work() == []  # on no task yet
    from app.features.claude import mcp_server
    from tests.test_claude_mcp import _call

    server = mcp_server.build(app, str(row.id))
    assert not _call(server, "set_task_status", {"task_id": str(inside.id), "status": "in_progress"}).is_error
    db.session.expire_all()
    (one,) = live_core.at_work()
    assert (one["task"], one["holders"], one["state"]) == (str(inside.id), [str(case.id)], "waiting")
    other = tasks_core.create(TaskCreate(title="Elsewhere"))
    _call(server, "set_task_status", {"task_id": str(other.id), "status": "in_progress"})
    db.session.expire_all()
    assert live_core.at_work()[0]["task"] == str(inside.id)  # another project's task does not move it
    inside_id = inside.id
    tasks_core.delete(inside_id)
    assert live_core.at_work() == []
