"""Reading a Claude Code that runs outside Cairn (D-075)."""

import json
import subprocess
import sys
import time

import psutil
import pytest

from app.core.schema.claude import OutsideStop
from app.features.claude import conversation_view, terminal_core, transcript_core
from tests.test_claude import open_outside  # noqa: F401 (a fixture)


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _used(name, **data):
    block = {"type": "tool_use", "id": "a", "name": name, "input": data}
    return {"type": "assistant", "message": {"content": [block]}}


def _answer(text, error=False):
    block = {"type": "tool_result", "tool_use_id": "a", "content": text, "is_error": error}
    return {"type": "user", "message": {"content": [block]}}


def _text(entry):
    return conversation_view.clean("\n".join(conversation_view.render(entry)))


def test_it_reads_like_claude_code():
    assert "❯ Fix it" in _text({"type": "user", "message": {"content": "Fix it"}})
    assert "● Done." in _text(_said("Done."))
    assert "Bash(ls -l)" in _text(_used("Bash", command="ls -l", description="List"))
    edit = _text(_used("Edit", file_path="/a.py", old_string="x = 1", new_string="x = 2"))
    assert "Edit(/a.py)" in edit and "- x = 1" in edit and "+ x = 2" in edit
    long = _text(_answer("\n".join(f"line {n}" for n in range(50))))
    assert "⎿ line 0" in long and "line 9" in long and "line 10" not in long and "+40 lines" in long
    for hidden in (
        {"type": "user", "message": {"content": "<task-notification>x"}},
        {"type": "user", "isMeta": True, "message": {"content": "x"}},
        {**_said("x"), "isSidechain": True},
        {"type": "ai-title", "aiTitle": "x"},
        {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "x"}]}},
        ["not", "a", "dict"],
    ):
        assert conversation_view.render(hidden) == []


def test_a_conversation_never_drives_the_terminal():
    bad = "a\x1b]0;title\x07b\x1b[2Jc\x1b]52;c;ZXZpbA==\x1b\\d\x9b31me\rf\x08g\u202eh"
    for entry in (_said(bad), _answer(bad), _used("Bash", command=bad), _used(bad, description=bad)):
        ours = "\n".join(conversation_view.render(entry))
        for code in (
            conversation_view.RESET,
            conversation_view.BOLD,
            conversation_view.DIM,
            conversation_view.GREEN,
            conversation_view.ORANGE,
        ):
            ours = ours.replace(code, "")
        assert not [c for c in ours if (ord(c) < 32 and c != "\n") or 127 <= ord(c) < 160 or c == "\u202e"]


def test_it_follows_in_a_terminal(ctx, open_outside):  # noqa: F811
    process, conversation, folder = open_outside
    path = transcript_core.transcript_path(str(folder), str(conversation))
    path.write_text(json.dumps(_said("Hello there")) + "\n", encoding="utf-8")
    wanted = OutsideStop(pid=process.pid, started=psutil.Process(process.pid).create_time())
    with pytest.raises(terminal_core.TerminalError, match="no longer running"):
        terminal_core.view_outside(wanted.model_copy(update={"started": wanted.started - 60}))
    session = terminal_core.view_outside(wanted)
    assert session.kind == "log" and terminal_core.view_outside(wanted).id == session.id

    def seen():
        return "".join(text for _, text in terminal_core.output(session.id, 0)[0])

    def until(text):
        deadline = time.monotonic() + 15
        while text not in seen() and time.monotonic() < deadline:
            time.sleep(0.1)
        return text in seen()

    assert until("Hello there") and "Read-only" in seen()
    whole = json.dumps(_said("Said later")) + "\n"
    with path.open("a", encoding="utf-8") as log:
        log.write(whole[:20])  # a line being written
        log.flush()
        time.sleep(0.8)
        log.write(whole[20:])
    assert until("Said later")
    terminal_core.write(session.id, "x\r")  # goes nowhere
    terminal_core.stop(session.id)
    assert process.poll() is None  # the Claude itself is not touched


def test_the_button_and_the_api(signed_in, open_outside):  # noqa: F811
    process, _conversation, _ = open_outside
    page = signed_in.get("/claude").data.decode()
    assert "/claude/outside/view" in page and "Move to Cairn" in page
    started = psutil.Process(process.pid).create_time()
    opened = signed_in.post("/claude/outside/view", data={"pid": process.pid, "started": started})
    assert "/claude/sessions/" in opened.location
    assert b"Only the view is closed" in signed_in.get(opened.location).data
    again = signed_in.post("/api/claude/outside/view", json={"pid": process.pid, "started": started})
    assert again.status_code == 201 and again.json["session"]["id"] in opened.location
    assert signed_in.post("/api/claude/outside/view", json={"pid": 2, "started": 0}).status_code == 409


def test_the_script_runs_alone(tmp_path):
    path = tmp_path / "a.jsonl"
    path.write_text("not json\n" + json.dumps(_said("Alone é")) + "\n", encoding="utf-8")
    running = subprocess.Popen(  # noqa: S603
        [sys.executable, conversation_view.__file__, str(path)], stdout=subprocess.PIPE
    )
    try:
        time.sleep(1.5)
        running.terminate()
        assert "Alone é" in running.stdout.read().decode("utf-8")
    finally:
        running.kill()
        running.wait()
        running.stdout.close()


def test_a_background_conversation_is_read_only(ctx, open_outside, monkeypatch):  # noqa: F811
    process, conversation, folder = open_outside
    path = transcript_core.registry_root() / f"{process.pid}.json"
    entry = json.loads(path.read_text(encoding="utf-8"))
    monkeypatch.setattr(transcript_core, "CLAUDE_NAMES", set())  # named after its version
    path.write_text(json.dumps({**entry, "kind": "bg", "status": "busy"}), encoding="utf-8")
    (found,) = [s for s in transcript_core.outside_sessions(set()) if s["pid"] == process.pid]
    assert found["background"] and found["cli_session_id"] == str(conversation)
    wanted = OutsideStop(pid=process.pid, started=found["started"])
    with pytest.raises(terminal_core.TerminalError, match="background"):
        terminal_core.stop_outside(wanted)
    from app.core.schema.claude import ResumeStart

    with pytest.raises(terminal_core.TerminalError, match="background"):
        terminal_core.resume(ResumeStart(cli_session_id=conversation, cwd=str(folder), take_over=True))
    assert terminal_core.view_outside(wanted).kind == "log"
    assert transcript_core.holds_background(psutil.Process().pid)  # these tests started it
    with pytest.raises(terminal_core.TerminalError, match="depends on this"):
        monkeypatch.setattr(transcript_core, "own_ancestors", set)
        terminal_core._close_outside([psutil.Process().pid], None, "stop_outside")
    path.write_text(json.dumps({**entry, "kind": "bg", "status": "idle"}), encoding="utf-8")
    assert not transcript_core.holds_background(psutil.Process().pid)
    assert process.poll() is None
