"""Which project a folder belongs to (D-080), from the files of git alone: the project's folder or
one inside it, one of its worktrees, or another clone of its repository."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select

from app.core.db_class.planning import Project
from app.core.extensions import db

# A submodule or an `insteadOf` has an address too: only the remotes are the repository's.
REMOTE = re.compile(r'^\[remote "[^"\n]+"\][^\[]*?^\s*url\s*=\s*(\S+)', re.M)
ORIGIN = re.compile(r'^\[remote "origin"\][^\[]*?^\s*url\s*=\s*(\S+)', re.M | re.S)
REPO = re.compile(r"[/:]([^/:]+/[^/]+?)(?:\.git)?/?$")


def git_of(folder: Path) -> tuple[Path, Path, Path] | None:
    """(top folder, its git folder, the repository's common git folder) of a folder, or None."""
    for top in (folder, *folder.parents):
        mark = top / ".git"
        try:
            if mark.is_dir():
                return top, mark, mark.resolve()
            if mark.is_file():
                own = Path(mark.read_text(encoding="utf-8").partition("gitdir:")[2].strip())
                own = own if own.is_absolute() else top / own
                common = own / "commondir"
                if common.is_file():
                    return top, own, (own / common.read_text(encoding="utf-8").strip()).resolve()
                return top, own, own.resolve()
        except OSError:
            return None
    return None


def repositories(common: Path) -> set[str]:
    """`owner/name` of every remote, in lower case."""
    try:
        urls = REMOTE.findall((common / "config").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return set()
    return {match[1].lower() for match in map(REPO.search, urls) if match}


def branch_of(own: Path) -> str:
    try:
        head = (own / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return head.removeprefix("ref: refs/heads/") if head.startswith("ref:") else head[:8]


def origin(common: Path) -> str | None:
    """`owner/name` of the repository's own remote on GitHub, as it is written."""
    try:
        found = ORIGIN.search((common / "config").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    url = found[1] if found else ""
    match = REPO.search(url) if "github.com" in url else None
    return match[1] if match else None


def project_for(folder: str) -> Project | None:
    """The project of a folder: the nearest that holds it, else the one whose repository it is a
    worktree of, else the only one it is a clone of (they share a remote: a fork's clone counts)."""
    try:
        path = Path(folder).expanduser().resolve()
    except OSError:
        return None
    projects = list(db.session.scalars(select(Project).where(Project.deleted_at.is_(None))))
    roots = [(Path(p.local_path).expanduser().resolve(), p) for p in projects if p.local_path]
    holding = [(len(root.parts), project) for root, project in roots if path.is_relative_to(root)]
    if holding:
        return max(holding, key=lambda item: item[0])[1]
    git = git_of(path)
    if git is None:
        return None
    # A project in a folder of another's repository is not that repository.
    tops = [(theirs, project) for root, project in roots if (theirs := git_of(root)) and theirs[0] == root]
    for theirs, project in tops:
        if theirs[2] == git[2]:
            return project
    mine = repositories(git[2])
    clones = {p.id: p for p in projects if (p.github_repo or "").lower() in mine}
    clones |= {p.id: p for theirs, p in tops if repositories(theirs[2]) & mine}
    return next(iter(clones.values())) if len(clones) == 1 else None
