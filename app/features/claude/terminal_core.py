"""Claude Code in a terminal inside Cairn (D-050).

The owner's own `claude` runs in a pseudo-terminal, in the project's folder, with the owner's
own sign-in and settings: Cairn does not drive it, it hosts it. One `Terminal` per session,
kept in this (web) process while it runs, so leaving the page does not stop it; its output is
kept (up to `SCROLLBACK` characters) so a page that comes back, or a dropped stream, resumes
where it was.

Only the configured Claude Code executable is ever started (argv list, no shell), in a
folder the owner chose (a project's, or any when free, D-056). Every start and end is logged.
"""

from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
from flask import current_app
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.claude import NewProjectStart, OutsideStop, ResumeStart, SessionLink, SessionStart
from app.core.schema.planning import ProjectCreate
from app.core.utils.actor import acting_as
from app.core.utils.events import publish
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.claude import (
    conversation_view,
    main_core,
    mcp_server,
    session_settings,
    skills_core,
    transcript_core,
    worktrees_core,
)
from app.features.claude.pty_host import Pty
from app.features.connections import connections_core
from app.features.projects import place_core, projects_core
from app.features.tasks import brief_core

CLOSE_WAIT = 10.0  # seconds a Claude Code outside Cairn has to close before a take-over gives up
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
        "WERKZEUG_RUN_MAIN",
        "WERKZEUG_SERVER_FD",
    }
)
# Cairn's own settings never reach a program it starts: CAIRN_SECRET_KEY signs the owner's
# session, CAIRN_MASTER_KEY opens the vault, CAIRN_DATABASE_URL may hold a password (D-064).
HIDDEN_ENV_PREFIXES = ("CAIRN_", "CLAUDE_CODE_CHILD_", "CLAUDE_CODE_SESSION_", "CLAUDE_CODE_MESSAGING_")


class TerminalError(ValueError):
    pass


@dataclass
class Terminal:
    session_id: uuid.UUID
    pty: Pty
    files: tuple[Path, ...] = ()  # removed when the session ends (rules, MCP config, skills)
    kind: str = "claude"
    chunks: deque = field(default_factory=deque)  # (seq, text)
    size: int = 0
    seq: int = 0
    ended: bool = False
    left: bool = False
    reader: threading.Thread | None = None
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


def _existing_folder(text: str) -> Path:
    folder = Path(text).expanduser()
    if not folder.is_absolute():
        raise TerminalError("Give the folder's full path.")
    if not folder.is_dir():
        raise TerminalError(f"The folder {folder} does not exist on this machine.")
    return folder


def _where(data: SessionStart) -> tuple[Project | None, Task | None, Path]:
    if data.folder is not None:
        folder = _existing_folder(data.folder)
        return projects_core.by_folder(str(folder)), None, folder
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
        "icon": "fa-claude",
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
    "fill": {
        "label": "Fill this project in Cairn",
        "icon": "fa-wand-magic-sparkles",
        "asks": "",
        "hint": "Anything to look at first (optional)",
    },
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
    if data.preset == "fill":
        focus = f" Look first at: {words}." if words else ""
        return FILL_MESSAGE + focus
    if data.preset == "review":
        focus = f" Look especially at: {words}." if words else ""
        return (
            "Review the current changes in this repository (git status, git diff, the last commits)."
            f"{focus} Correctness first, then clarity. List what you find by importance; do not change "
            f"code unless I ask.{about}"
        )
    return (words + about) if words else (about.strip() or None)


FILL_MESSAGE = (
    "Fill this project in Cairn with what this folder already says, without changing any file here. "
    "Read: the README and every Markdown file (docs/, doc/, *.md), the configuration (pyproject, "
    "package.json, Dockerfile, compose, CI), the skills (.claude/skills, any SKILL.md), CLAUDE.md, "
    "AGENTS.md, the logos and images (logo*, docs/images, static), the git log and remotes. Then, with "
    "Cairn's tools, each change asked to me: update_project (what it is in a few paragraphs, its stack, "
    "tags, GitHub repository, main branch, its links: site, docs, demo, chat), set_project_logo with "
    "the best square-ish PNG, JPEG, GIF or WebP logo if there is one, add_resource for the documents "
    "and links worth keeping (a note with the essentials of a long doc, never a copy of it). Then "
    "found_in_project: tell me what can be brought in (to-do lists, issues, skills, commands) and give "
    "me its bring_in address, where I choose; skills are taken there, by me. Last, if the folder shows "
    "work to do, propose_changeset with the tasks, in order. Only facts from the files; say what you "
    "did not find."
)


