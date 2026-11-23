"""The main Claude opens a project's Claude and hands it work (D-068).

Terminals live in the web process, the MCP server does not: the tool writes a request, the web
process opens the session and writes the answer back. Only the main session may ask, and Claude
Code asks the owner first (an `ask` rule holds in every mode, D-064). One already open on a
project is never typed into: a note is left for it instead.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import timedelta

from flask import Flask
from sqlalchemy import select, update

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeRequest, ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.claude import SessionStart
from app.core.utils.actor import acting_as, current_actor
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.core.utils.settings import get_setting
from app.features.claude import main_core

WORK_LIMIT = 7000  # with the preamble, under what a session starts with
STALE = timedelta(seconds=60)  # an older request is refused: nothing opens by surprise later
EVERY = 0.7
PREAMBLE = (
    "Cairn's main Claude hands you this work, approved by the owner. Stay within this project, ask "
    "the owner when something is unclear, and do not commit or push without their go. When you "
    "are done or stuck, tell Cairn with take_note.\n\n"
)


class HandoverError(ValueError):
    pass


def ask(session: ClaudeSession | None, project: Project, task: Task | None, work: str) -> ClaudeRequest:
    """Called by the MCP server, for the main session only."""
    if not main_core.is_main(session):
        raise HandoverError("Only Cairn's main Claude opens the others. Leave it a note with take_note.")
    words = work.strip()
    if not words or len(words) > WORK_LIMIT:
        raise HandoverError(f"Say what the work is, in {WORK_LIMIT} characters at most.")
    if task is not None and task.project_id != project.id:
        raise HandoverError(f"“{task.title}” is not a task of “{project.name}”.")
    if not project.local_path:
        raise HandoverError(f"“{project.name}” has no local folder: the owner sets it in Edit.")
    with batch():
        request = ClaudeRequest(
            project_id=project.id,
            task_id=task.id if task else None,
            work=words,
            created_by=current_actor(),
        )
        db.session.add(request)
        db.session.flush()
        log_action(
            "claude_request.create",
            target_type="claude_request",
            target_id=request.id,
            meta={"project": str(project.id), "task": str(task.id) if task else None},
        )
    return request


def wait(request_id: uuid.UUID, seconds: float = 20.0) -> ClaudeRequest:
    """The request once answered; refused here if nobody answers (Cairn's web server is away)."""
    deadline = time.monotonic() + seconds
    while True:
        db.session.expire_all()
        request = db.session.get(ClaudeRequest, request_id)
        if request.status not in ("pending", "opening"):
            return request
        late = time.monotonic() - deadline
        if late > 0 and request.status == "pending" and _claim(request_id):
            _answer(request_id, "refused", error="Cairn's web server did not answer.")
            return db.session.get(ClaudeRequest, request_id)
        if late > seconds + 20:  # claimed, then nothing: the web process stopped on the way
            return request
        db.session.rollback()  # see what the web process commits
        time.sleep(0.3)


def _claim(request_id: uuid.UUID) -> bool:
    """Take a waiting request: one taker only, so it is never opened twice nor after it was
    given up on."""
    taken = db.session.execute(
        update(ClaudeRequest)
        .where(ClaudeRequest.id == request_id, ClaudeRequest.status == "pending")
        .values(status="opening")
    )
    db.session.commit()
    db.session.expire_all()
    return taken.rowcount == 1


def _answer(
    request_id: uuid.UUID, status: str, session: ClaudeSession | None = None, error: str = ""
) -> None:
    with batch():
        request = db.session.get(ClaudeRequest, request_id)
        if request.status not in ("pending", "opening"):
            return
        request.status, request.error = status, error[:300]
        request.session_id = session.id if session else None
        log_action(
            f"claude_request.{status}",
            target_type="claude_request",
            target_id=request.id,
            meta={"session": str(session.id) if session else None, "error": error[:300]},
        )


def _open(request_id: uuid.UUID) -> None:
    from app.features.claude import terminal_core

    request = db.session.get(ClaudeRequest, request_id)
    if utcnow() - request.created_at > STALE:
        return _answer(request_id, "refused", error="It was asked too long ago.")
    running = [row for row in terminal_core.sessions() if terminal_core.is_running(row.id)]
    here = [row for row in running if row.project_id == request.project_id]
    if here:
        names = ", ".join(row.title for row in here)
        error = f"A Claude is already open on this project ({names}): leave it a note with take_note."
        return _answer(request_id, "refused", error=error)
    limit = int(get_setting("claude.max_open"))
    if len(running) >= limit:
        return _answer(request_id, "refused", error=f"{limit} Claude sessions are already open in Cairn.")
    if not _claim(request_id):
        return None  # given up on meanwhile
    place = {"task_id": request.task_id} if request.task_id else {"project_id": request.project_id}
    preset = "task" if request.task_id else "free"
    data = SessionStart(preset=preset, detail=PREAMBLE + request.work, **place)
    try:
        session = terminal_core.start(data)
    except terminal_core.TerminalError as exc:
        return _answer(request_id, "refused", error=str(exc))
    return _answer(request_id, "opened", session=session)


def serve_pending() -> int:
    """Answer every request waiting; returns how many there were."""
    waiting = list(
        db.session.scalars(
            select(ClaudeRequest.id)
            .where(ClaudeRequest.status == "pending")
            .order_by(ClaudeRequest.created_at)
        )
    )
    for request_id in waiting:
        try:
            _open(request_id)
        except Exception:
            db.session.rollback()
            logging.getLogger("cairn.claude").exception("A handed-over Claude could not open")
            _answer(request_id, "refused", error="Cairn could not open it (see its log).")
    return len(waiting)


def watch(app: Flask) -> None:
    """In the web process: open what the main Claude asks for."""

    def work() -> None:
        while True:
            with app.app_context(), acting_as("system"):
                try:
                    serve_pending()
                except Exception:
                    logging.getLogger("cairn.claude").exception("Requests could not be read")
                    time.sleep(10)
                finally:
                    db.session.remove()
            time.sleep(EVERY)

    threading.Thread(target=work, name="claude-handover", daemon=True).start()
