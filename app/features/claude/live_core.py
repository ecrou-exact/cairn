"""What every Claude Code is doing right now, as a graph (D-059).

Only facts read from the machine: the conversation's transcript (tool calls without a result
yet, background tasks without an end, the files, skills and servers used since the last
request), its agents' own files (`<session>/subagents/agent-*.jsonl` with a `.meta.json` that
says whether it finished), Claude Code's registry (busy or idle) and the processes it started.

Two levels: every running session with what is alive under it; one session, with all it did
since the owner's last request. Cairn lays the graph out left to right (D-035).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from app.features.claude import claude_core, terminal_core, transcript_core
from app.features.claude.transcript_core import describe_tool

CARD_W, COL_GAP = 224, 176  # the cards of the plan's graph (graph_core), further apart
ROW = 124
FILES_SHOWN = 12
ITEMS_KEPT = 15
SETTLED = 3.0  # seconds a process must have lived to be shown: helpers come and go
WORKING = 20.0  # without a registry entry: seconds since the transcript moved
AGENT_QUIET = 600.0  # an unfinished agent silent for longer was cut, not working
SHELLS = {
    "sh",
    "bash",
    "zsh",
    "fish",
    "dash",
    "uv",
    "timeout",
    "nohup",
    "pwsh.exe",
    "powershell.exe",
    "cmd.exe",
}
FILTERS = {"grep", "ugrep", "rg", "head", "tail", "cat", "tee", "sleep", "sed", "awk"}  # ends of pipes
CHANGES = ("Edit", "MultiEdit", "Write", "NotebookEdit")
TASK_ID = re.compile(r"<task-id>([\w-]+)</task-id>")
TASK_END = re.compile(r"<status>(completed|failed|killed|stopped)</status>")
GROUPS = {  # tool → group of the session's own graph
    "Bash": "commands",
    "PowerShell": "commands",
    "Read": "reads",
    "Grep": "searches",
    "Glob": "searches",
    "WebFetch": "web",
    "WebSearch": "web",
}
GROUP_LABELS = {
    "commands": ("Commands", "fa-terminal"),
    "reads": ("Files read", "fa-book-open"),
    "searches": ("Searches", "fa-magnifying-glass"),
    "web": ("Web", "fa-globe"),
}
ORDER = (
    "agent",
    "running",
    "background",
    "process",
    "skill",
    "file",
    "commands",
    "reads",
    "searches",
    "web",
    "server",
)


@dataclass
class Call:
    id: str
    name: str
    input: dict
    at: str
    label: str
    icon: str
    done: bool = False
    failed: bool = False


@dataclass
class Conversation:
    prompt: str = ""
    prompt_at: str = ""
    calls: list[Call] = field(default_factory=list)  # since the last request
    background: dict[str, Call] = field(default_factory=dict)  # started, no end seen
    ids: set[str] = field(default_factory=set)  # every call seen, to tell whose an agent is


def _epoch(at: str) -> float:
    try:
        return datetime.fromisoformat(at.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def _request(entry: dict) -> str:
    """The owner's words in a user entry; empty for anything Claude Code wrote itself."""
    origin = entry.get("origin")
    if entry.get("isMeta") or (isinstance(origin, dict) and origin.get("kind") != "human"):
        return ""
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        content = " ".join(
            str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    text = str(content or "").strip()
    return "" if text.startswith("<") else text


def read_conversation(lines: list[str], cwd: str, agent: bool = False) -> Conversation:
    """One transcript (its end), in order. `agent`: an agent's own file, whose entries are all
    side-chain ones and whose first message is its task, not the owner's request."""
    found = Conversation()
    calls: dict[str, Call] = {}
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or (entry.get("isSidechain") and not agent):
            continue
        kind, at = entry.get("type"), str(entry.get("timestamp") or "")
        message = entry.get("message")
        if kind == "queue-operation" or (kind == "user" and isinstance(message, dict)):
            text = entry.get("content") if kind == "queue-operation" else message.get("content")
            if isinstance(text, str) and "<task-notification>" in text and TASK_END.search(text):
                for task_id in TASK_ID.findall(text):
                    found.background.pop(task_id, None)
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if kind == "user":
            words = "" if agent else _request(entry)
            if words:
                found.prompt, found.prompt_at = words, at
                found.calls = []
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                call = calls.get(str(block.get("tool_use_id")))
                if call is None:
                    continue
                call.done, call.failed = True, bool(block.get("is_error"))
                result = entry.get("toolUseResult")
                if isinstance(result, dict) and result.get("backgroundTaskId"):
                    found.background[str(result["backgroundTaskId"])] = call
        elif kind == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name, data = str(block.get("name", "")), block.get("input")
                data = data if isinstance(data, dict) else {}
                icon, label = describe_tool(name, data, cwd)
                call = Call(str(block.get("id")), name, data, at, label, icon)
                calls[call.id] = call
                found.calls.append(call)
    found.ids = set(calls)
    return found


_cache: dict[Path, tuple[tuple[float, int], Conversation]] = {}


def _conversation(path: Path, cwd: str, agent: bool = False) -> Conversation:
    """`read_conversation` of a file, again only when the file changed."""
    try:
        stat = path.stat()
        mark = (stat.st_mtime, stat.st_size)
        known = _cache.get(path)
        if known and known[0] == mark:
            return known[1]
        read = read_conversation(transcript_core.tail_lines(path), cwd, agent)
    except OSError:
        return Conversation()
    if len(_cache) > 200:
        _cache.clear()
    _cache[path] = (mark, read)
    return read


# -- agents and processes ---------------------------------------------------------------------


def _agents(transcript: Path, cwd: str, since: float, born: float) -> list[dict[str, Any]]:
    """The conversation's agents: at work, or that finished since `since` (the last request)."""
    found = []
    folder = transcript.with_suffix("") / "subagents"
    try:
        metas = sorted(folder.glob("agent-*.meta.json"))
    except OSError:
        return []
    for meta_path in metas:
        path = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".jsonl")
        try:
            moved = path.stat().st_mtime
            if moved < max(born, min(since, time.time() - AGENT_QUIET)):
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        working = not meta.get("finished") and time.time() - moved < AGENT_QUIET
        if not working and moved < since:
            continue
        found.append(
            {
                "id": path.stem,
                "type": str(meta.get("agentType") or "agent"),
                "label": str(meta.get("description") or meta.get("agentType") or "Agent"),
                "model": str(meta.get("model") or ""),
                "call": str(meta.get("toolUseId") or ""),
                "working": working,
                "conversation": _conversation(path, cwd, agent=True),
            }
        )
    return found


