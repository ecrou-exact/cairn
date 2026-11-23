"""What the owner did in a day, read where it happened (D-078): the commits of every branch of the
repositories on this machine, GitHub (pull requests, issues, commits of repositories not here), the
tasks finished in Cairn and the Claude conversations. Read only: nothing is fetched, nothing changes.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.planning import Project, Task, TimeEntry
from app.core.extensions import db
from app.core.utils.settings import get_setting
from app.features.claude import transcript_core
from app.features.folder import programs

DEPTH = 3
SLOT = 30  # minutes: how finely activity is counted
SKIPPED = {"node_modules", "venv", "vendor", "__pycache__"}
REMOTE = re.compile(r"[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
FORMAT = "%H%x1f%aI%x1f%an%x1f%ae%x1f%ct%x1f%s"
BOTS = ("dependabot/", "renovate/", "pre-commit-ci")


def bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min).astimezone()
    return start, datetime.combine(day + timedelta(days=1), time.min).astimezone()


def repositories() -> list[Path]:
    """The projects' folders, and the repositories found in the folders of the settings."""
    found: dict[Path, None] = {}
    paths = db.session.scalars(
        select(Project.local_path).where(Project.deleted_at.is_(None), Project.local_path.is_not(None))
    )
    for path in paths:
        if path and (Path(path) / ".git").exists():
            found[Path(path).resolve()] = None
    for root in get_setting("recap.folders"):
        _walk(Path(root).expanduser(), DEPTH, found)
    return list(found)


def _walk(folder: Path, depth: int, found: dict[Path, None]) -> None:
    try:
        if (folder / ".git").exists():
            found[folder.resolve()] = None
            return
        if depth:
            for child in sorted(folder.iterdir()):
                hidden = child.name.startswith(".") or child.name in SKIPPED
                if not hidden and child.is_dir() and not child.is_symlink():
                    _walk(child, depth - 1, found)
    except OSError:
        return


def _branch(ref: str) -> str:
    for prefix in ("refs/heads/", "refs/remotes/"):
        if ref.startswith(prefix):
            name = ref.removeprefix(prefix)
            return name.split("/", 1)[-1] if prefix.endswith("remotes/") else name
    return ref.removeprefix("refs/")


def _branch_of(folder: Path, sha: str, written: int) -> str:
    """The branch a commit was made on, as far as git can tell: of those that hold it, the one whose
    last commit is the nearest after it (the others took it later), on this machine first."""
    raw = programs.git(
        folder, "for-each-ref", "--contains", sha,
        "--format=%(committerdate:unix) %(refname)", "refs/heads", "refs/remotes",
    )  # fmt: skip
    found = []
    for line in raw.splitlines():
        tip, _, ref = line.partition(" ")
        name = _branch(ref)
        if name != "HEAD" and not name.startswith(BOTS):
            found.append((abs(int(tip) - written), ref.startswith("refs/remotes/"), name))
    return min(found)[2] if found else ""


def _read_repository(folder: Path, start: datetime, end: datetime, login: str) -> dict[str, Any]:
    remote = REMOTE.search(programs.git(folder, "remote", "get-url", "origin"))
    name = f"{remote[1]}/{remote[2]}" if remote else folder.name
    me = {
        value.lower()
        for value in (
            programs.git(folder, "config", "user.name"),
            programs.git(folder, "config", "user.email"),
            login,
        )
        if value
    }
    # Rebased or amended the same day: git keeps the author's date, so it is looked for wider.
    since = (start - timedelta(days=1)).isoformat()
    raw = programs.git(
        folder,
        "log",
        "--exclude=refs/stash",
        "--all",
        "--no-merges",
        f"--since={since}",
        f"--format={FORMAT}",
    )
    commits = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 6:
            continue
        sha, at, author, email, written, subject = parts
        when = datetime.fromisoformat(at)
        if start <= when < end and (author.lower() in me or email.lower() in me):
            commits.append(
                {
                    "sha": sha,
                    "at": when.isoformat(),
                    "branch": _branch_of(folder, sha, int(written)),
                    "subject": subject,
                }
            )
    return {"repo": name, "github": bool(remote), "folder": str(folder), "commits": commits}


# -- GitHub ------------------------------------------------------------------------------------


def _github(start: datetime, end: datetime) -> dict[str, Any]:
    """Pull requests, issues and commits, with GitHub's own command line signed in by the owner."""
    user = programs.gh("user")
    if not isinstance(user, dict) or not user.get("login"):
        return {"login": "", "read": False, "items": [], "commits": []}
    login = user["login"]
    span = f"{start.isoformat()}..{(end - timedelta(seconds=1)).isoformat()}"
    searches = {
        "pr_opened": ("search/issues", f"author:{login} is:pr created:{span}"),
        "pr_merged": ("search/issues", f"author:{login} is:pr merged:{span}"),
        "issue_opened": ("search/issues", f"author:{login} is:issue created:{span}"),
        "commits": ("search/commits", f"author:{login} author-date:{span}"),
    }
    with ThreadPoolExecutor(4) as pool:
        answers = dict(
            zip(
                searches,
                pool.map(lambda s: programs.gh(s[0], f"q={s[1]}", "per_page=100"), searches.values()),
                strict=True,
            )
        )
    items, commits = [], []
    for kind in ("pr_opened", "pr_merged", "issue_opened"):
        for row in (answers[kind] or {}).get("items", []):
            repo = row["repository_url"].split("/repos/", 1)[-1]
            items.append(
                {
                    "kind": kind,
                    "repo": repo,
                    "number": row["number"],
                    "title": row["title"],
                    "url": row["html_url"],
                }
            )
    for row in (answers["commits"] or {}).get("items", []):
        if len(row.get("parents") or []) > 1:
            continue
        commits.append(
            {
                "repo": row["repository"]["full_name"],
                "sha": row["sha"],
                "at": row["commit"]["author"]["date"].replace("Z", "+00:00"),
                "branch": "",
                "subject": row["commit"]["message"].split("\n", 1)[0],
            }
        )
    return {
        "login": login,
        "read": all(a is not None for a in answers.values()),
        "items": items,
        "commits": commits,
    }