def _title(data: SessionStart, name: str, task: Task | None) -> str:
    words = " ".join(data.detail.split())
    if data.preset == "pr":
        return f"PR {words.rstrip('/').rsplit('/', 1)[-1]}" if "/pull/" in words else "Pull request"
    if data.preset == "fix":
        return f"Fix: {words[:80]}"
    if data.preset == "review":
        return f"Review of {name}"
    if data.preset == "fill":
        return f"Fill {name}"
    return task.title if task is not None else name


def _rules_file(session_id: uuid.UUID, project: Project | None, cwd: str) -> Path:
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
    text += main_core.rules(cwd) + worktrees_core.rules(cwd)
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
                "env": {
                    "CAIRN_MCP_SESSION": str(session_id),
                    "CAIRN_DATA_DIR": str(current_app.config["CAIRN_DATA_DIR"]),
                },
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
    settings: str | None = None,
    skills: Path | None = None,
    add_dir: Path | None = None,
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
    if add_dir is not None:  # takes several values: never before the first message
        argv += ["--add-dir", str(add_dir)]
    if skills is not None:
        argv += ["--plugin-dir", str(skills)]
    if settings is not None:
        argv += ["--settings", settings]
    if mcp is not None:
        argv += ["--mcp-config", str(mcp)]
        argv += [
            "--allowedTools",
            ",".join(
                f"mcp__{mcp_server.SERVER_NAME}__{name}"
                for name in (*mcp_server.READ_TOOLS, *mcp_server.PROPOSAL_TOOLS)
            ),
        ]
    return argv


def start(data: SessionStart) -> ClaudeSession:
    """Open Claude Code in a terminal, in the project's or the given folder, for what `data` asks (D-050)."""
    project, task, folder = _where(data)
    wanted = data.worktree
    if wanted is None:  # on a task, unless the settings say otherwise or it is not a git folder
        wanted = task is not None and get_setting("claude.worktrees") and worktrees_core.is_repository(folder)
    if wanted and project is not None:
        try:
            folder = Path(worktrees_core.open_for(project, task, folder).path)
        except worktrees_core.WorktreeError as exc:
            raise TerminalError(str(exc)) from exc
    message = _first_message(data, task)
    title = _title(data, project.name if project else folder.name or str(folder), task)
    return _launch(project, task, folder, message, title, cols=data.cols, rows=data.rows, preset=data.preset)


def _read_message(name: str) -> str:
    return (
        f"This folder is now the project “{name}” in Cairn. Read it (README, documentation, "
        "configuration, main code, git log) without changing any file. Then fill the project with "
        "Cairn's update_project tool (what it is, its stack, its GitHub repository) and propose the "
        "tasks you see; create them with create_task once I agree."
    )


def link(session_id: uuid.UUID, data: SessionLink) -> tuple[ClaudeSession, ClaudeSession | None]:
    """Link a session to a project, a new one, or none (D-056), at any time. Returns the session
    and, when Claude was asked to read a new project's folder, the session that reads it: a
    separate one, so nothing is ever typed into a conversation in progress."""
    session = get(session_id)
    if session.kind != "claude":
        raise TerminalError("Only a Claude session can be linked.")
    with batch():
        folder = _existing_folder(data.folder or session.cwd)
        if data.name is not None:
            known = projects_core.by_folder(str(folder))
            if known is not None:
                raise TerminalError(f"{folder} is already the folder of “{known.name}”: link to it.")
            project = projects_core.create(ProjectCreate(name=data.name, local_path=str(folder)))
        else:
            project = projects_core.get_project(data.project_id) if data.project_id else None
        before, after = session.project_id, project.id if project else None
        if before != after:
            session.project_id = after
            session.task_id = None  # a task belongs to the project left
            log_action(
                "claude_session.link",
                target_type="claude_session",
                target_id=session.id,
                diff={"project_id": [str(before) if before else None, str(after) if after else None]},
            )
            publish("claude.changed", {"id": str(session.id), "status": session.status})
    if project is None or data.name is None or not data.read:
        return session, None
    reader = _launch(
        project,
        None,
        folder,
        _read_message(project.name),
        f"Read {project.name}",
        cols=120,
        rows=32,
        preset="read",
    )
    return session, reader