def _program(process: psutil.Process) -> str:
    """A process in a few words: its program and plain arguments. Options and NAME=value are
    left out: they may carry secrets."""
    argv = process.cmdline() or [process.name()]
    words = [Path(argv[0]).name]
    for arg in argv[1:]:
        if arg.startswith("-") or "=" in arg or "://" in arg or " " in arg or len(arg) > 80:
            continue
        words.append(Path(arg).name)
        if len(words) == 4:
            break
    if len(words) > 1 and words[0].startswith("python"):
        words = words[1:]
    return " ".join(words)


def _processes(pid: int) -> list[dict[str, Any]]:
    """What a Claude Code started and still runs: a command's own processes, not the shells
    around them, with the ports they listen on."""
    from app.features.instances import instances_core  # instances build on this feature

    found: list[dict[str, Any]] = []

    def walk(process: psutil.Process, depth: int) -> None:
        try:
            name = (process.name() or "").lower()
            if name in transcript_core.CLAUDE_NAMES:
                return
            children = process.children()
            if name in SHELLS and depth < 4:
                for child in children:
                    walk(child, depth + 1)
                return
            if name in FILTERS or time.time() - process.create_time() < SETTLED:
                return
            label = _program(process)
            if label.split(" ")[0] in FILTERS:  # run by another binary, under its name
                return
            argv = " ".join(process.cmdline()).lower()
            found.append(
                {
                    "id": f"{process.pid}-{int(process.create_time())}",
                    "pid": process.pid,
                    "label": label,
                    "server": "mcp" in argv,
                    "since": process.create_time(),
                    "family": len(process.children(recursive=True)),
                    "ports": instances_core.listening_ports(process.pid),
                }
            )
        except psutil.Error:
            return

    try:
        for child in psutil.Process(pid).children():
            walk(child, 0)
    except psutil.Error:
        return []
    return found


# -- the graph --------------------------------------------------------------------------------


