"""Every instance running on the machine, by project (D-079): started from Cairn, or anywhere else."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.core.db_class.planning import Project
from app.core.extensions import db
from app.features.instances import found_core, instances_core


def _projects() -> list[Project]:
    return list(
        db.session.scalars(
            select(Project).where(Project.deleted_at.is_(None)).order_by(func.lower(Project.name))
        )
    )


def _matches(words: str, *texts: Any) -> bool:
    return words in " ".join(str(text) for text in texts).lower()


def overview(q: str = "") -> dict[str, Any]:
    """The projects with something running, then what runs in folders that are no project's."""
    words, projects = q.strip().lower(), _projects()
    outside, loose = found_core.everywhere(projects)

    def kept(items: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
        fields = ("copy", "folder", "branch", "label", "where", "ports")
        return [i for i in items if _matches(words, name, *(i[f] for f in fields))]

    groups = []
    for project in projects:
        ours = [
            item
            for item in instances_core.for_project(project.id)
            if item["running"]
            and _matches(words, project.name, item["instance"].name, item["instance"].command, item["ports"])
        ]
        theirs = kept(outside[project.id], project.name)
        if ours or theirs:
            groups.append({"project": project, "ours": ours, "outside": theirs})
    loose = kept(loose, "")
    total = sum(len(g["ours"]) + len(g["outside"]) for g in groups) + len(loose)
    return {"groups": groups, "loose": loose, "total": total}
