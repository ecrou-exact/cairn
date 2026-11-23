"""Cairn at session start (D-062)."""

import os
import sys
from pathlib import Path

import manage
from app.core import autostart


def test_autostart_writes_and_removes_its_files(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(autostart.shutil, "which", lambda name: "/bin/systemctl")
    monkeypatch.setattr(autostart, "_systemctl", lambda *args: calls.append(args) or 0)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    old = tmp_path / "autostart" / "cairn.desktop"
    old.parent.mkdir()
    old.write_text("[Desktop Entry]")  # the page opened at each session start before D-100
    root = Path("/srv/my cairn")
    assert autostart.run("on", root) == 0
    unit = (tmp_path / "systemd" / "user" / "cairn-web.service").read_text()
    assert f'ExecStart="{sys.executable}" "{root}/manage.py" serve' in unit
    assert (tmp_path / "data" / "applications" / "cairn.desktop").is_file() and not old.exists()
    assert calls[-1] == ("restart", "cairn-web", "cairn-worker")
    assert autostart.run("off", root) == 0
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_autostart_is_refused_elsewhere(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert autostart.run("on", Path("/x")) == 1


def test_serve_reads_the_env_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("CAIRN_SECRET_KEY=from-file\nCAIRN_PORT=7999\n")
    monkeypatch.setattr(manage, "ENV_FILE", env)
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if not k.startswith("CAIRN_")})
    started = []
    monkeypatch.setattr(manage, "_run", lambda *args, env=None: started.append(args) or 0)
    assert manage.cmd_serve(None) == 0
    assert os.environ["CAIRN_SECRET_KEY"] == "from-file" and any("7999" in arg for arg in started[0])