def _running() -> list[dict[str, Any]]:
    """Every Claude Code running on this machine, in Cairn or not."""
    found = []
    for row in terminal_core.sessions():
        if not terminal_core.is_running(row.id):
            continue
        facts = claude_core.describe(row)
        found.append(
            {
                "key": str(row.id),
                "pid": row.pid,
                "cwd": row.cwd,
                "conversation": facts["cli_session_id"],
                "title": facts["title"],
                "where": "in Cairn",
                "project": facts["project"],
                "usage": facts["usage"],
                "started": row.created_at.timestamp(),
                "open": facts["url"],
            }
        )
    for facts in claude_core.outside():
        found.append(
            {
                "key": f"pid-{facts['pid']}",
                "pid": facts["pid"],
                "cwd": facts["cwd"],
                "conversation": facts["cli_session_id"],
                "title": facts["usage"]["title"] or Path(facts["cwd"]).name or "Claude Code",
                "where": f"in {facts['host']}",
                "project": facts["project"],
                "usage": facts["usage"],
                "started": facts["started"],
                "open": None,
            }
        )
    return found


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []

    def add(self, node_id: str, parent: str | None, kind: str, label: str, icon: str, **data: Any) -> str:
        data = {"kind": kind, "label": label, "icon": icon, "live": False, "parent": parent, **data}
        self.nodes.append({"id": node_id, "data": data})
        if parent is not None:
            self.edges.append(
                {
                    "id": f"{parent}>{node_id}",
                    "from": parent,
                    "to": node_id,
                    "data": {"kind": "live" if data["live"] else "past"},
                }
            )
        return node_id


def _items(calls: list[Call]) -> list[dict[str, Any]]:
    return [
        {"at": c.at, "label": c.label, "state": "failed" if c.failed else ("done" if c.done else "running")}
        for c in reversed(calls[-ITEMS_KEPT:])
    ]


def _state(session: dict[str, Any]) -> str:
    """working / waiting, from Claude Code's registry, or from the transcript's last change."""
    status = transcript_core.registered_status(session["pid"])
    if status is not None:
        return "working" if status == "busy" else "waiting"
    moved = session["usage"]["last_activity"]
    return "working" if moved and time.time() - moved < WORKING else "waiting"


