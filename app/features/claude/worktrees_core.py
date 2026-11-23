"""A git worktree per Claude (D-077): its own folder and branch, so that several work on one
project without getting in each other's way. Made when a session opens on a task (or when asked),
used again for the same task, removed only by the owner: never with changes not committed, never
while a Claude is open in it, and the branch always stays.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import uuid
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.db_class.worktree import Worktree
from app.core.extensions import db
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.features.projects.projects_core import slugify

TIMEOUT = 60


class WorktreeError(ValueError):
    pass


def _git(folder: Path, *args: str) -> str:
    from app.features.claude import terminal_core  # it builds on this module

    git = shutil.which("git")
    if git is None:
        raise WorktreeError("git was not found on this machine.")
    env = {**terminal_core._environment(), "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
    try:
        done = subprocess.run(  # noqa: S603  # nosec B603
            [git, "-C", str(folder), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorktreeError(f"git did not answer: {exc}") from exc
    if done.returncode:
        raise WorktreeError((done.stderr.strip().splitlines() or ["git failed"])[-1][:300])
    return done.stdout.strip()


def is_repository(folder: Path) -> bool:
    """A git folder with at least one commit."""
    try:
        return bool(_git(folder, "rev-parse", "--verify", "--quiet", "HEAD"))
    except WorktreeError:
        return False


def _root() -> Path:
    path = Path(current_app.config["CAIRN_DATA_DIR"]).resolve() / "worktrees"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _exists(folder: Path, branch: str) -> bool:
    try:
        _git(folder, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
    except WorktreeError:
        return False
    return True


def _free_name(project: Project, folder: Path, wanted: str) -> tuple[str, Path]:
    place = _root() / project.slug
    place.mkdir(exist_ok=True)
    for n in range(1, 100):
        branch = wanted if n == 1 else f"{wanted}-{n}"
        path = place / branch.replace("/", "-")
        if not path.exists() and not _exists(folder, branch):
            return branch, path
    raise WorktreeError("Too many worktrees of this name: remove some.")


def live(project_id: uuid.UUID) -> list[Worktree]:
    return list(
        db.session.scalars(
            select(Worktree)
            .where(Worktree.project_id == project_id, Worktree.deleted_at.is_(None))
            .order_by(Worktree.created_at.desc())
        )
    )


def for_path(path: str) -> Worktree | None:
    return db.session.scalar(select(Worktree).where(Worktree.path == path, Worktree.deleted_at.is_(None)))


def open_for(project: Project, task: Task | None, folder: Path) -> Worktree:
    """The task's worktree, or a new one from the project's main branch."""
    if task is not None:
        for known in live(project.id):
            if known.task_id == task.id and Path(known.path).is_dir():
                return known
    if not is_repository(folder):
        raise WorktreeError(f"{folder} is not a git repository with a commit: no worktree can be made.")
    kind = re.sub(r"[^a-z0-9-]", "", task.type) if task is not None else "claude"
    name = slugify(task.title)[:50].strip("-") if task is not None else uuid.uuid4().hex[:8]
    branch, path = _free_name(project, folder, f"{kind or 'task'}/{name}")
    base = project.default_branch if _exists(folder, project.default_branch) else "HEAD"
    _git(folder, "worktree", "add", "-q", "-b", branch, "--", str(path), base)
    with batch():
        made = Worktree(
            project_id=project.id,
            task_id=task.id if task else None,
            path=str(path),
            branch=branch,
            base=base,
            created_by=current_actor(),
        )
        db.session.add(made)
        db.session.flush()
        log_action(
            "worktree.create",
            target_type="worktree",
            target_id=made.id,
            meta={"branch": branch, "base": base, "path": str(path)},
        )
    return made


def _in_use(path: str) -> list[ClaudeSession]:
    from app.features.claude import terminal_core

    rows = db.session.scalars(
        select(ClaudeSession).where(ClaudeSession.cwd == path, ClaudeSession.status == "running")
    )
    return [row for row in rows if terminal_core.is_running(row.id)]


def describe(row: Worktree) -> dict[str, Any]:
    path = Path(row.path)
    task = db.session.get(Task, row.task_id) if row.task_id else None
    told: dict[str, Any] = {
        "id": str(row.id),
        "branch": row.branch,
        "base": row.base,
        "path": row.path,
        "task": {"id": str(task.id), "title": task.title} if task and not task.is_deleted else None,
        "here": path.is_dir(),
        "changes": 0,
        "commits": 0,
        "behind": 0,
        "running": [{"id": str(s.id), "title": s.title} for s in _in_use(row.path)],
    }
    if told["here"]:
        try:
            told["changes"] = len(_git(path, "status", "--porcelain").splitlines())
            if row.base != "HEAD":
                counts = _git(path, "rev-list", "--left-right", "--count", f"{row.base}...HEAD").split()
                told["behind"], told["commits"] = int(counts[0]), int(counts[1])
        except (WorktreeError, ValueError, IndexError):
            told["here"] = False
    return told


def for_project(project_id: uuid.UUID) -> list[dict[str, Any]]:
    return [describe(row) for row in live(project_id)]


def remove(worktree_id: uuid.UUID) -> Worktree:
    """Remove the folder; its branch and commits stay in the repository."""
    row = db.session.get(Worktree, worktree_id)
    if row is None or row.is_deleted:
        raise WorktreeError("This worktree does not exist.")
    if _in_use(row.path):
        raise WorktreeError("A Claude is open in it: stop it first.")
    path = Path(row.path)
    if path.is_dir():
        if not path.resolve().is_relative_to(_root()):
            raise WorktreeError("This folder is not one Cairn made.")
        if _git(path, "status", "--porcelain"):
            raise WorktreeError("It has changes that are not committed: commit or discard them first.")
        project = db.session.get(Project, row.project_id)
        main = Path(project.local_path).expanduser() if project and project.local_path else path
        _git(main, "worktree", "remove", "--", str(path))  # never --force
    with batch():
        row.deleted_at = utcnow()
        log_action(
            "worktree.remove",
            target_type="worktree",
            target_id=row.id,
            meta={"branch": row.branch, "path": row.path},
        )
        publish("claude.changed", {"id": str(row.id), "status": "worktree"})
    return row


RULES = """

You work in a git worktree of your own: {path}, on the branch {branch}. Other Claudes may be at work
in the project's main folder or in other worktrees: stay in this one, do not switch branch, and do
not commit, merge or push without the owner's go. Files git ignores (a virtual environment, .env)
are not here.
"""


def rules(cwd: str) -> str:
    row = for_path(cwd)
    return RULES.format(path=row.path, branch=row.branch) if row is not None else ""
