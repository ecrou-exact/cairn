"""Instances that outlive Cairn (D-070)."""

import os
import stat
import sys
import time

import psutil
import pytest

from app.core.extensions import db
from app.core.schema.instances import InstanceCreate
from app.core.schema.planning import ProjectCreate
from app.features.claude import claude_core, terminal_core
from app.features.instances import instances_core, runner, survivor
from app.features.projects import projects_core

pytestmark = pytest.mark.skipif(os.name != "posix", reason="instances stay in Cairn's process on Windows")

PROGRAM = """
import os, sys
print("SECRET", os.environ.get("CAIRN_SECRET_KEY"), "PORT", os.environ.get("PORT"), flush=True)
for line in sys.stdin:
    print("GOT", line.strip(), os.get_terminal_size().columns, flush=True)
    if line.strip() == "bye":
        sys.exit(3)
"""


@pytest.fixture
def instance(ctx, tmp_path, monkeypatch):
    monkeypatch.setenv("CAIRN_SECRET_KEY", "never")
    (tmp_path / "program.py").write_text(PROGRAM)
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(tmp_path)))
    return instances_core.create(
        InstanceCreate(project_id=project.id, name="Program", command=f'"{sys.executable}" program.py')
    )


def _until(check, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.1)
    return check()


def _seen(session_id):
    return "".join(text for _, text in terminal_core.output(session_id, 0)[0])


def _restart_cairn(session_id):
    """What a restart does: the terminals are left, then found again."""
    terminal_core.close_all()
    assert not terminal_core.is_running(session_id)
    db.session.expire_all()
    assert terminal_core.get(session_id).status == "running"
    return instances_core.reattach()


def test_it_goes_on_and_is_found_again(instance):
    session = instances_core.start(instance.id)
    sid, pid = session.id, session.pid
    assert _until(lambda: "SECRET None" in _seen(sid))  # nothing of Cairn's environment
    assert _restart_cairn(sid) == 1
    assert psutil.pid_exists(pid) and instances_core.running(instance.id).id == sid
    assert _until(lambda: "SECRET None" in _seen(sid))  # what it printed before is there
    terminal_core.resize(sid, 91, 30)
    terminal_core.write(sid, "hello\r")
    assert _until(lambda: "GOT hello 91" in _seen(sid))  # keys and size still reach it
    instances_core.stop(instance.id)
    assert _until(lambda: not terminal_core.is_running(sid)) and not psutil.pid_exists(pid)
    db.session.expire_all()
    assert terminal_core.get(sid).status == "ended"
    assert "GOT hello" in claude_core.ended_log(terminal_core.get(sid))


def test_one_that_ended_meanwhile_is_closed_with_its_code(instance):
    session = instances_core.start(instance.id)
    sid, pid = session.id, session.pid
    found = survivor.find(sid)
    terminal_core.close_all()
    found.write("bye\r")
    assert _until(lambda: not psutil.pid_exists(pid) or survivor.ended_code(sid) == 3)
    assert instances_core.reattach() == 0
    db.session.expire_all()
    row = terminal_core.get(sid)
    assert (row.status, row.exit_code) == ("ended", 3) and "while Cairn was closed" in row.end_reason


def test_another_process_is_not_taken_for_it(instance):
    session = instances_core.start(instance.id)
    state = survivor.folder() / f"{session.id}.json"
    terminal_core.close_all()
    survivor.find(session.id).kill()
    runner.write_state(state, pid=os.getpid(), ended=False)  # its pid, reused by these tests
    assert survivor.find(session.id) is None
    survivor.Survivor(session.id, state, state, state, os.getpid()).kill()  # and never stopped for it
    assert instances_core.reattach() == 0


def test_files_are_private_and_the_environment_is_not_left(instance):
    session = instances_core.start(instance.id)
    names = {path.name for path in survivor.folder().iterdir()}
    assert not [name for name in names if "spec" in name]
    assert stat.S_IMODE(survivor.log_path(session.id).stat().st_mode) == 0o600
    sock = survivor._socket_path(session.id)
    assert stat.S_IMODE(sock.stat().st_mode) == 0o600 and len(str(sock)) < 100
    assert not [arg for arg in psutil.Process(session.pid).cmdline() if "never" in arg]


def test_a_program_that_cannot_start(ctx, tmp_path, instance, monkeypatch):
    monkeypatch.setattr(instances_core, "argv_for", lambda command, path=None: [str(tmp_path / "nope")])
    with pytest.raises(terminal_core.TerminalError, match="could not start"):
        instances_core.start(instance.id)
    assert instances_core.running(instance.id) is None
    assert not list(survivor.folder().glob("*.spec.json"))


def test_the_log_is_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "LOG_MAX", 1000)
    monkeypatch.setattr(runner, "LOG_KEPT", 300)
    log = runner.Log(tmp_path / "a.log")
    for n in range(100):
        log.write(f"line {n} {'x' * 20}\n".encode())
    log.handle.close()
    text = (tmp_path / "a.log").read_text()
    assert len(text) < 1100 and text.endswith(f"line 99 {'x' * 20}\n") and text.startswith("line ")


def test_old_logs_go(ctx):
    import uuid

    kept, old = uuid.uuid4(), uuid.uuid4()
    for owner in (kept, old):
        path = survivor.log_path(owner)
        path.write_text("x")
        os.utime(path, (0, 0))
    assert survivor.prune({kept}, 10) == 1
    assert survivor.log_path(kept).exists() and not survivor.log_path(old).exists()