def start_new_project(data: NewProjectStart) -> ClaudeSession:
    """Create the project (and its folder when missing), then Claude Code in it (D-051): to set
    it up, or to read it when it has files (D-056)."""
    folder = Path(data.folder).expanduser()
    if not folder.is_absolute():
        raise TerminalError("Give the folder's full path (for example C:\\Users\\me\\code\\new-app).")
    if folder.exists() and not folder.is_dir():
        raise TerminalError(f"{folder} is not a folder.")
    known = projects_core.by_folder(str(folder))
    if known is not None:
        raise TerminalError(f"{folder} is already the folder of “{known.name}”.")
    try:
        has_files = folder.is_dir() and any(folder.iterdir())
    except OSError as exc:
        raise TerminalError(f"Cannot read {folder}: {exc}") from exc
    with batch():
        project = projects_core.create(
            ProjectCreate(name=data.name, local_path=str(folder), description_md=data.description)
        )
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TerminalError(f"Cannot create {folder}: {exc}") from exc
        about = f"\n\nWhat it is for:\n{data.description.strip()}" if data.description.strip() else ""
        if has_files:
            message = _read_message(data.name) + about
        else:
            message = (
                f"This is a new, empty project: “{data.name}”.{about}\n\n"
                "Ask me what you need to know, propose a structure and tools, and set it up once I agree."
            )
        return _launch(
            project,
            None,
            folder,
            message,
            f"Read {data.name}" if has_files else f"Set up {data.name}",
            cols=data.cols,
            rows=data.rows,
            preset="setup",
        )


def stop_outside(data: OutsideStop) -> None:
    """Close a Claude Code running outside Cairn (D-056)."""
    for found in transcript_core.outside_sessions(running_pids()):
        if found["pid"] == data.pid and abs(found["started"] - data.started) < 1:
            _close_outside([data.pid], found["cli_session_id"], "stop_outside")
            publish("claude.changed", {"id": f"pid-{data.pid}", "status": "ended"})
            db.session.commit()
            return
    raise TerminalError("This Claude Code is no longer running.")


def view_outside(data: OutsideStop) -> ClaudeSession:
    """Read, in a terminal, the conversation of a Claude Code running outside Cairn, as it goes
    (D-075): the view already open on it, or a new one. Nothing typed there reaches it."""
    found = next(
        (
            s
            for s in transcript_core.outside_sessions(running_pids())
            if s["pid"] == data.pid and abs(s["started"] - data.started) < 1
        ),
        None,
    )
    if found is None:
        raise TerminalError("This Claude Code is no longer running.")
    conversation = found["cli_session_id"]
    path = transcript_core.transcript_path(found["cwd"], conversation) if conversation else None
    if path is None or not path.is_file():
        raise TerminalError("Nothing was said in this conversation yet.")
    for row in sessions(kind="log"):
        if row.cli_session_id == uuid.UUID(conversation) and is_running(row.id):
            return row
    return open_session(
        kind="log",
        folder=Path(found["cwd"]),
        title=f"Claude · {found['usage']['title'] or Path(found['cwd']).name}",
        build=lambda session: (
            [sys.executable, str(Path(conversation_view.__file__).resolve()), str(path)],
            (),
        ),
        env=_environment(),
        project=place_core.project_for(found["cwd"]),
        cli_session_id=uuid.UUID(conversation),
        meta={"conversation": conversation, "pid": data.pid},
    )


