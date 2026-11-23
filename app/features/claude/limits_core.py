"""How much of the account's Claude usage is left (D-056): the numbers the status line of the
sessions Cairn opens last reported. They are the account's, shared by every session."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from flask import current_app

from app.features.claude import statusline

LABELS = {"five_hour": "5h", "seven_day": "7d"}


def limits_file() -> Path:
    return Path(current_app.config["CAIRN_DATA_DIR"]) / "claude" / "limits.json"


def settings_json() -> str:
    """The `--settings` of a session: Cairn's status line, which runs the owner's after it."""
    parts = (Path(sys.executable), Path(statusline.__file__).resolve(), limits_file().resolve())
    command = " ".join(f'"{part.as_posix()}"' for part in parts)
    return json.dumps({"statusLine": {"type": "command", "command": command}})


def context_window(model: str) -> int | None:
    """The size of a model's context window, as Claude Code last reported it."""
    try:
        size = json.loads(limits_file().read_text(encoding="utf-8"))["context_windows"][model]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return size if isinstance(size, int) and size > 0 else None


def limits() -> dict[str, Any]:
    """`{"at", "windows": [{"key", "label", "used", "left", "resets_at"}]}`; a window whose
    reset has passed is left out: its number is no longer known."""
    try:
        data = json.loads(limits_file().read_text(encoding="utf-8"))
        windows = []
        for key, label in LABELS.items():
            window = data.get(key)
            if window is None or (window["resets_at"] and float(window["resets_at"]) <= time.time()):
                continue
            used = min(100, max(0, round(float(window["used"]))))
            windows.append(
                {
                    "key": key,
                    "label": label,
                    "used": used,
                    "left": 100 - used,
                    "resets_at": window["resets_at"],
                }
            )
        return {"at": float(data["at"]), "windows": windows}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"at": None, "windows": []}
