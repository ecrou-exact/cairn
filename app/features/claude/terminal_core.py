"""Claude Code in a terminal inside Cairn (D-050).

The owner's own `claude` runs in a pseudo-terminal, in the project's folder, with the owner's
own sign-in and settings: Cairn does not drive it, it hosts it. One `Terminal` per session,
kept in this (web) process while it runs, so leaving the page does not stop it; its output is
kept (up to `SCROLLBACK` characters) so a page that comes back, or a dropped stream, resumes
where it was.

Only the configured Claude Code executable is ever started (argv list, no shell), and only
in a project's local folder. Every start and end is logged.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.claude import NewProjectStart, SessionStart
from app.core.schema.planning import ProjectCreate
from app.core.utils.actor import acting_as
from app.core.utils.events import publish
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.claude import mcp_server, transcript_core
from app.features.claude.pty_host import Pty
from app.features.connections import connections_core
from app.features.projects import projects_core
from app.features.tasks import brief_core

SCROLLBACK = 2_000_000  # characters of output kept per session for resuming
BRIEF_LIMIT = 24_000  # a first message stays well under Windows' 32k command line
# Markers a running Claude Code gives the processes it starts (its session, "child session",
# its messaging socket and token…). Cairn may itself have been started from a Claude Code
# session: the Claude it opens must be a fresh, top-level session of its own (otherwise it
# does not save its transcript), and the parent's token must not travel. Settings the owner
# sets on purpose (CLAUDE_CODE_USE_BEDROCK, limits…) are kept.
HIDDEN_ENV = frozenset(
    {
        "CLAUDECODE",
        "CLAUDE_PID",
        "CLAUDE_EFFORT",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_EXECPATH",
        "CLAUDE_AGENT_SDK_VERSION",
    }
)
HIDDEN_ENV_PREFIXES = ("CLAUDE_CODE_CHILD_", "CLAUDE_CODE_SESSION_", "CLAUDE_CODE_MESSAGING_")


class TerminalError(ValueError):
    pass


@dataclass
class Terminal:
    session_id: uuid.UUID
    pty: Pty
    files: tuple[Path, ...] = ()  # removed when the session ends (rules, MCP config)
    kind: str = "claude"
    chunks: deque = field(default_factory=deque)  # (seq, text)
    size: int = 0
    seq: int = 0
    ended: bool = False
    cond: threading.Condition = field(default_factory=threading.Condition)

    def append(self, text: str) -> None:
        with self.cond:
            self.seq += 1
            self.chunks.append((self.seq, text))
            self.size += len(text)
            while self.size > SCROLLBACK and len(self.chunks) > 1:
                _, old = self.chunks.popleft()
                self.size -= len(old)
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.ended = True
            self.cond.notify_all()

    def since(self, after: int, wait: float = 0.0) -> tuple[list[tuple[int, str]], bool]:
        """Output after `after`, waiting up to `wait` seconds for some; and whether it ended."""
        with self.cond:
            if wait and not self.ended and (not self.chunks or self.chunks[-1][0] <= after):
                self.cond.wait(wait)
            return [(seq, text) for seq, text in self.chunks if seq > after], self.ended


_terminals: dict[uuid.UUID, Terminal] = {}
_lock = threading.Lock()


def _terminal(session_id: uuid.UUID) -> Terminal:
    with _lock:
        terminal = _terminals.get(session_id)
    if terminal is None:
        raise TerminalError("This Claude session is not running.")
    return terminal


def _where(data: SessionStart) -> tuple[Project | None, Task | None, Path]:
    task = db.session.get(Task, data.task_id) if data.task_id else None
    if data.task_id and (task is None or task.is_deleted):
        raise TerminalError("This task does not exist.")
    project = task.project if task is not None else db.session.get(Project, data.project_id)
    if project is None or project.is_deleted:
        raise TerminalError("Claude runs in a project's folder: put this task in a project first.")
    if not project.local_path:
        raise TerminalError(f"Set the local folder of “{project.name}” first (Edit the project).")
    folder = Path(project.local_path).expanduser()
    if not folder.is_dir():
        raise TerminalError(f"The folder {folder} does not exist on this machine.")
    return project, task, folder


def _environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in HIDDEN_ENV and not key.upper().startswith(HIDDEN_ENV_PREFIXES)
    }
    env.update({"TERM": "xterm-256color", "COLORTERM": "truecolor"})
    return env


# What a session is opened for (D-051): label, icon, what the launcher asks for. One place,
# used by the launcher, the palette and the buttons; the first message is built here.
PRESET_INFO = {
    "free": {
        "label": "Work freely",
        "icon": "fa-terminal",
        "asks": "",
        "hint": "Anything to start with (optional)",
    },
    "task": {
        "label": "Work on a task",
        "icon": "fa-list-check",
        "asks": "task",
        "hint": "Anything to add (optional)",
    },
    "pr": {
        "label": "Answer a pull request",
        "icon": "fa-code-pull-request",
        "asks": "url",
        "hint": "https://github.com/…/pull/42",
    },
    "fix": {"label": "Fix a bug", "icon": "fa-bug", "asks": "text", "hint": "What goes wrong, how to see it"},
    "review": {
        "label": "Review the changes",
        "icon": "fa-magnifying-glass",
        "asks": "",
        "hint": "What to look at (optional)",
    },
}


def _brief(task: Task) -> str:
    brief = brief_core.task_brief(task)
    if len(brief) > BRIEF_LIMIT:
        brief = (
            brief[:BRIEF_LIMIT] + "\n\n[The brief was cut here; the full one is on the task page in Cairn.]"
        )
    return brief


def _first_message(data: SessionStart, task: Task | None) -> str | None:
    """The message Claude Code starts with, from the preset and the owner's words."""
    words = data.detail.strip()
    about = f"\n\nThis is about the task “{task.title}” tracked in Cairn." if task is not None else ""
    if data.preset == "task" and task is not None:
        extra = f"\n\nAlso: {words}" if words else ""
        return f"I want to work on this task, tracked in Cairn. Here is its brief:\n\n{_brief(task)}{extra}"
    if data.preset == "pr":
        return (
            f"Take care of this pull request: {words}\n"
            "Read it with its review comments (the gh CLI is the easiest way), answer each comment, "
            "make the changes asked for, run the tests, then show me the diff and wait for my go "
            f"before committing or pushing anything.{about}"
        )
    if data.preset == "fix":
        return (
            f"There is a bug to fix: {words}\n"
            "Find the cause first, fix it, add a test that fails without the fix, run the tests, "
            f"then show me the diff and wait for my go before committing.{about}"
        )
    if data.preset == "review":
        focus = f" Look especially at: {words}." if words else ""
        return (
            "Review the current changes in this repository (git status, git diff, the last commits)."
            f"{focus} Correctness first, then clarity. List what you find by importance; do not change "
            f"code unless I ask.{about}"
        )
    return (words + about) if words else (about.strip() or None)


