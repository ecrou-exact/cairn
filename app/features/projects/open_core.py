"""Open a project's folder on the owner's machine (D-067): in the file manager, or in their
editor. Only a project's own local folder, as one argument, never through a shell. On Linux the
program is started by the session's systemd, outside Cairn's service: restarting Cairn does not
close it."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
from pathlib import Path

from app.core.db_class.planning import Project
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.claude import terminal_core
from app.features.projects.projects_core import ProjectError

FILE_MANAGERS = {"win32": "explorer", "darwin": "open"}


def _program(kind: str) -> str:
    name = get_setting("projects.editor") if kind == "editor" else FILE_MANAGERS.get(sys.platform, "xdg-open")
    found = shutil.which(name)
    if found is None:
        raise ProjectError(f"“{name}” was not found on this machine.")
    if sys.platform == "win32" and found.lower().endswith((".cmd", ".bat")):
        raise ProjectError(f"“{name}” is a script: set the editor's .exe in Settings.")
    return found


def open_folder(project: Project, kind: str) -> None:
    """`kind`: `files` (the file manager) or `editor`."""
    if not project.local_path:
        raise ProjectError(f"Set the local folder of “{project.name}” first (Edit the project).")
    folder = Path(project.local_path).expanduser()
    if not folder.is_absolute() or not folder.is_dir():
        raise ProjectError(f"The folder {folder} does not exist on this machine.")
    argv = [_program(kind), str(folder)]
    runner = shutil.which("systemd-run") if sys.platform.startswith("linux") else None
    if runner is not None:
        argv = [runner, "--user", "--collect", "--quiet", "--", *argv]
    try:
        subprocess.Popen(  # noqa: S603  # nosec B603
            argv,
            cwd=folder,
            env=terminal_core._environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise ProjectError(f"{folder} could not be opened: {exc}") from exc
    with batch():
        log_action("project.open", target_type="project", target_id=project.id, meta={"with": kind})
