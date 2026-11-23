"""Skills from the library, given to the Claude sessions Cairn opens (D-058).

Each session gets a plugin folder of its own (`claude --plugin-dir`), made from the library's
skills as it opens and removed when it ends: nothing is written in `~/.claude` nor in the
project. A skill attached nowhere goes to every session; one attached to projects or tasks
only to theirs.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from sqlalchemy import select

from app.core.db_class.planning import Project, Task
from app.core.db_class.resource import Resource, ResourceLink
from app.core.extensions import db
from app.core.utils.logger import log_action
from app.features.projects.projects_core import slugify
from app.features.resources import resources_core

PLUGIN = "cairn-skills"  # Claude Code shows them as /cairn-skills:<name>
MAX_BYTES = 20 * 1024 * 1024  # a skill folder larger than this is left out
SKIPPED = {".git", "node_modules", "__pycache__", ".venv"}
FRONT_MATTER = re.compile(r"\A---\r?\n.*?^---\s*$", re.S | re.M)


class SkillError(ValueError):
    pass


def for_session(project: Project | None, task: Task | None) -> list[Resource]:
    wanted = {("project", project.id)} if project else set()
    if task is not None:
        wanted.add(("task", task.id))
    links: dict = {}
    for link in db.session.scalars(
        select(ResourceLink)
        .join(Resource, Resource.id == ResourceLink.resource_id)
        .where(Resource.kind == "skill")
    ):
        links.setdefault(link.resource_id, set()).add((link.target_type, link.target_id))
    skills = db.session.scalars(
        select(Resource)
        .where(Resource.kind == "skill", Resource.deleted_at.is_(None))
        .order_by(Resource.title, Resource.id)
    )
    return [skill for skill in skills if skill.id not in links or links[skill.id] & wanted]


def _text(skill: Resource) -> str:
    """SKILL.md of a skill written in Cairn: its own front matter, or one made from its title."""
    if FRONT_MATTER.match(skill.body):
        return skill.body
    about = " ".join(skill.description_md.split()) or skill.title
    return (
        f"---\nname: {slugify(skill.title)}\ndescription: {json.dumps(about[:1000], ensure_ascii=False)}\n"
        f"---\n\n{skill.body}\n"
    )


def _ignore(folder: str, names: list[str]) -> set[str]:
    """Links are not followed: a skill folder never brings files from elsewhere."""
    return {name for name in names if name in SKIPPED or (Path(folder) / name).is_symlink()}


def _copy(source: Path, target: Path) -> None:
    size, pending = 0, [source]
    while pending:
        folder = pending.pop()
        names = [entry.name for entry in folder.iterdir()]
        left_out = _ignore(str(folder), names)
        for name in names:
            entry = folder / name
            if name in left_out:
                continue
            if entry.is_dir():
                pending.append(entry)
            else:
                size += entry.stat().st_size
        if size > MAX_BYTES:
            raise SkillError("its folder is larger than 20 MB")
    shutil.copytree(source, target, ignore=_ignore)


def write_plugin(folder: Path, skills: list[Resource]) -> Path | None:
    """The plugin folder for these skills (None without any). One that can no longer be read is
    left out and logged: the session opens without it."""
    if not skills:
        return None
    (folder / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (folder / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": PLUGIN, "description": "Skills from Cairn's library", "version": "1.0.0"}),
        encoding="utf-8",
    )
    names: set[str] = set()
    for skill in skills:
        base = slugify(skill.title)
        name, n = base, 2
        while name in names:
            name, n = f"{base}-{n}", n + 1
        target = folder / "skills" / name
        try:
            if skill.path:
                _copy(resources_core.skill_folder(skill.path), target)
            else:
                target.mkdir(parents=True)
                (target / "SKILL.md").write_text(_text(skill), encoding="utf-8")
        except (OSError, shutil.Error, SkillError, resources_core.ResourceError) as exc:
            shutil.rmtree(target, ignore_errors=True)
            log_action(
                "claude_session.skill_left_out",
                target_type="resource",
                target_id=skill.id,
                meta={"reason": str(exc)[:300]},
                level="warning",
            )
            continue
        names.add(name)
    return folder