def _session(build: _Builder, session: dict[str, Any], full: bool) -> None:
    key, cwd, state = session["key"], session["cwd"], _state(session)
    talk, transcript = Conversation(), None
    if session["conversation"]:
        transcript = transcript_core.transcript_path(cwd, session["conversation"])
        talk = _conversation(transcript, cwd)
    working, usage = state == "working", session["usage"]
    build.add(
        key,
        None,
        "session",
        session["title"],
        "fa-terminal",
        live=working,
        state=state,
        cwd=cwd,
        where=session["where"],
        pid=session["pid"],
        project=session["project"],
        model=usage["model"].replace("claude-", ""),
        context=usage["percent"],
        now=usage["now"] if working else "",
        prompt=talk.prompt[:400],
        prompt_at=talk.prompt_at,
        calls=len(talk.calls),
        items=_items(talk.calls),
        url=session["open"],
        drill=None if full else f"/claude/live?session={key}",
    )

    def running(owner: str, calls: list[Call], alive: bool) -> None:
        for call in calls:
            if alive and not call.done and call.name not in ("Agent", "Task"):
                build.add(
                    f"{owner}/t/{call.id}",
                    owner,
                    "running",
                    call.label,
                    call.icon,
                    live=True,
                    state="running",
                    tool=call.name,
                    since=call.at,
                )

    agents = (
        _agents(transcript, cwd, _epoch(talk.prompt_at), session["started"] - 5 if session["started"] else 0)
        if transcript is not None
        else []
    )
    owners = {call: f"{key}/a/{a['id']}" for a in agents for call in a["conversation"].ids}
    for agent in agents:
        node = f"{key}/a/{agent['id']}"
        parent = owners.get(agent["call"], key)
        calls = agent["conversation"].calls
        build.add(
            node,
            parent if parent != node else key,
            "agent",
            agent["label"],
            "fa-user-astronaut",
            live=agent["working"],
            state="working" if agent["working"] else "finished",
            agent=agent["type"],
            model=agent["model"].replace("claude-", ""),
            calls=len(calls),
            now=calls[-1].label if calls and agent["working"] else "",
            items=_items(calls),
        )
        running(node, calls, agent["working"])
    running(key, talk.calls, working)
    for task_id, call in talk.background.items():
        if _epoch(call.at) < session["started"] - 5:
            continue  # started by an earlier Claude Code on this conversation: gone with it
        build.add(
            f"{key}/b/{task_id}",
            key,
            "background",
            call.label,
            "fa-layer-group",
            live=True,
            state="in the background",
            since=call.at,
        )
    for process in _processes(session["pid"]) if session["pid"] else []:
        if process["server"] and not full:
            continue
        build.add(
            f"{key}/p/{process['id']}",
            key,
            "process",
            process["label"],
            "fa-plug" if process["server"] else "fa-gears",
            live=True,
            state="MCP server" if process["server"] else "process",
            pid=process["pid"],
            since=datetime.fromtimestamp(process["since"]).astimezone().isoformat(),
            ports=process["ports"],
            family=process["family"],
        )
    skills: dict[str, list[Call]] = {}
    servers: dict[str, list[Call]] = {}
    files: dict[str, list[Call]] = {}
    groups: dict[str, list[Call]] = {}
    for call in talk.calls:
        if call.name == "Skill":
            skills.setdefault(str(call.input.get("skill") or "skill"), []).append(call)
        elif call.name.startswith("mcp__"):
            servers.setdefault(call.name.split("__")[1], []).append(call)
        elif call.name in CHANGES:
            path = str(call.input.get("file_path") or call.input.get("notebook_path") or "")
            files.setdefault(path, []).append(call)
        elif call.name in GROUPS:
            groups.setdefault(GROUPS[call.name], []).append(call)

    def group(kind: str, name: str, label: str, icon: str, calls: list[Call], **data: Any) -> None:
        build.add(
            f"{key}/{kind}/{name}",
            key,
            kind,
            label,
            icon,
            state=f"{len(calls)}×",
            live=working and any(not c.done for c in calls),
            failed=sum(c.failed for c in calls),
            items=_items(calls),
            **data,
        )

    for name, calls in skills.items():
        group("skill", name, name, "fa-wand-magic-sparkles", calls)
    if not full:
        return
    recent = sorted(files.items(), key=lambda item: item[1][-1].at, reverse=True)
    for path, calls in recent[:FILES_SHOWN]:
        group("file", path, Path(path).name or path, "fa-file-pen", calls, path=path)
    if len(recent) > FILES_SHOWN:
        rest = [call for _, calls in recent[FILES_SHOWN:] for call in calls]
        more = len(recent) - FILES_SHOWN
        group("file", "more", f"{more} more file{'s' if more > 1 else ''}", "fa-file-pen", rest)
    for name, (label, icon) in GROUP_LABELS.items():
        if name in groups:
            group(name, "all", label, icon, groups[name])
    for name, calls in servers.items():
        group("server", name, name, "fa-plug", calls)


def layout(nodes: list[dict[str, Any]]) -> None:
    """Left to right: a column per level, a card centred on what is under it; pinned."""
    under: dict[str | None, list[dict[str, Any]]] = {}
    for node in nodes:
        under.setdefault(node["data"]["parent"], []).append(node)
    row = 0.0

    def place(node: dict[str, Any], depth: int) -> float:
        nonlocal row
        below = sorted(
            under.get(node["id"], []),
            key=lambda n: ORDER.index(n["data"]["kind"]),
        )
        if below:
            ys = [place(child, depth + 1) for child in below]
            y = (ys[0] + ys[-1]) / 2
        else:
            y = row
            row += ROW
        x = float(depth * (CARD_W + COL_GAP))
        node.update({"x": x, "y": y, "fx": x, "fy": y})
        return y

    for root in under.get(None, []):
        place(root, 0)
        row += ROW * 0.4


def graph(session: str | None = None) -> dict[str, Any]:
    """The graph of every running session, or of one (`session`: its key)."""
    sessions = _running()
    if session is not None:
        sessions = [s for s in sessions if s["key"] == session]
    build = _Builder()
    for found in sessions:
        _session(build, found, full=session is not None)
    layout(build.nodes)
    return {
        "nodes": build.nodes,
        "edges": build.edges,
        "sessions": len(sessions),
        "live": sum(1 for n in build.nodes if n["data"]["live"]),
        "at": time.time(),
    }
