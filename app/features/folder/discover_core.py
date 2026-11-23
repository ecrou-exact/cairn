"""Every project of the machine, found and started at once (D-088), for a new owner as for one with many
repositories. A job walks the folders of the setting `recap.folders`, groups the git repositories that
are one project (its clones, worktrees and forks), and says for each whether Cairn has it already. The
owner chooses; a second job makes the chosen ones as `/cairn -init` would. Nothing is written in a folder.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.job import Job
from app.core.extensions import db
from app.core.jobs.context import JobContext
from app.core.schema.planning import ProjectCreate
from app.core.utils.history import batch
from app.features.folder import programs
from app.features.projects import place_core, projects_core
from app.features.recap import facts_core

FIND = "projects.discover"
MAKE = "projects.discover_make"
BACKUPS = {"backup", "backups", "old", "archive", "archives"}
MAIN_BRANCHES = ("main", "master", "develop", "development", "dev")
HEADING = re.compile(r"^\s*(#|=|-{3,}|!\[|<|\[!\[|\||```)")


class DiscoverError(ValueError):
    pass


def _short(repo: str) -> str:
    return repo.rsplit("/", 1)[-1].lower()


def _group(folders: list[Path]) -> list[list[dict[str, Any]]]:
    """Folders that are one project: same repository, or a remote of the same name on GitHub."""
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        while parent.setdefault(key, key) != key:
            key = parent[key]
        return key

    def join(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    places = []
    for folder in folders:
        git = place_core.git_of(folder)
        if git is None:
            continue
        repos = place_core.repositories(git[2])
        place = {
            "folder": str(git[0]),
            "branch": place_core.branch_of(git[1]),
            "worktree": git[1] != git[2],
            "repos": sorted(repos),
            "origin": place_core.origin(git[2]),
        }
        places.append(place)
        own = f"dir:{git[2]}"
        for repo in repos:
            join(own, f"name:{_short(repo)}")
        find(own)
    groups: dict[str, list[dict[str, Any]]] = {}
    for place in places:
        common = place_core.git_of(Path(place["folder"]))[2]
        groups.setdefault(find(f"dir:{common}"), []).append(place)
    return list(groups.values())


def _last_commit(folder: str) -> int:
    found = programs.git(Path(folder), "log", "-1", "--format=%ct")
    return int(found) if found.isdigit() else 0


def _main(places: list[dict[str, Any]]) -> dict[str, Any]:
    """The folder worked in: not a worktree nor a backup, the most recent commit, the shortest name."""

    def rank(place: dict[str, Any]) -> tuple:
        backup = any(part.lower() in BACKUPS for part in Path(place["folder"]).parts)
        return (place["worktree"], backup, -_last_commit(place["folder"]), len(Path(place["folder"]).name))

    return min(places, key=rank)


def _mine(places: list[dict[str, Any]], me: set[str]) -> int:
    """When the owner last committed in this project, on any of its copies (0: never)."""
    last = 0
    for place in places:
        for who in me:
            found = programs.git(
                Path(place["folder"]), "log", "--all", "-1", "--format=%ct", f"--author={who}"
            )
            if found.isdigit():
                last = max(last, int(found))
    return last


def _me() -> set[str]:
    """How the owner signs commits: git's own settings and the GitHub sign-in."""
    found = {programs.git(Path.home(), "config", "--global", key) for key in ("user.name", "user.email")}
    user = programs.gh("user")
    if isinstance(user, dict) and user.get("login"):
        found.add(user["login"])
    return {who for who in found if who}


def _about(folder: Path) -> str:
    """The first paragraph of its README."""
    for name in ("README.md", "README.rst", "README", "readme.md"):
        path = folder / name
        try:
            if not path.is_file() or path.is_symlink():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:20_000]
        except OSError:
            continue
        for block in re.split(r"\n\s*\n", text):
            lines = [line.strip() for line in block.strip().splitlines()]
            if lines and not HEADING.match(lines[0]) and len(" ".join(lines)) > 30:
                return " ".join(lines)[:600]
    return ""


def find(context: JobContext | None = None) -> dict[str, Any]:
    folders = facts_core.repositories()
    if context:
        context.log(f"{len(folders)} git folders found in {', '.join(_roots())}.")
        context.progress(20)
    groups = _group(folders)
    me = _me()
    found = []
    for n, places in enumerate(groups, 1):
        main = _main(places)
        project = next((p for p in map(place_core.project_for, (x["folder"] for x in places)) if p), None)
        repo = main["origin"]
        found.append(
            {
                "key": main["folder"],
                "name": _short(repo) if repo else Path(main["folder"]).name,
                "repo": repo,
                "main": main["folder"],
                "branch": main["branch"],
                "copies": [p["folder"] for p in places if p["folder"] != main["folder"]],
                "about": _about(Path(main["folder"])),
                "mine": _mine(places, me),
                "project": {"name": project.name, "slug": project.slug} if project else None,
            }
        )
        if context:
            told = f"already in Cairn as {project.name}" if project else "new"
            context.log(
                f"{found[-1]['name']}: {len(places)} folder{'s' if len(places) != 1 else ''}, {told}."
            )
            context.progress(20 + 80 * n // max(1, len(groups)))
            context.check_cancelled()
    found.sort(key=lambda g: (g["project"] is not None, not g["mine"], g["name"]))
    return {"groups": found, "folders": len(folders)}


def _roots() -> list[str]:
    from app.core.utils.settings import get_setting

    return list(get_setting("recap.folders"))


def _upstream(repo: str | None) -> str | None:
    """The repository a fork was made from: its issues and pull requests are there."""
    about = programs.gh(f"repos/{repo}") if repo else None
    parent = about.get("parent") if isinstance(about, dict) else None
    return parent["full_name"] if parent else repo


def make(keys: list[str], context: JobContext | None = None) -> dict[str, Any]:
    """Start the chosen projects, each once; one already started is left as it is."""
    groups = {g["key"]: g for g in find()["groups"]}
    chosen = [groups[k] for k in keys if k in groups]
    made, skipped = [], []
    for n, group in enumerate(chosen, 1):
        if group["project"] or place_core.project_for(group["main"]):
            skipped.append(group["name"])
            continue
        repo = _upstream(group["repo"])
        values = {
            "name": group["name"][:120],
            "local_path": group["main"],
            "description_md": group["about"],
            "github_repo": repo,
        }
        if group["branch"] in MAIN_BRANCHES:
            values["default_branch"] = group["branch"]
        with batch():
            project = projects_core.create(ProjectCreate(**{k: v for k, v in values.items() if v}))
        made.append({"name": project.name, "slug": project.slug})
        if context:
            context.log(f"Started {project.name} ({repo or group['main']}).")
            context.progress(100 * n // max(1, len(chosen)))
            context.check_cancelled()
    return {"made": made, "skipped": skipped}


def last(job_type: str) -> Job | None:
    return db.session.scalar(select(Job).where(Job.type == job_type).order_by(Job.created_at.desc()).limit(1))