def _close_outside(pids: list[int], conversation: str | None, action: str) -> None:
    """Close Claude Code processes running outside Cairn. Refused when Cairn itself was started
    from one of them: closing it would stop Cairn."""
    if transcript_core.own_ancestors().intersection(pids):
        raise TerminalError(
            "Cairn was started from this Claude Code session: closing it would stop Cairn. "
            "Start Cairn from your own terminal first."
        )
    for pid in pids:
        try:
            background = transcript_core.in_background(psutil.Process(pid))
        except psutil.Error:
            continue
        if background:
            raise TerminalError("It runs in the background of Claude Code: stop it from there.")
        if transcript_core.holds_background(pid):
            raise TerminalError(
                "A background conversation at work depends on this Claude Code: closing it would stop it. "
                "Wait for it to finish."
            )
    processes = []
    for pid in pids:
        try:
            process = psutil.Process(pid)
            process.terminate()
            processes.append(process)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            raise TerminalError(f"Cannot close the other Claude Code (pid {pid}).") from exc
    _, alive = psutil.wait_procs(processes, timeout=CLOSE_WAIT)
    if alive:
        raise TerminalError(f"The other Claude Code (pid {alive[0].pid}) did not close: close it yourself.")
    with batch():  # recorded even if the reopening fails
        log_action(
            f"claude_session.{action}",
            target_type="claude_session",
            meta={"cli_session_id": conversation, "pids": pids},
        )


def _last_link(cli_session_id: uuid.UUID) -> tuple[Project | None, Task | None] | None:
    """What this conversation was last linked to in Cairn (None: it never ran here)."""
    last = db.session.scalar(
        select(ClaudeSession)
        .where(ClaudeSession.cli_session_id == cli_session_id, ClaudeSession.kind == "claude")
        .order_by(ClaudeSession.created_at.desc())
        .limit(1)
    )
    if last is None:
        return None
    project = db.session.get(Project, last.project_id) if last.project_id else None
    task = db.session.get(Task, last.task_id) if last.task_id else None
    return (
        project if project and not project.is_deleted else None,
        task if task and not task.is_deleted else None,
    )


def resume(data: ResumeStart) -> ClaudeSession:
    """Reopen a Claude Code conversation in Cairn (`claude --resume`), in its own folder: one
    started outside Cairn, or one of Cairn's that ended. Its project is the one whose local
    folder it is, if any. Two Claude Codes on one conversation do not see each other's turns:
    one open outside Cairn is closed first (`take_over`), or the request is refused."""
    cli_session_id, folder = data.cli_session_id, Path(data.cwd)
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
    elsewhere = transcript_core.open_elsewhere(str(cli_session_id), running_pids())
    if elsewhere and not data.take_over:
        raise TerminalError(
            f"This conversation is open in another terminal (pid {elsewhere[0]}). Close it there, "
            "or move it here from its card on the Claude page."
        )
    if elsewhere:
        _close_outside(elsewhere, str(cli_session_id), "take_over")
    project, task = _last_link(cli_session_id) or (place_core.project_for(str(folder)), None)
    usage = transcript_core.session_usage(str(folder), str(cli_session_id))
    title = usage.title or (project.name if project else folder.name)
    return _launch(
        project,
        task,
        folder,
        None,
        title,
        cols=data.cols,
        rows=data.rows,
        preset="resume",
        resume=cli_session_id,
    )


def open_claude(
    folder: Path,
    title: str,
    *,
    preset: str,
    resume: uuid.UUID | None = None,
    add_dir: Path | None = None,
) -> ClaudeSession:
    """Claude Code in a folder of Cairn's own, free of any project."""
    return _launch(
        None, None, folder, None, title, cols=120, rows=32, preset=preset, resume=resume, add_dir=add_dir
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
    add_dir: Path | None = None,
) -> ClaudeSession:
    executable = connections_core.claude_code_path()
    if not executable:
        raise TerminalError(
            "Claude Code was not found on this machine. Install it, or set its path in Accounts."
        )
    cli_session_id = resume or uuid.uuid4()  # names the transcript Claude Code writes (context gauge)

    def build(session: ClaudeSession) -> tuple[list[str], tuple[Path, ...]]:
        rules, mcp = _rules_file(session.id, project, session.cwd), _mcp_config(session.id)
        skills = skills_core.write_plugin(
            rules.with_name(f"{session.id}-skills"), skills_core.for_session(project, task)
        )
        argv = command(
            executable,
            cli_session_id,
            message,
            rules,
            resume=bool(resume),
            mcp=mcp,
            settings=session_settings.settings_json(session.cwd),
            skills=skills,
            add_dir=add_dir,
        )
        return argv, (rules, mcp, *([skills] if skills else []))

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
    spawn=None,
) -> ClaudeSession:
    """Run a program in a terminal Cairn keeps (D-050, D-053): the session row, the terminal,
    the reader thread, the log and the event. `build(session)` gives the argv and the files
    to remove when it ends (it may need the session's id). `spawn(session, argv, **options)`
    starts it otherwise than in a terminal of this process (an instance that survives, D-070)."""
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
            options = {"cwd": str(folder), "env": env, "cols": cols, "rows": rows}
            pty = spawn(session, argv, **options) if spawn else Pty.spawn(argv, **options)
        except OSError as exc:
            for path in files:
                _remove(path)
            raise TerminalError(f"{title} could not start: {exc}") from exc
        session.pid = pty.pid
        log_action(
            f"{kind}_session.start",
            target_type="claude_session",
            target_id=session.id,
            meta={"cwd": session.cwd, "task": str(task.id) if task else None, **(meta or {})},
        )
        publish(f"{kind}.changed", {"id": str(session.id), "status": "running"})
    _follow(Terminal(session.id, pty, tuple(files), kind))
    return session