# -- Claude ------------------------------------------------------------------------------------


def _asked(line: bytes) -> tuple[str, datetime] | None:
    """(folder, when) of a request the owner typed; what was said is not kept."""
    if b'"type":"user"' not in line or b'"tool_use_id"' in line:
        return None
    try:
        entry = json.loads(line)
        if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
            return None
        return entry["cwd"], datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def _claude(start: datetime, end: datetime) -> dict[str, list[datetime]]:
    """When the owner asked something to Claude, by folder."""
    found: dict[str, list[datetime]] = defaultdict(list)
    for path in transcript_core.projects_root().glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime < start.timestamp():
                continue
            with path.open("rb") as lines:
                for line in lines:
                    asked = _asked(line)
                    if asked and start <= asked[1] < end:
                        found[asked[0]].append(asked[1])
        except OSError:
            continue
    return found


# -- together ----------------------------------------------------------------------------------


def slot(when: datetime) -> str:
    local = when.astimezone()
    return f"{local.hour:02d}:{local.minute // SLOT * SLOT:02d}"


def _finished(start: datetime, end: datetime) -> list[Task]:
    return list(
        db.session.scalars(
            select(Task)
            .where(Task.deleted_at.is_(None), Task.completed_at >= start, Task.completed_at < end)
            .order_by(Task.completed_at)
        )
    )


def _repo_of(task: Task) -> str:
    return (task.project.github_repo or task.project.name) if task.project else "No project"


def _timed(start: datetime, end: datetime) -> dict[str, set[str]]:
    """The half hours a task's timer ran, by repository."""
    found: dict[str, set[str]] = defaultdict(set)
    query = (
        select(TimeEntry, Task)
        .join(Task, Task.id == TimeEntry.task_id)
        .where(TimeEntry.deleted_at.is_(None), TimeEntry.started_at < end)
        .where((TimeEntry.ended_at.is_(None)) | (TimeEntry.ended_at > start))
    )
    for entry, task in db.session.execute(query):
        at, until = max(entry.started_at, start), min(entry.ended_at or utcnow(), end)
        while at < until:
            found[_repo_of(task)].add(slot(at))
            at += timedelta(minutes=SLOT)
    return found


def short(repo: str) -> str:
    """A repository and its forks are one: the name alone."""
    return repo.rsplit("/", 1)[-1].lower()


def gather(day: date) -> dict[str, Any]:
    """The day by repository, the busiest first."""
    start, end = bounds(day)
    folders = repositories()
    github = _github(start, end)
    with ThreadPoolExecutor(8) as pool:
        read = list(pool.map(lambda f: _read_repository(f, start, end, github["login"]), folders))
    groups: dict[str, dict[str, Any]] = {}

    def group(repo: str) -> dict[str, Any]:
        return groups.setdefault(
            short(repo),
            {
                "name": short(repo),
                "repo": repo,
                "commits": [],
                "items": [],
                "tasks": [],
                "asked": 0,
                "slots": set(),
            },
        )

    seen: set[str] = set()
    same: set[tuple[str, str, str]] = set()
    by_folder: dict[str, str] = {}
    for found in read:
        by_folder[found["folder"]] = found["repo"]
        for commit in found["commits"]:
            _add(group(found["repo"]), commit, found["repo"] if found["github"] else "", seen, same)
    for commit in github["commits"]:
        _add(group(commit["repo"]), commit, commit["repo"], seen, same)
    for item in github["items"]:
        group(item["repo"])["items"].append({k: item[k] for k in ("kind", "number", "title", "url")})
    for task in _finished(start, end):
        row = group(_repo_of(task))
        row["tasks"].append({"id": str(task.id), "title": task.title})
        row["slots"].add(slot(task.completed_at))
    for repo, slots in _timed(start, end).items():
        group(repo)["slots"] |= slots
    places = sorted(by_folder, key=len, reverse=True)
    for cwd, times in _claude(start, end).items():
        place = next((p for p in places if cwd == p or cwd.startswith(p + os.sep)), None)
        if place is not None:
            row = group(by_folder[place])
            row["asked"] += len(times)
            row["slots"] |= {slot(when) for when in times}
    rows = []
    for row in groups.values():
        row["commits"].sort(key=lambda c: c["at"])
        row["slots"] = sorted(row["slots"])
        rows.append(row)
    rows.sort(key=lambda r: (-len(r["slots"]), -len(r["commits"]), r["name"]))
    return {"repos": rows, "github": github["read"], "folders": len(folders)}


def _add(row: dict, commit: dict, github: str, seen: set[str], same: set[tuple[str, str, str]]) -> None:
    """Once, whatever the clones that hold it and the times it was rebased."""
    alike = (row["name"], commit["subject"], datetime.fromisoformat(commit["at"]).astimezone().isoformat())
    if commit["sha"] in seen or alike in same:
        return
    seen.add(commit["sha"])
    same.add(alike)
    url = f"https://github.com/{github}/commit/{commit['sha']}" if github else ""
    row["commits"].append(
        {
            "sha": commit["sha"][:9],
            "branch": commit["branch"],
            "subject": commit["subject"],
            "at": commit["at"],
            "url": url,
        }
    )
    row["slots"].add(slot(datetime.fromisoformat(commit["at"])))
