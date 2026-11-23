"""What Claude Code sessions are doing, read from the machine (D-050).

Claude Code writes each session's transcript to
`~/.claude/projects/<folder with every non-alphanumeric character as "-">/<session id>.jsonl`:
one JSON object per line, assistant messages carrying their `model` and token `usage`,
`ai-title` lines carrying the title it gave the conversation. From the last assistant
message we know how much of the context window the session fills: input + cache creation +
cache read tokens of that turn. Only the end of the file is read (transcripts grow large).

Sessions started outside Cairn (in a terminal, an editor) are found by their process
(`psutil`: a `claude` executable, its folder, when it started). Their conversation is the one
Claude Code registers for that process (`~/.claude/sessions/<pid>.json`), or the newest
transcript of the folder when it registers none.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psutil

from app.core.utils.settings import get_setting
from app.features.claude import limits_core

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
    now: str = ""  # what Claude does or did last, in words
    now_icon: str = ""
    events: list = field(default_factory=list)  # the last few: {"at", "who", "icon", "label"}

    def as_dict(self) -> dict:
        return asdict(self)


def projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def registry_root() -> Path:
    return Path.home() / ".claude" / "sessions"


def _registry(process: psutil.Process) -> dict:
    """Claude Code's entry for a process, or {}. A file left by a dead process whose pid was
    reused is told apart by its start time."""
    try:
        entry = json.loads((registry_root() / f"{process.pid}.json").read_text(encoding="utf-8"))
        if process.create_time() > float(entry["startedAt"]) / 1000 + 5:
            return {}
        return entry
    except (OSError, ValueError, KeyError, TypeError, psutil.Error):
        return {}


def registered(process: psutil.Process) -> str | None:
    """The conversation Claude Code registered for a process."""
    try:
        return str(uuid.UUID(_registry(process)["sessionId"]))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def registered_status(pid: int | None) -> str | None:
    """`busy`, `idle`…: what Claude Code says it is doing; None when it says nothing."""
    try:
        status = _registry(psutil.Process(pid)).get("status") if pid else None
    except psutil.Error:
        return None
    return status if isinstance(status, str) else None


def own_ancestors() -> set[int]:
    """The processes Cairn itself runs in: closing one would stop Cairn."""
    try:
        return {process.pid for process in psutil.Process().parents()}
    except psutil.Error:
        return set()


def open_elsewhere(cli_session_id: str, known_pids: set[int]) -> list[int]:
    """The `claude` processes, other than Cairn's, that have this conversation open."""
    return [
        process.pid
        for process in psutil.process_iter(["name"])
        if (process.info.get("name") or "").lower() in CLAUDE_NAMES
        and process.pid not in known_pids
        and registered(process) == cli_session_id
    ]


