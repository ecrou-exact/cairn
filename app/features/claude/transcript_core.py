"""What Claude Code sessions are doing, read from the machine (D-050).

Claude Code writes each session's transcript to
`~/.claude/projects/<folder with every non-alphanumeric character as "-">/<session id>.jsonl`:
one JSON object per line, assistant messages carrying their `model` and token `usage`,
`ai-title` lines carrying the title it gave the conversation. From the last assistant
message we know how much of the context window the session fills: input + cache creation +
cache read tokens of that turn. Only the end of the file is read (transcripts grow large).

Sessions started outside Cairn (in a terminal, an editor) are found by their process
(`psutil`: a `claude` executable, its folder, when it started) and matched with the newest
transcript of that folder.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

from app.core.utils.settings import get_setting

TAIL_BYTES = 768 * 1024  # enough for the last turns; titles come often
NEXT_WINDOW = 1_000_000  # a session past its configured window is counted against this
CLAUDE_NAMES = {"claude", "claude.exe"}


@dataclass
class Usage:
    context_tokens: int = 0
    window: int = 0
    percent: float = 0.0
    model: str = ""
    title: str = ""
    last_activity: float | None = None  # epoch seconds (transcript modified)
    transcript: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def folder_key(cwd: str) -> str:
    """The transcript folder Claude Code uses for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def transcript_path(cwd: str, cli_session_id: str) -> Path:
    return projects_root() / folder_key(cwd) / f"{cli_session_id}.jsonl"


def _window(model: str, used: int) -> int:
    windows = get_setting("claude.context_windows")
    size = windows.get(model) or windows.get("default", 200_000)
    return max(size, NEXT_WINDOW) if used > size else size


def _tail_lines(path: Path) -> list[str]:
    with path.open("rb") as handle:
        handle.seek(0, 2)
        end = handle.tell()
        handle.seek(max(0, end - TAIL_BYTES))
        data = handle.read()
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if end > TAIL_BYTES else lines  # the first line may be cut


def read_usage(path: Path) -> Usage:
    """Context use, model and title of one transcript; an empty Usage when it is missing."""
    try:
        lines = _tail_lines(path)
        modified = path.stat().st_mtime
    except OSError:
        return Usage()
    usage, title = None, ""
    for line in reversed(lines):
        if usage is not None and title:
            break
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not title and entry.get("type") == "ai-title":
            title = str(entry.get("aiTitle") or "")[:200]
        message = entry.get("message")
        if usage is None and entry.get("type") == "assistant" and isinstance(message, dict):
            numbers = message.get("usage")
            if isinstance(numbers, dict):
                used = sum(
                    int(numbers.get(key) or 0)
                    for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                )
                usage = (used, str(message.get("model") or ""))
    used, model = usage or (0, "")
    window = _window(model, used)
    return Usage(
        context_tokens=used,
        window=window,
        percent=round(100 * used / window, 1) if window else 0.0,
        model=model,
        title=title,
        last_activity=modified,
        transcript=True,
    )


def session_usage(cwd: str, cli_session_id: str) -> Usage:
    return read_usage(transcript_path(cwd, cli_session_id))


def outside_sessions(known_pids: set[int]) -> list[dict]:
    """`claude` processes not started by Cairn: where they run, since when, their context.

    A process whose parent is itself `claude` is a helper of that session and is skipped;
    one we may not inspect (another user's) is skipped too.
    """
    found = []
    for process in psutil.process_iter(["pid", "name", "create_time", "ppid"]):
        info = process.info
        if (info.get("name") or "").lower() not in CLAUDE_NAMES or info["pid"] in known_pids:
            continue
        try:
            parent = psutil.Process(info["ppid"]) if info.get("ppid") else None
            if parent is not None and (parent.name() or "").lower() in CLAUDE_NAMES:
                continue
            if parent is not None and parent.pid in known_pids:
                continue
            cwd = process.cwd()
        except (psutil.Error, OSError):
            continue
        usage, conversation = Usage(), None
        folder = projects_root() / folder_key(cwd)
        started = info.get("create_time") or 0
        try:
            recent = [p for p in folder.glob("*.jsonl") if p.stat().st_mtime >= started - 5]
        except OSError:
            recent = []
        if recent:
            newest = max(recent, key=lambda p: p.stat().st_mtime)
            usage, conversation = read_usage(newest), newest.stem
        found.append(
            {
                "pid": info["pid"],
                "cwd": cwd,
                "cli_session_id": conversation,
                "started": started,
                "running_for": max(0, int(time.time() - started)) if started else None,
                "usage": usage.as_dict(),
            }
        )
    found.sort(key=lambda item: -(item["usage"]["last_activity"] or item["started"] or 0))
    return found
