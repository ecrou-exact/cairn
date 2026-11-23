"""Work linked to a project, a task or a subtask (D-083): what the owner or a Claude links, and what
Cairn knows already (a task's worktrees and the Claudes opened on it). Each is described from where it
lives (git in the project's copies, GitHub, the conversation), for the pages and for Claude's brief:
a subtask gets its own, its parents' and its project's."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project, Task
from app.core.db_class.worklink import WorkLink
from app.core.db_class.worktree import Worktree
from app.core.extensions import db
from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action
from app.features.folder import copies_core, programs
from app.features.tasks import tasks_core

SHOWN_COMMITS = 5
LABELS = {
    "branch": ("Branch", "fa-code-branch"),
    "commit": ("Commit", "fa-code-commit"),
    "pull": ("Pull request", "fa-code-pull-request"),
    "claude": ("Claude", "fa-claude"),
    "folder": ("Folder", "fa-folder-open"),
}


class WorkLinkError(ValueError):
    pass


def _target(target_type: str, target_id: uuid.UUID) -> Project | Task:
    found = db.session.get(Project if target_type == "project" else Task, target_id)
    if found is None or found.is_deleted:
        raise WorkLinkError(f"This {target_type} does not exist.")
    return found


def _project_of(target: Project | Task) -> Project | None:
    return target if isinstance(target, Project) else target.project


def _changed(link: WorkLink) -> None:
    publish("worklink.changed", {"target": link.target_type, "id": str(link.target_id)})


def add(data: WorkLinkCreate) -> WorkLink:
    _target(data.target_type, data.target_id)
    same = db.session.scalar(
        select(WorkLink).where(
            WorkLink.target_type == data.target_type,
            WorkLink.target_id == data.target_id,
            WorkLink.kind == data.kind,
            WorkLink.ref == data.ref,
            WorkLink.deleted_at.is_(None),
        )
    )
    if same is not None:
        return same
    with batch():
        link = WorkLink(**data.model_dump())
        db.session.add(link)
        db.session.flush()
        log_action(
            "worklink.create",
            target_type=data.target_type,
            target_id=data.target_id,
            diff={"kind": [None, data.kind], "ref": [None, data.ref], "note": [None, data.note]},
            meta={"link": str(link.id)},
        )
        _changed(link)
    return link


def remove(link_id: uuid.UUID) -> WorkLink:
    link = db.session.get(WorkLink, link_id)
    if link is None or link.is_deleted:
        raise WorkLinkError("This link does not exist.")
    with batch():
        link.deleted_at = utcnow()
        log_action(
            "worklink.delete",
            target_type=link.target_type,
            target_id=link.target_id,
            meta={"link": str(link.id)},
        )
        _changed(link)
    return link


def _undo_create(row) -> None:
    link = db.session.get(WorkLink, uuid.UUID(row.meta["link"]))
    if link is not None:
        link.deleted_at = utcnow()
        _changed(link)


def _undo_delete(row) -> None:
    link = db.session.get(WorkLink, uuid.UUID(row.meta["link"]))
    if link is not None:
        link.deleted_at = None
        _changed(link)


register_undo("worklink.create", _undo_create)
register_undo("worklink.delete", _undo_delete)


# -- reading ----------------------------------------------------------------------------------


def _own(target_type: str, target_id: uuid.UUID) -> list[WorkLink]:
    return list(
        db.session.scalars(
            select(WorkLink)
            .where(
                WorkLink.target_type == target_type,
                WorkLink.target_id == target_id,
                WorkLink.deleted_at.is_(None),
            )
            .order_by(WorkLink.created_at)
        )
    )


def _git_facts(project: Project | None, kind: str, ref: str) -> dict[str, Any]:
    """Where the branch or the commit is on the machine, and its last commits."""
    for folder in copies_core.folders(project) if project and project.local_path else []:
        if kind == "branch":
            for name in (ref, f"origin/{ref}", f"fork/{ref}"):
                log = programs.git(
                    folder, "log", f"-{SHOWN_COMMITS}", "--format=%h %ad %s", "--date=short", name, "--"
                )
                if log:
                    return {"folder": str(folder), "commits": log.splitlines(), "found": True}
        else:
            line = programs.git(folder, "show", "-s", "--format=%h %ad %s%n%b", "--date=short", ref)
            if line:
                head, _, body = line.partition("\n")
                return {"folder": str(folder), "commits": [head], "body": body.strip()[:1500], "found": True}
    return {"found": False}


def _pull_facts(project: Project | None, ref: str) -> dict[str, Any]:
    repo, _, number = ref.partition("#")
    repo = repo or (project.github_repo if project else "")
    if not repo:
        return {"found": False}
    found = programs.gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(found, dict) or "number" not in found:
        return {"found": False, "url": f"https://github.com/{repo}/pull/{number}"}
    state = "merged" if found.get("merged_at") else "draft" if found.get("draft") else found["state"]
    return {
        "found": True,
        "title": found["title"],
        "url": found["html_url"],
        "state": state,
        "branch": found["head"]["ref"],
        "base": found["base"]["ref"],
        "body": (found.get("body") or "")[:1500],
    }


def _claude_facts(ref: str) -> dict[str, Any]:
    try:
        key = uuid.UUID(ref)
    except ValueError:
        return {"found": False}
    row = db.session.get(ClaudeSession, key) or db.session.scalar(
        select(ClaudeSession)
        .where(ClaudeSession.cli_session_id == key)
        .order_by(ClaudeSession.created_at.desc())
    )
    if row is None:
        return {"found": False}
    return {
        "found": True,
        "title": row.title,
        "folder": row.cwd,
        "conversation": str(row.cli_session_id),
        "url": f"/claude/sessions/{row.id}",
    }


def describe(kind: str, ref: str, project: Project | None, *, deep: bool = True) -> dict[str, Any]:
    label, icon = LABELS[kind]
    facts: dict[str, Any] = {}
    if deep and kind in ("branch", "commit"):
        facts = _git_facts(project, kind, ref)
    elif deep and kind == "pull":
        facts = _pull_facts(project, ref)
    elif kind == "claude":
        facts = _claude_facts(ref)
    elif kind == "folder":
        facts = {"found": Path(ref).expanduser().is_dir(), "folder": ref}
    return {"kind": kind, "ref": ref, "label": label, "icon": icon, **facts}


def _known(task: Task) -> list[dict[str, Any]]:
    """What Cairn made for the task itself: its worktrees and the Claudes opened on it."""
    found = []
    for tree in db.session.scalars(
        select(Worktree).where(Worktree.task_id == task.id, Worktree.deleted_at.is_(None))
    ):
        found.append({"kind": "branch", "ref": tree.branch, "note": f"its worktree, {tree.path}"})
    for row in db.session.scalars(
        select(ClaudeSession).where(ClaudeSession.task_id == task.id, ClaudeSession.kind == "claude")
    ):
        found.append({"kind": "claude", "ref": str(row.id), "note": "opened on this task"})
    return found


def for_target(target_type: str, target_id: uuid.UUID, *, deep: bool = True) -> dict[str, Any]:
    """Its own links, what Cairn knows already, and what comes from its parents and its project."""
    target = _target(target_type, target_id)
    project = _project_of(target)

    def shown(link: WorkLink | dict, origin: str) -> dict[str, Any]:
        if isinstance(link, WorkLink):
            base = {"id": str(link.id), "kind": link.kind, "ref": link.ref, "note": link.note}
        else:
            base = {"id": None, **link}
        return {**describe(base["kind"], base["ref"], project, deep=deep), **base, "from": origin}

    own = [shown(link, "") for link in _own(target_type, target_id)]
    known, inherited = [], []
    if isinstance(target, Task):
        known = [shown(link, "") for link in _known(target)]
        for parent in tasks_core.ancestors(target):
            inherited += [shown(link, parent.title) for link in _own("task", parent.id)]
        if project is not None:
            inherited += [shown(link, project.name) for link in _own("project", project.id)]
    seen, unique = set(), []
    for item in [*own, *known, *inherited]:
        if (item["kind"], item["ref"]) not in seen:
            seen.add((item["kind"], item["ref"]))
            unique.append(item)
    return {
        "own": [i for i in unique if i["id"] and not i["from"]],
        "known": [i for i in unique if not i["id"]],
        "inherited": [i for i in unique if i["from"] and i["id"]],
    }


def brief_lines(task: Task) -> list[str]:
    """The work linked to a task, for the brief Claude reads."""
    found = for_target("task", task.id)
    lines = []
    for item in [*found["own"], *found["known"], *found["inherited"]]:
        head = f"- {item['label']} `{item['ref']}`"
        extra = [text for text in (item.get("title"), item.get("state"), item.get("note")) if text]
        if item["from"]:
            extra.append(f"from {item['from']}")
        if item.get("folder"):
            extra.append(f"in `{item['folder']}`")
        if item.get("url", "").startswith("http"):
            extra.append(item["url"])
        if item.get("conversation"):
            extra.append(f"conversation {item['conversation']}")
        lines.append(head + (": " + ", ".join(extra) if extra else ""))
        lines += [f"  - {commit}" for commit in item.get("commits", [])]
        if item.get("body"):
            lines.append("  > " + " ".join(item["body"].split())[:600])
    return lines
