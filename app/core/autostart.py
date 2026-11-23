"""Cairn at session start, on Linux (D-062): systemd user services for the web server and the
worker, and the page opened in the browser. Written for this folder and this Python; nothing
needs root. `manage.py autostart on | off | status`. The server starts with the user's session (D-100);
the page opens only from the applications menu."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
from pathlib import Path

UNITS = {"cairn-web": "serve", "cairn-worker": "worker"}

UNIT = """[Unit]
Description=Cairn ({command})
After=network.target

[Service]
WorkingDirectory={root}
ExecStart="{python}" "{root}/manage.py" {command}
Environment="PATH={path}"
Environment=CAIRN_ENV=production
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=default.target
"""

# In the applications menu: Cairn opens on a click; the server runs already, from the session's start.
DESKTOP = """[Desktop Entry]
Type=Application
Name=Cairn
GenericName=Planning workspace
Comment=Open Cairn: projects, tasks, Claude
Exec="{python}" "{root}/manage.py" open
Icon=cairn
Terminal=false
Categories=Development;ProjectManagement;
StartupNotify=false
"""


def _config() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def _data() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


# Opened the page at each session start, before the owner asked for the menu entry instead (D-100).
OLD_AUTOSTART = "autostart/cairn.desktop"


def _files(root: Path) -> dict[Path, str]:
    values = {"root": root, "python": sys.executable, "path": os.environ.get("PATH", os.defpath)}
    files = {
        _config() / "systemd" / "user" / f"{name}.service": UNIT.format(command=command, **values)
        for name, command in UNITS.items()
    }
    files[_data() / "applications" / "cairn.desktop"] = DESKTOP.format(**values)
    # The app's own icon (a light mark on a dark tile: the plain mark is drawn in the text colour)
    files[_data() / "icons" / "hicolor" / "scalable" / "apps" / "cairn.svg"] = (
        Path(__file__).resolve().parents[2] / "docs" / "brand" / "cairn-app.svg"
    ).read_text(encoding="utf-8")
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
        for path in [*_files(root), _config() / OLD_AUTOSTART]:
            path.unlink(missing_ok=True)
        return _systemctl("daemon-reload")
    (_config() / OLD_AUTOSTART).unlink(missing_ok=True)
    for path, text in _files(root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return _systemctl("daemon-reload") or _systemctl("enable", *units) or _systemctl("restart", *units)


def wake() -> None:
    """Start the services when they were installed and are stopped; nothing otherwise."""
    if not sys.platform.startswith("linux") or shutil.which("systemctl") is None:
        return
    if not (_config() / "systemd" / "user" / "cairn-web.service").exists():
        return
    try:
        stopped = subprocess.run(  # noqa: S603  # nosec B603
            [str(shutil.which("systemctl")), "--user", "is-active", "--quiet", "cairn-web"], check=False
        ).returncode
    except OSError:
        return
    if stopped:
        _systemctl("start", *UNITS)