def folder_key(cwd: str) -> str:
    """The transcript folder Claude Code uses for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def transcript_path(cwd: str, cli_session_id: str) -> Path:
    return projects_root() / folder_key(cwd) / f"{cli_session_id}.jsonl"


def _window(model: str, used: int) -> int:
    windows = get_setting("claude.context_windows")
    size = windows.get(model) or limits_core.context_window(model) or windows.get("default", 200_000)
    return max(size, NEXT_WINDOW) if used > size else size


def tail_lines(path: Path) -> list[str]:
    with path.open("rb") as handle:
        handle.seek(0, 2)
        end = handle.tell()
        handle.seek(max(0, end - TAIL_BYTES))
        data = handle.read()
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if end > TAIL_BYTES else lines  # the first line may be cut


EVENTS_KEPT = 8
HOSTS = {  # a terminal or editor a Claude Code started outside Cairn runs in (by process name)
    "code.exe": "VS Code",
    "code": "VS Code",
    "cursor.exe": "Cursor",
    "cursor": "Cursor",
    "windowsterminal.exe": "Windows Terminal",
    "wt.exe": "Windows Terminal",
    "idea64.exe": "JetBrains",
    "pycharm64.exe": "PyCharm",
    "webstorm64.exe": "WebStorm",
    "iterm2": "iTerm2",
    "terminal": "Terminal",
    "gnome-terminal-server": "GNOME Terminal",
    "konsole": "Konsole",
    "alacritty": "Alacritty",
    "kitty": "kitty",
    "wezterm-gui": "WezTerm",
    "tmux: server": "tmux",
    "tmux": "tmux",
    "claude.exe": "Claude",
    "pwsh.exe": "PowerShell",
    "powershell.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "bash": "bash",
    "zsh": "zsh",
}
EDITORS_FIRST = (
    "VS Code",
    "Cursor",
    "JetBrains",
    "PyCharm",
    "WebStorm",
    "Windows Terminal",
    "iTerm2",
    "tmux",
)


def _short(text: str, size: int = 90) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= size else text[: size - 1] + "…"


def _relative(path: str, cwd: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(cwd).resolve())) or path
    except (ValueError, OSError):
        return path


def describe_tool(name: str, data: dict, cwd: str) -> tuple[str, str]:
    """A tool call in words, with an icon: what Claude is doing."""
    data = data if isinstance(data, dict) else {}
    target = _relative(str(data.get("file_path") or data.get("notebook_path") or ""), cwd)
    if name in ("Edit", "MultiEdit", "NotebookEdit"):
        return "fa-pen", f"Editing {target}"
    if name == "Write":
        return "fa-file-pen", f"Writing {target}"
    if name == "Read":
        return "fa-book-open", f"Reading {target}"
    if name in ("Bash", "PowerShell"):
        return "fa-terminal", _short(data.get("description") or f"Running {data.get('command', '')}")
    if name == "Grep":
        return "fa-magnifying-glass", f"Searching “{_short(data.get('pattern', ''), 50)}”"
    if name == "Glob":
        return "fa-folder-tree", f"Looking for {_short(data.get('pattern', ''), 50)}"
    if name == "WebFetch":
        return "fa-globe", f"Reading {_short(data.get('url', ''), 70)}"
    if name == "WebSearch":
        return "fa-globe", f"Searching the web: {_short(data.get('query', ''), 60)}"
    if name in ("Agent", "Task"):
        return "fa-users", f"Delegating: {_short(data.get('description', ''), 70)}"
    if name == "TodoWrite":
        return "fa-list-check", "Updating its to-do list"
    if name == "AskUserQuestion":
        return "fa-circle-question", "Asking you a question"
    if name == "Skill":
        return "fa-wand-magic-sparkles", f"Using the skill {data.get('skill', '')}"
    if name == "ToolSearch":
        return "fa-toolbox", "Loading tools"
    if name.startswith("mcp__"):
        _, server, tool = [*name.split("__", 2), "", ""][:3]
        label = tool.replace("_", " ")
        return (
            ("fa-layer-group", f"Cairn: {label}") if server == "cairn" else ("fa-plug", f"{server}: {label}")
        )
    return "fa-gear", name


def _events(entries: list[dict], cwd: str) -> list[dict]:
    found = []
    for entry in entries:
        message, at = entry.get("message"), entry.get("timestamp")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if entry.get("type") == "user" and isinstance(content, str) and not content.startswith("<"):
            found.append({"at": at, "who": "you", "icon": "fa-user", "label": _short(content)})
        elif entry.get("type") == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    icon, label = describe_tool(str(block.get("name", "")), block.get("input") or {}, cwd)
                    found.append({"at": at, "who": "claude", "icon": icon, "label": label})
                elif block.get("type") == "text" and str(block.get("text", "")).strip():
                    found.append(
                        {"at": at, "who": "claude", "icon": "fa-comment", "label": _short(block["text"])}
                    )
    return found[-EVENTS_KEPT:]


def host_of(pid: int) -> str:
    """The terminal or editor a process runs in, from its parents (the closest editor or
    terminal app; a shell only if nothing better is found)."""
    names = []
    try:
        process = psutil.Process(pid)
        for _ in range(8):
            process = process.parent()
            if process is None:
                break
            name = HOSTS.get((process.name() or "").lower())
            if name and name != "Claude":
                names.append(name)
    except psutil.Error:
        pass
    for wanted in EDITORS_FIRST:
        if wanted in names:
            return wanted
    return names[0] if names else "a terminal"


def read_usage(path: Path, cwd: str = "") -> Usage:
    """Context use, model and title of one transcript; an empty Usage when it is missing."""
    try:
        lines = tail_lines(path)
        modified = path.stat().st_mtime
    except OSError:
        return Usage()
    usage, title, entries = None, "", []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if len(entries) < 60:
            entries.append(entry)
        if usage is not None and title and len(entries) >= 60:
            break
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
    events = _events(list(reversed(entries)), cwd)
    last = next((e for e in reversed(events) if e["who"] == "claude"), None)
    return Usage(
        now=last["label"] if last else "",
        now_icon=last["icon"] if last else "",
        events=events,
        context_tokens=used,
        window=window,
        percent=round(100 * used / window, 1) if window else 0.0,
        model=model,
        title=title,
        last_activity=modified,
        transcript=True,
    )


def session_usage(cwd: str, cli_session_id: str) -> Usage:
    return read_usage(transcript_path(cwd, cli_session_id), cwd)


def outside_sessions(known_pids: set[int]) -> list[dict]:
    """`claude` processes not started by Cairn: where they run, since when, their context.

    A process whose parent is itself `claude` is a helper of that session and is skipped;
    one we may not inspect (another user's) is skipped too.
    """
    found = []
    ancestors = own_ancestors()
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
        known = registered(process)
        try:
            recent = [p for p in folder.glob("*.jsonl") if p.stat().st_mtime >= started - 5]
        except OSError:
            recent = []
        if known:
            usage, conversation = session_usage(cwd, known), known
        elif recent:
            newest = max(recent, key=lambda p: p.stat().st_mtime)
            usage, conversation = read_usage(newest, cwd), newest.stem
        found.append(
            {
                "pid": info["pid"],
                "hosts_cairn": info["pid"] in ancestors,
                "cwd": cwd,
                "cli_session_id": conversation,
                "host": host_of(info["pid"]),
                "started": started,
                "running_for": max(0, int(time.time() - started)) if started else None,
                "usage": usage.as_dict(),
            }
        )
    found.sort(key=lambda item: -(item["usage"]["last_activity"] or item["started"] or 0))
    return found