def _title(data: SessionStart, project: Project, task: Task | None) -> str:
    words = " ".join(data.detail.split())
    if data.preset == "pr":
        return f"PR {words.rstrip('/').rsplit('/', 1)[-1]}" if "/pull/" in words else "Pull request"
    if data.preset == "fix":
        return f"Fix: {words[:80]}"
    if data.preset == "review":
        return f"Review of {project.name}"
    return task.title if task is not None else project.name


def _rules_file(session_id: uuid.UUID, project: Project | None) -> Path:
    """The owner's rules and the project's instructions, appended to Claude Code's system
    prompt (a file: a command line is limited to 32k characters on Windows)."""
    folder = Path(current_app.config["CAIRN_DATA_DIR"]) / "claude"
    folder.mkdir(parents=True, exist_ok=True)
    rules = get_setting("claude.rules")
    text = "Rules from the owner, set in Cairn:\n" + "\n".join(f"- {rule}" for rule in rules)
    if project is not None and project.claude_instructions_md.strip():
        text += (
            f"\n\nInstructions for the project “{project.name}”:\n{project.claude_instructions_md.strip()}"
        )
    path = folder / f"{session_id}.md"
    path.write_text(text + "\n", encoding="utf-8")
    return path


def _mcp_config(session_id: uuid.UUID) -> Path:
    """Cairn's MCP server for this session (D-052), started by Claude Code over stdio."""
    folder = Path(current_app.config["CAIRN_DATA_DIR"]) / "claude"
    folder.mkdir(parents=True, exist_ok=True)
    manage = Path(current_app.root_path).parent / "manage.py"
    config = {
        "mcpServers": {
            mcp_server.SERVER_NAME: {
                "type": "stdio",
                "command": sys.executable,
                "args": [str(manage), "mcp"],
                "env": {"CAIRN_MCP_SESSION": str(session_id)},
            }
        }
    }
    path = folder / f"{session_id}.mcp.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def command(
    executable: str,
    cli_session_id: uuid.UUID,
    first_message: str | None,
    rules: Path | None = None,
    resume: bool = False,
    mcp: Path | None = None,
) -> list[str]:
    """The argv Claude Code is started with. The first message comes right after the
    executable: `--mcp-config` and `--allowedTools` take several values and would swallow
    anything after them, so they come last; a message starting with "-" gets a leading space
    so it is never read as an option."""
    argv = [executable]
    if first_message:
        argv.append(" " + first_message if first_message.startswith("-") else first_message)
    argv += ["--resume" if resume else "--session-id", str(cli_session_id)]
    if rules is not None:
        argv += ["--append-system-prompt-file", str(rules)]
    if mcp is not None:
        argv += ["--mcp-config", str(mcp)]
        argv += [
            "--allowedTools",
            ",".join(f"mcp__{mcp_server.SERVER_NAME}__{name}" for name in mcp_server.READ_TOOLS),
        ]
    return argv


