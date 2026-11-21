"""The project form: HTML fields to schema input and back (links as `label | url` lines)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.db_class.planning import Project
from app.core.utils.web import optional, split_list


def links_from_text(raw: str | None) -> list[dict[str, str]]:
    links = []
    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        label, _, url = line.partition("|")
        if not url:
            label, url = "", label
        links.append({"label": label.strip() or url.strip(), "url": url.strip()})
    return links


def values_from_form(form: Mapping[str, str]) -> dict[str, Any]:
    return {
        "name": form.get("name", ""),
        "slug": optional(form, "slug"),
        "description_md": form.get("description_md", ""),
        "status": form.get("status", "active"),
        "color": form.get("color", "slate"),
        "icon": optional(form, "icon") or "fa-folder",
        "github_repo": optional(form, "github_repo"),
        "default_branch": optional(form, "default_branch") or "main",
        "local_path": optional(form, "local_path"),
        "stack": split_list(form.get("stack")),
        "links": links_from_text(form.get("links")),
        "tags": split_list(form.get("tags")),
        "claude_instructions_md": form.get("claude_instructions_md", ""),
        "weight": form.get("weight") or 1,
    }


def values_from_project(project: Project) -> dict[str, Any]:
    return {
        "name": project.name,
        "slug": project.slug,
        "description_md": project.description_md,
        "status": project.status,
        "color": project.color,
        "icon": project.icon,
        "github_repo": project.github_repo or "",
        "default_branch": project.default_branch,
        "local_path": project.local_path or "",
        "stack": ", ".join(project.stack),
        "links": "\n".join(f"{link['label']} | {link['url']}" for link in project.links),
        "tags": ", ".join(project.tags),
        "claude_instructions_md": project.claude_instructions_md,
        "weight": f"{project.weight:g}",
    }
