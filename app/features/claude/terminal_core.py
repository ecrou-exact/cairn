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

import os
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
from app.core.schema.claude import SessionStart
from app.core.utils.actor import acting_as
from app.core.utils.events import publish
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.features.claude.pty_host import Pty
from app.features.connections import connections_core
from app.features.tasks import brief_core

SCROLLBACK = 2_000_000  # characters of output kept per session for resuming
BRIEF_LIMIT = 24_000  # a first message stays well under Windows' 32k command line
HIDDEN_ENV = ("CLAUDECODE",)  # Cairn may itself run inside Claude Code: the child must not think so


class TerminalError(ValueError):
    pass


@dataclass
class Terminal:
    session_id: uuid.UUID
    pty: Pty
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
    env = {key: value for key, value in os.environ.items() if key not in HIDDEN_ENV}
    env.update({"TERM": "xterm-256color", "COLORTERM": "truecolor"})
    return env


def _first_message(task: Task) -> str:
    brief = brief_core.task_brief(task)
    if len(brief) > BRIEF_LIMIT:
        brief = (
            brief[:BRIEF_LIMIT] + "\n\n[The brief was cut here; the full one is on the task page in Cairn.]"
        )
    return f"I want to work on this task, tracked in Cairn. Here is its brief:\n\n{brief}"


def command(executable: str, cli_session_id: uuid.UUID, first_message: str | None) -> list[str]:
    """The argv Claude Code is started with: its session id (so Cairn finds its transcript)
    and, on a task, the brief as the first message."""
    argv = [executable, "--session-id", str(cli_session_id)]
    if first_message:
        argv.append(first_message)
    return argv


def start(data: SessionStart) -> ClaudeSession:
    """Open Claude Code in a terminal, in the project's folder (D-050)."""
    project, task, folder = _where(data)
    executable = connections_core.claude_code_path()
    if not executable:
        raise TerminalError(
            "Claude Code was not found on this machine. Install it, or set its path in Accounts."
        )
    cli_session_id = uuid.uuid4()  # names the transcript Claude Code writes (context gauge)
    argv = command(executable, cli_session_id, _first_message(task) if data.with_brief and task else None)
    with batch():
        session = ClaudeSession(
            project_id=project.id if project else None,
            task_id=task.id if task else None,
            cwd=str(folder),
            cli_session_id=cli_session_id,
            title=task.title if task else project.name,
        )
        db.session.add(session)
        db.session.flush()
        try:
            pty = Pty.spawn(argv, cwd=str(folder), env=_environment(), cols=data.cols, rows=data.rows)
        except OSError as exc:
            raise TerminalError(f"Claude Code could not start: {exc}") from exc
        session.pid = pty.pid
        log_action(
            "claude_session.start",
            target_type="claude_session",
            target_id=session.id,
            meta={"cwd": session.cwd, "task": str(task.id) if task else None, "brief": bool(data.with_brief)},
        )
        publish("claude.changed", {"id": str(session.id), "status": "running"})
    terminal = Terminal(session.id, pty)
    with _lock:
        _terminals[session.id] = terminal
    app = current_app._get_current_object()
    threading.Thread(target=_pump, args=(app, terminal), name=f"claude-{session.id}", daemon=True).start()
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
            "claude_session.end",
            target_type="claude_session",
            target_id=session.id,
            meta={"exit_code": code, "reason": reason},
        )
        publish("claude.changed", {"id": str(session_id), "status": "ended"})


def write(session_id: uuid.UUID, text: str) -> None:
    terminal = _terminal(session_id)
    if terminal.ended:
        raise TerminalError("This Claude session has ended.")
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


def is_running(session_id: uuid.UUID) -> bool:
    with _lock:
        return session_id in _terminals


def get(session_id: uuid.UUID) -> ClaudeSession:
    session = db.session.get(ClaudeSession, session_id)
    if session is None:
        raise TerminalError("This Claude session does not exist.")
    return session


def sessions(*, project_id: uuid.UUID | None = None, task_id: uuid.UUID | None = None, limit: int = 50):
    """Cairn's sessions, running first, then the most recent. A session recorded as running
    whose terminal is gone (Cairn was restarted) is closed on the way."""
    query = select(ClaudeSession).where(ClaudeSession.deleted_at.is_(None))
    if project_id is not None:
        query = query.where(ClaudeSession.project_id == project_id)
    if task_id is not None:
        query = query.where(ClaudeSession.task_id == task_id)
    rows = list(db.session.scalars(query.order_by(ClaudeSession.created_at.desc()).limit(limit)))
    for row in rows:
        if row.status == "running" and not is_running(row.id):
            with acting_as("system"):
                _ended(row.id, None, "Cairn was restarted while it ran")
    rows.sort(key=lambda r: (r.status != "running", -r.created_at.timestamp()))
    return rows


def running_pids() -> set[int]:
    with _lock:
        return {terminal.pty.pid for terminal in _terminals.values()}
