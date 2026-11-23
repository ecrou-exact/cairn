"""Cairn at session start (D-062)."""

import sys
from pathlib import Path

from app.core import autostart


def test_autostart_writes_and_removes_its_files(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(autostart.shutil, "which", lambda name: "/bin/systemctl")
    monkeypatch.setattr(autostart, "_systemctl", lambda *args: calls.append(args) or 0)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    root = Path("/srv/my cairn")
    assert autostart.run("on", root) == 0
    unit = (tmp_path / "systemd" / "user" / "cairn-web.service").read_text()
    assert f'ExecStart="{sys.executable}" "{root}/manage.py" serve' in unit
    assert (tmp_path / "autostart" / "cairn.desktop").is_file()
    assert calls[-1] == ("restart", "cairn-web", "cairn-worker")
    assert autostart.run("off", root) == 0
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_autostart_is_refused_elsewhere(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert autostart.run("on", Path("/x")) == 1