def reattach(session: ClaudeSession, pty: Any) -> None:
    """Follow again a program that outlived a restart of Cairn (D-070)."""
    if not is_running(session.id):
        _follow(Terminal(session.id, pty, (), session.kind))


def _follow(terminal: Terminal) -> None:
    app = current_app._get_current_object()
    terminal.reader = threading.Thread(
        target=_pump, args=(app, terminal), name=f"{terminal.kind}-{terminal.session_id}", daemon=True
    )
    with _lock:
        _terminals[terminal.session_id] = terminal
    terminal.reader.start()


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
    if terminal.left:  # it goes on: Cairn only stops following it
        with _lock:
            _terminals.pop(terminal.session_id, None)
        return
    code = terminal.pty.exit_code()
    for path in terminal.files:  # the rules, MCP file and skills only live as long as their session
        _remove(path)
    with app.app_context(), acting_as("system"):
        record_end(terminal.session_id, code, "")
    with _lock:
        _terminals.pop(terminal.session_id, None)


def record_end(session_id: uuid.UUID, code: int | None, reason: str) -> None:
    """Close a session's row, with how it ended."""
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


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def _remove_session_files(session_id: uuid.UUID) -> None:
    """The rules, MCP file and skills of a session whose reader could not remove them."""
    folder = Path(current_app.config["CAIRN_DATA_DIR"]) / "claude"
    for name in (f"{session_id}.md", f"{session_id}.mcp.json", f"{session_id}-skills"):
        _remove(folder / name)


def write(session_id: uuid.UUID, text: str) -> None:
    terminal = _terminal(session_id)
    if terminal.ended:
        raise TerminalError("This session has ended.")
    try:
        terminal.pty.write(text)
    except OSError as exc:
        raise TerminalError("This program no longer takes keys.") from exc


def resize(session_id: uuid.UUID, cols: int, rows: int) -> None:
    try:
        _terminal(session_id).pty.resize(cols, rows)
    except OSError as exc:
        raise TerminalError("This program has just ended.") from exc


def stop(session_id: uuid.UUID) -> None:
    """Close the session (like closing its terminal). Its end is recorded by the reader."""
    _terminal(session_id).pty.kill()


def close_all(wait: float = 10.0, *, survivors: bool = False) -> None:
    """Stop every terminal and let its reader record the end; an instance that survives Cairn is
    only left (`survivors`: stopped too). Run when Cairn exits, too: an
    interpreter ending while readers still wait for output can hang on their buffers."""
    with _lock:
        terminals = list(_terminals.values())
    for terminal in terminals:  # one at a time: each reader writes its session's end
        if getattr(terminal.pty, "survives", False) and not survivors:
            terminal.left = True
            terminal.pty.leave()
        else:
            terminal.pty.kill()
        if terminal.reader is not None:
            terminal.reader.join(wait)


atexit.register(close_all)


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
                record_end(row.id, None, "Cairn was restarted while it ran")
            _remove_session_files(row.id)  # its reader died with the old process
    rows.sort(key=lambda r: (r.status != "running", -r.created_at.timestamp()))
    return rows


def running_pids(kind: str | None = None) -> set[int]:
    with _lock:
        return {t.pty.pid for t in _terminals.values() if kind is None or t.kind == kind}
