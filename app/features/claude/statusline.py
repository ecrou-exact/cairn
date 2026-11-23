"""The status line of a Claude Code opened from Cairn (D-056), run by Claude Code itself.

Claude Code gives its status line command a JSON object on stdin, with the account's usage
limits (`rate_limits`: share used of the 5-hour and 7-day windows, when they reset). This
keeps those numbers and the size of the model's context window (nothing else) in the file
named by the first argument, then runs the owner's own status line
(`~/.claude/settings.json`) so the terminal looks as usual.

With `--keep` it only keeps the numbers: for the owner's own status line to call it, so that
sessions outside Cairn report too (D-058). Standard library only and no Cairn import: it runs
at every refresh and must be quick.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 (the owner's own status line command, from their settings)
import sys
import time
from pathlib import Path

WINDOWS = ("five_hour", "seven_day")


def _stored(target: Path) -> dict:
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _newer(found: dict, known: dict | None) -> bool:
    """Several sessions report, some with old numbers: within a window usage only grows."""
    if not isinstance(known, dict):
        return True
    ends, known_ends = found["resets_at"] or 0, known.get("resets_at") or 0
    return ends > known_ends or (ends == known_ends and found["used"] >= known.get("used", 0))


def keep(data: dict, target: Path) -> None:
    kept = _stored(target)
    before = json.dumps(kept)
    limits = data.get("rate_limits")
    for name in WINDOWS:
        window = limits.get(name) if isinstance(limits, dict) else None
        if isinstance(window, dict) and isinstance(window.get("used_percentage"), int | float):
            found = {"used": window["used_percentage"], "resets_at": window.get("resets_at")}
            if _newer(found, kept.get(name)):
                kept[name], kept["at"] = found, time.time()
    model, context = data.get("model"), data.get("context_window")
    if isinstance(model, dict) and isinstance(context, dict):
        name, size = str(model.get("id") or "").split("[")[0], context.get("context_window_size")
        if name and isinstance(size, int) and size > 0:
            sizes = kept.get("context_windows")
            kept["context_windows"] = {**(sizes if isinstance(sizes, dict) else {}), name: size}
    if json.dumps(kept) == before:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.{os.getpid()}")
    partial.write_text(json.dumps(kept), encoding="utf-8")
    partial.replace(target)


def own_command() -> str:
    try:
        settings = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
        return str(settings["statusLine"]["command"])
    except (OSError, ValueError, KeyError, TypeError):
        return ""


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            keep(data, Path(sys.argv[1]))
    except (OSError, ValueError, IndexError):
        pass  # the owner's status line still shows
    if "--keep" in sys.argv[2:]:
        return 0
    command, bash = own_command(), shutil.which("bash")
    if command and bash:
        return subprocess.run([bash, "-c", command], input=raw, check=False).returncode  # noqa: S603  # nosec B603
    return 0


if __name__ == "__main__":
    sys.exit(main())