def start(data: SessionStart) -> ClaudeSession:
    """Open Claude Code in a terminal, in the project's folder, for what `data` asks (D-050)."""
    project, task, folder = _where(data)
    message, title = _first_message(data, task), _title(data, project, task)
    return _launch(project, task, folder, message, title, cols=data.cols, rows=data.rows, preset=data.preset)


def start_new_project(data: NewProjectStart) -> ClaudeSession:
    """Create the project and its folder (missing, or empty), then Claude Code in it (D-051)."""
    folder = Path(data.folder).expanduser()
    if not folder.is_absolute():
        raise TerminalError("Give the folder's full path (for example C:\\Users\\me\\code\\new-app).")
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise TerminalError(f"{folder} already exists and is not empty: pick a new folder.")
    with batch():
        project = projects_core.create(
            ProjectCreate(name=data.name, local_path=str(folder), description_md=data.description)
        )
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TerminalError(f"Cannot create {folder}: {exc}") from exc
        about = f"\n\nWhat it is for:\n{data.description.strip()}" if data.description.strip() else ""
        message = (
            f"This is a new, empty project: “{data.name}”.{about}\n\n"
            "Ask me what you need to know, propose a structure and tools, and set it up once I agree."
        )
        return _launch(
            project,
            None,
            folder,
            message,
            f"Set up {data.name}",
            cols=data.cols,
            rows=data.rows,
            preset="setup",
        )


def resume(cli_session_id: uuid.UUID, cwd: str, cols: int = 120, rows: int = 32) -> ClaudeSession:
    """Reopen a Claude Code conversation in Cairn (`claude --resume`), in its own folder: one
    started outside Cairn, or one of Cairn's that ended. Its project is the one whose local
    folder it is, if any."""
    folder = Path(cwd)
    if not folder.is_dir():
        raise TerminalError(f"The folder {folder} does not exist on this machine.")
    if not transcript_core.transcript_path(str(folder), str(cli_session_id)).is_file():
        raise TerminalError("Claude Code has no conversation with this id in that folder.")
    running = db.session.scalar(
        select(ClaudeSession).where(
            ClaudeSession.cli_session_id == cli_session_id, ClaudeSession.status == "running"
        )
    )
    if running is not None and is_running(running.id):
        return running  # already open in Cairn
    project = projects_core.by_folder(str(folder))
    usage = transcript_core.session_usage(str(folder), str(cli_session_id))
    title = usage.title or (project.name if project else folder.name)
    return _launch(
        project, None, folder, None, title, cols=cols, rows=rows, preset="resume", resume=cli_session_id
    )


