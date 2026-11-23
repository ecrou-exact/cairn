"""Cairn at session start, on Linux (D-062): systemd user services for the web server and the
worker, and the page opened in the browser. Written for this folder and this Python; nothing
needs root. `manage.py autostart on | off | status`."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
from pathlib import Path

UNITS = {"cairn-web": "serve", "cairn-worker": "worker"}

UNIT = """[Unit]
Description=Cairn ({command})
After=graphical-session.target
PartOf=graphical-session.target

[Service]
WorkingDirectory={root}
ExecStart="{python}" "{root}/manage.py" {command}
Environment="PATH={path}"
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=graphical-session.target
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=Cairn
Comment=Open Cairn when the session starts
Exec="{python}" "{root}/manage.py" open
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def _config() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def _files(root: Path) -> dict[Path, str]:
    values = {"root": root, "python": sys.executable, "path": os.environ.get("PATH", os.defpath)}
    files = {
        _config() / "systemd" / "user" / f"{name}.service": UNIT.format(command=command, **values)
        for name, command in UNITS.items()
    }
    files[_config() / "autostart" / "cairn.desktop"] = DESKTOP.format(**values)
    return files


def _systemctl(*args: str) -> int:
    return subprocess.call([str(shutil.which("systemctl")), "--user", *args])  # noqa: S603  # nosec B603


def run(action: str, root: Path) -> int:
    if not sys.platform.startswith("linux") or shutil.which("systemctl") is None:
        print("Starting with the session is only available on Linux with systemd.")
        return 1
    units = list(UNITS)
    if action == "status":
        return _systemctl("--no-pager", "--lines=0", "status", *units)
    if action == "off":
        _systemctl("disable", "--now", *units)
        for path in _files(root):
            path.unlink(missing_ok=True)
        return _systemctl("daemon-reload")
    for path, text in _files(root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return _systemctl("daemon-reload") or _systemctl("enable", *units) or _systemctl("restart", *units)
