"""Every copy of a project's repository on the machine (D-081): its folder, its worktrees, its other
clones, each with its branch, what is not committed, its pull request and what runs in it."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.core.db_class.planning import Project
from app.features.claude import claude_core
from app.features.folder import programs
from app.features.instances import found_core, instances_core
from app.features.projects import place_core
from app.features.recap import facts_core

PAGES = 2  # of 100 pull requests, the most recently changed first


def _worktrees(common: Path) -> list[Path]:
    """The other folders of a repository, as git keeps them."""
    found = []
    try:
        for kept in (common / "worktrees").glob("*/gitdir"):
            folder = Path(kept.read_text(encoding="utf-8").strip()).parent
            if folder.is_dir():
                found.append(folder.resolve())
    except OSError:
        pass
    return found


def folders(project: Project, known: list[Path] | None = None) -> list[Path]:
    """The top folders of its copies, its own first."""
    copies = found_core.Copies(project)
    found: dict[Path, None] = {}
    if copies.root is not None and copies.common is not None:
        found[Path(copies.place(str(copies.root))["folder"])] = None
    for folder in facts_core.repositories() if known is None else known:
        git = place_core.git_of(folder)  # another repository inside its folder is not a copy of it
        if git and (git[2] == copies.common or copies.repos & place_core.repositories(git[2])):
            found[git[0]] = None
    for folder in list(found):
        git = place_core.git_of(folder)
        for other in _worktrees(git[2]) if git else []:
            found[other] = None
    return list(found)


def _facts(folder: Path) -> dict[str, Any]:
    _, own, common = place_core.git_of(folder)
    last = programs.git(folder, "log", "-1", "--format=%ct%x1f%s").split("\x1f")
    counts = programs.git(folder, "rev-list", "--left-right", "--count", "HEAD...@{upstream}").split()
    changes = programs.git(folder, "status", "--porcelain", "--untracked-files=normal")
    return {
        "folder": str(folder),
        "name": folder.name,
        "branch": place_core.branch_of(own),
        "worktree": own != common,
        "repos": sorted(place_core.repositories(common)),
        "changes": len(changes.splitlines()),
        "ahead": int(counts[0]) if len(counts) == 2 else None,
        "behind": int(counts[1]) if len(counts) == 2 else None,
        "committed": int(last[0]) if last[0].isdigit() else 0,
        "subject": last[1] if len(last) == 2 else "",
    }


def _pulls(repos: set[str]) -> tuple[list[dict[str, Any]], bool]:
    """The pull requests of the repositories, and whether GitHub answered for each."""
    asked = [(repo, page) for repo in sorted(repos) for page in range(1, PAGES + 1)]
    with ThreadPoolExecutor(6) as pool:
        answers = list(
            pool.map(
                lambda a: programs.gh(
                    f"repos/{a[0]}/pulls",
                    "state=all",
                    "sort=updated",
                    "direction=desc",
                    "per_page=100",
                    f"page={a[1]}",
                ),
                asked,
            )
        )
    found = []
    for answer in answers:
        for row in answer if isinstance(answer, list) else []:
            head = (row["head"].get("repo") or {}).get("full_name") or ""
            state = "merged" if row.get("merged_at") else "draft" if row.get("draft") else row["state"]
            found.append(
                {
                    "number": row["number"],
                    "title": row["title"],
                    "url": row["html_url"],
                    "state": state if row["state"] == "open" or state == "merged" else "closed",
                    "branch": row["head"]["ref"],
                    "head": head.lower(),
                    "base": row["base"]["ref"],
                    "repo": row["base"]["repo"]["full_name"],
                }
            )
    return found, all(isinstance(answer, list) for answer in answers)


def overview(project: Project, *, github: bool = True) -> dict[str, Any]:
    places = folders(project)
    with ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(_facts, places))
    repos = {repo for row in rows for repo in row["repos"]} | (
        {project.github_repo.lower()} if project.github_repo else set()
    )
    pulls, read = _pulls(repos) if github and repos else ([], True)
    outside = found_core.for_project(project)
    ours = [
        (str(Path(item["running"].cwd).resolve()), item)
        for item in instances_core.for_project(project.id)
        if item["running"]
    ]
    claudes = claude_core.outside()
    main = str(places[0]) if places else ""
    for row in rows:
        row["main"] = row["folder"] == main
        mine = [p for p in pulls if p["branch"] == row["branch"] and p["head"] in row["repos"]]
        mine.sort(key=lambda p: (p["state"] not in ("open", "draft"), -p["number"]))
        row["pull"] = mine[0] if mine else None
        row["outside"] = [item for item in outside if item["folder"] == row["folder"]]
        row["ours"] = [
            {"name": item["instance"].name, "session": str(item["running"].id), "ports": item["ports"]}
            for cwd, item in ours
            if Path(cwd).is_relative_to(row["folder"])
        ]
        row["claudes"] = sum(Path(c["cwd"]).is_relative_to(row["folder"]) for c in claudes)
    rows.sort(
        key=lambda r: (
            not r["main"],
            not (r["outside"] or r["ours"] or r["claudes"]),
            not (r["pull"] and r["pull"]["state"] in ("open", "draft")),
            -r["committed"],
        )
    )
    return {"copies": rows, "github": read}
