"""Where a page is, as a trail of links shown at the top of every page (D-094): the section, then the
project, the parent tasks and the task, then the page itself."""

from __future__ import annotations

import uuid
from typing import Any

from flask import request, url_for

from app.core.db_class.planning import Project, Task
from app.core.extensions import db

SECTIONS = {
    "home": ("Today", "home.index"),
    "tasks": ("Tasks", "tasks.index"),
    "projects": ("Projects", "projects.index"),
    "folder": ("Projects", "projects.index"),
    "worklinks": ("Projects", "projects.index"),
    "graph": ("Projects", "projects.index"),
    "recap": ("Day summary", "recap.index"),
    "instances": ("Instances", "instances.index"),
    "resources": ("Resources", "resources.index"),
    "claude": ("Claude", "claude.index"),
    "changesets": ("Claude", "claude.index"),
    "connections": ("Accounts", "connections.index"),
    "jobs": ("Jobs", "jobs.index"),
    "trash": ("Trash", "trash.index"),
    "settings": ("Settings", "settings.index"),
    "account": ("Account", "account.profile"),
    "about": ("Built with", "about.built_with"),
}
# The page itself, after its section (and its project or task): endpoint → label
PAGES = {
    "projects.new": "New project",
    "projects.edit": "Edit",
    "projects.import_form": "Import",
    "folder.discover": "Find my projects",
    "folder.bring": "Bring in",
    "folder.copies": "Copies",
    "worklinks.github": "A task per pull request",
    "tasks.new": "New task",
    "tasks.edit": "Edit",
    "recap.rules": "Rules",
    "claude.tools": "Tools",
    "claude.live": "Live",
    "changesets.index": "Proposals",
    "changesets.detail": "Proposal",
    "resources.new": "New resource",
    "resources.edit": "Edit",
    "account.security": "Security",
}
TABS = {
    "plan": "Plan",
    "tasks": "Tasks",
    "git": "Git",
    "claude": "Claude",
    "instances": "Instances",
    "about": "About",
}


def _project(slug: str | None) -> Project | None:
    if not slug:
        return None
    return db.session.query(Project).filter(Project.slug == slug, Project.deleted_at.is_(None)).first()


def _task(raw: Any) -> Task | None:
    try:
        found = db.session.get(Task, raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw)))
    except (ValueError, TypeError):
        return None
    return found if found is not None and not found.is_deleted else None


def _with_task(task: Task) -> list[tuple[str, str]]:
    trail: list[tuple[str, str]] = []
    if task.project is not None:
        trail.append((task.project.name, url_for("projects.detail", slug=task.project.slug)))
    chain, parent = [], task.parent_id
    while parent is not None and len(chain) < 10:
        above = db.session.get(Task, parent)
        if above is None:
            break
        chain.append(above)
        parent = above.parent_id
    trail += [(above.title, url_for("tasks.detail", task_id=above.id)) for above in reversed(chain)]
    trail.append((task.title, url_for("tasks.detail", task_id=task.id)))
    return trail


def trail() -> list[tuple[str, str]]:
    """(label, address) from the section to this page; [] where there is nothing to show."""
    endpoint = request.endpoint or ""
    section = SECTIONS.get(request.blueprint or "")
    if section is None or endpoint == section[1]:
        return []
    args = request.view_args or {}
    found = [(section[0], url_for(section[1]))]
    project = _project(args.get("slug"))
    task = _task(args.get("task_id")) if "task_id" in args else None
    if endpoint.startswith("changesets.detail"):
        from app.core.db_class.changeset import Changeset

        changeset = db.session.get(Changeset, args.get("changeset_id"))
        project = (
            db.session.get(Project, changeset.project_id) if changeset and changeset.project_id else None
        )
        found = [("Projects", url_for("projects.index"))] if project else found
    if task is not None:
        found = [
            (
                "Projects" if task.project else "Tasks",
                url_for("projects.index" if task.project else "tasks.index"),
            )
        ]
        found += _with_task(task)
    elif project is not None:
        found = [
            ("Projects", url_for("projects.index")),
            (project.name, url_for("projects.detail", slug=project.slug)),
        ]
    if endpoint == "changesets.detail":
        found.append(("Proposals", url_for("changesets.index")))
    page = PAGES.get(endpoint)
    tab = request.args.get("tab")
    if endpoint in ("projects.detail", "tasks.detail") and tab:
        page = TABS.get(tab, tab.capitalize())
    if page:
        found.append((page, ""))
    return found
