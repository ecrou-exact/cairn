"""Who started Cairn's MCP server (D-080): a Claude Cairn opened, or one in the owner's own terminal."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

import psutil
from sqlalchemy import select

from app.core.db_class.claude import ClaudeSession
from app.core.extensions import db
from app.features.claude import transcript_core


@dataclass(frozen=True)
class Caller:
    session_id: str | None  # Cairn's, when Cairn opened it
    actor: str
    folder: str


def identify(given: str | None) -> Caller:
    """From the environment Cairn gives its sessions, else from the Claude Code above this process:
    the same server may be set up for every Claude Code of the machine."""
    conversation, folder = None, os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        for process in psutil.Process().parents():
            if transcript_core.is_claude(process, process.name() or ""):
                conversation, folder = transcript_core.registered(process), process.cwd()
                break
    except (psutil.Error, OSError):
        pass
    if given is None and conversation is not None:
        row = db.session.scalar(
            select(ClaudeSession)
            .where(ClaudeSession.cli_session_id == uuid.UUID(conversation))
            .where(ClaudeSession.status == "running", ClaudeSession.kind == "claude")
            .order_by(ClaudeSession.created_at.desc())
        )
        given = str(row.id) if row is not None else None
    return Caller(given, f"claude:{given or conversation or 'outside'}", folder)


def address() -> str:
    host, port = os.environ.get("CAIRN_HOST", "127.0.0.1"), os.environ.get("CAIRN_PORT", "7010")
    return f"http://{host}:{port}"


def cairn_runs() -> bool:
    try:
        with urllib.request.urlopen(f"{address()}/health", timeout=2) as answer:  # noqa: S310  # nosec B310
            return answer.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False
