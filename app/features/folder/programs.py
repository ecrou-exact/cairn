"""git and GitHub's command line, read only: what they print, "" or None when they fail."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
from pathlib import Path
from typing import Any

from app.features.claude import terminal_core

TIMEOUT = 40


def _run(argv: list[str]) -> str:
    env = {
        **terminal_core._environment(),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GH_PROMPT_DISABLED": "1",
        "LC_ALL": "C",
    }
    try:
        done = subprocess.run(  # noqa: S603  # nosec B603
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def git(folder: Path, *args: str) -> str:
    found = shutil.which("git")
    return _run([found, "-C", str(folder), *args]) if found else ""


def gh(path: str, *fields: str, method: str = "GET") -> Any:
    """An answer of GitHub's API, with the owner's own sign-in."""
    found = shutil.which("gh")
    if found is None:
        return None
    args = [found, "api", "--method", method, path]
    for field in fields:
        args += ["-f", field]
    try:
        return json.loads(_run(args) or "null")
    except ValueError:
        return None