def _launch(
    project: Project | None,
    task: Task | None,
    folder: Path,
    message: str | None,
    title: str,
    *,
    cols: int,
    rows: int,
    preset: str,
    resume: uuid.UUID | None = None,
) -> ClaudeSession:
    executable = connections_core.claude_code_path()
    if not executable:
        raise TerminalError(
            "Claude Code was not found on this machine. Install it, or set its path in Accounts."
        )
    cli_session_id = resume or uuid.uuid4()  # names the transcript Claude Code writes (context gauge)

    def build(session: ClaudeSession) -> tuple[list[str], tuple[Path, ...]]:
        rules, mcp = _rules_file(session.id, project), _mcp_config(session.id)
        return command(executable, cli_session_id, message, rules, resume=bool(resume), mcp=mcp), (rules, mcp)

    return open_session(
        kind="claude",
        folder=folder,
        title=title,
        build=build,
        env=_environment(),
        project=project,
        task=task,
        cli_session_id=cli_session_id,
        cols=cols,
        rows=rows,
        meta={"preset": preset},
    )


def open_session(
    *,
    kind: str,
    folder: Path,
    title: str,
    build,
    env: dict[str, str],
    project: Project | None = None,
    task: Task | None = None,
    cli_session_id: uuid.UUID | None = None,
    instance_id: uuid.UUID | None = None,
    port: int | None = None,
    cols: int = 120,
    rows: int = 32,
    meta: dict[str, Any] | None = None,
) -> ClaudeSession:
    """Run a program in a terminal Cairn keeps (D-050, D-053): the session row, the terminal,
    the reader thread, the log and the event. `build(session)` gives the argv and the files
    to remove when it ends (it may need the session's id)."""
    with batch():
        session = ClaudeSession(
            kind=kind,
            project_id=project.id if project else None,
            task_id=task.id if task else None,
            instance_id=instance_id,
            port=port,
            cwd=str(folder),
            cli_session_id=cli_session_id or uuid.uuid4(),
            title=title[:200],
        )
        db.session.add(session)
        db.session.flush()
        argv, files = build(session)
        try:
            pty = Pty.spawn(argv, cwd=str(folder), env=env, cols=cols, rows=rows)
        except OSError as exc:
            for path in files:
                path.unlink(missing_ok=True)
            raise TerminalError(f"{title} could not start: {exc}") from exc
        session.pid = pty.pid
        log_action(
            f"{kind}_session.start",
            target_type="claude_session",
            target_id=session.id,
            meta={"cwd": session.cwd, "task": str(task.id) if task else None, **(meta or {})},
        )
        publish(f"{kind}.changed", {"id": str(session.id), "status": "running"})
    terminal = Terminal(session.id, pty, tuple(files), kind)
    with _lock:
        _terminals[session.id] = terminal
    app = current_app._get_current_object()
    threading.Thread(target=_pump, args=(app, terminal), name=f"{kind}-{session.id}", daemon=True).start()
    return session


def _pump(app: Any, terminal: Terminal) -> None:
    """Read the terminal until it ends, then record how it ended."""
    while True:
        try:
            text = terminal.pty.read()
        except EOFError:
            break
        except OSError:
            break
        if text:
            terminal.append(text)
    terminal.finish()
    code = terminal.pty.exit_code()
    for path in terminal.files:  # the rules and MCP files only live as long as their session
        path.unlink(missing_ok=True)
    with app.app_context(), acting_as("system"):
        _ended(terminal.session_id, code, "")
    with _lock:
        _terminals.pop(terminal.session_id, None)


def _ended(session_id: uuid.UUID, code: int | None, reason: str) -> None:
    with batch():
        session = db.session.get(ClaudeSession, session_id)
        if session is None or session.status == "ended":
            return
        session.status, session.ended_at, session.exit_code, session.end_reason = (
            "ended",
            utcnow(),
            code,
            reason,
        )
        log_action(
            f"{session.kind}_session.end",
            target_type="claude_session",
            target_id=session.id,
            meta={"exit_code": code, "reason": reason},
        )
        publish(f"{session.kind}.changed", {"id": str(session_id), "status": "ended"})


def _remove_session_files(session_id: uuid.UUID) -> None:
    """The rules and MCP files of a session whose reader could not remove them."""
    folder = Path(current_app.config["CAIRN_DATA_DIR"]) / "claude"
    for path in (folder / f"{session_id}.md", folder / f"{session_id}.mcp.json"):
        path.unlink(missing_ok=True)


def write(session_id: uuid.UUID, text: str) -> None:
    terminal = _terminal(session_id)
    if terminal.ended:
        raise TerminalError("This session has ended.")
    terminal.pty.write(text)


def resize(session_id: uuid.UUID, cols: int, rows: int) -> None:
    _terminal(session_id).pty.resize(cols, rows)


def stop(session_id: uuid.UUID) -> None:
    """Close the session (like closing its terminal). Its end is recorded by the reader."""
    _terminal(session_id).pty.kill()


def output(session_id: uuid.UUID, after: int, wait: float = 0.0) -> tuple[list[tuple[int, str]], bool]:
    """Output after `after` (and whether it ended); a session no longer running has none."""
    with _lock:
        terminal = _terminals.get(session_id)
    if terminal is None:
        return [], True
    return terminal.since(after, wait)


# Escape sequences a terminal program prints (colours, cursor moves, titles), to strip them.
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")


def preview(session_id: uuid.UUID, lines: int = 8) -> list[str]:
    """The last lines a terminal printed, as plain text (for a log-like program: an instance;
    a full-screen program such as Claude Code redraws its screen and reads poorly this way)."""
    with _lock:
        terminal = _terminals.get(session_id)
    if terminal is None:
        return []
    with terminal.cond:
        tail = "".join(text for _, text in list(terminal.chunks)[-40:])[-12000:]
    plain = ANSI.sub("", tail).replace("\r\n", "\n")
    shown = [line.rsplit("\r", 1)[-1].rstrip() for line in plain.split("\n")]
    return [line for line in shown if line.strip()][-lines:]


def is_running(session_id: uuid.UUID) -> bool:
    with _lock:
        return session_id in _terminals


def get(session_id: uuid.UUID) -> ClaudeSession:
    session = db.session.get(ClaudeSession, session_id)
    if session is None:
        raise TerminalError("This session does not exist.")
    return session


def sessions(
    *,
    project_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    kind: str = "claude",
    instance_id: uuid.UUID | None = None,
    limit: int = 50,
):
    """Cairn's sessions of one kind, running first, then the most recent. A session recorded
    as running whose terminal is gone (Cairn was restarted) is closed on the way."""
    query = select(ClaudeSession).where(ClaudeSession.deleted_at.is_(None), ClaudeSession.kind == kind)
    if instance_id is not None:
        query = query.where(ClaudeSession.instance_id == instance_id)
    if project_id is not None:
        query = query.where(ClaudeSession.project_id == project_id)
    if task_id is not None:
        query = query.where(ClaudeSession.task_id == task_id)
    rows = list(db.session.scalars(query.order_by(ClaudeSession.created_at.desc()).limit(limit)))
    for row in rows:
        if row.status == "running" and not is_running(row.id):
            with acting_as("system"):
                _ended(row.id, None, "Cairn was restarted while it ran")
            _remove_session_files(row.id)  # its reader died with the old process
    rows.sort(key=lambda r: (r.status != "running", -r.created_at.timestamp()))
    return rows


def running_pids() -> set[int]:
    with _lock:
        return {terminal.pty.pid for terminal in _terminals.values()}
