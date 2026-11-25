"""What the owner did in a day, read where it happened (D-078, D-103): the commits of every branch of
the repositories on this machine and GitHub (pull requests, issues, commits of repositories not here).
Only what the owner wrote counts: not Claude's conversations, not Cairn's tasks or timers. Read only:
nothing is fetched, nothing changes.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.planning import Project
from app.core.extensions import db
from app.core.utils.settings import get_setting
from app.features.folder import programs

DEPTH = 3
SLOT = 30  # minutes: how finely activity is counted
SKIPPED = {"node_modules", "venv", "vendor", "__pycache__"}
REMOTE = re.compile(r"[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
FORMAT = "%H%x1f%aI%x1f%an%x1f%ae%x1f%ct%x1f%s"
PAGE, FOUND = 100, 1000  # results of GitHub's search: by page, and at most for one search
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
    return {"repo": name, "github": bool(remote), "commits": commits}


# -- GitHub ------------------------------------------------------------------------------------


def _search(path: str, query: str, start: datetime, end: datetime) -> tuple[list[dict[str, Any]], bool]:
    """Every result of a search from `start` to `end`, page by page, and whether GitHub gave them all.
    `query` holds `{span}`. Past what one search gives, the time is cut in two."""
    span = f"{start.isoformat()}..{(end - timedelta(seconds=1)).isoformat()}"
    fields = (f"q={query.format(span=span)}", f"per_page={PAGE}")
    answer = programs.gh(path, *fields)
    if not isinstance(answer, dict):
        return [], False
    total = answer.get("total_count", 0)
    if total > FOUND and end - start > timedelta(days=1):
        middle = (start + (end - start) / 2).replace(microsecond=0)
        left, right = _search(path, query, start, middle), _search(path, query, middle, end)
        return left[0] + right[0], left[1] and right[1]
    items, whole = list(answer.get("items", [])), not answer.get("incomplete_results")
    for page in range(2, (min(total, FOUND) - 1) // PAGE + 2):
        more = programs.gh(path, *fields, f"page={page}")
        if not isinstance(more, dict):
            return items, False
        items += more.get("items", [])
        whole = whole and not more.get("incomplete_results")
    return items, whole and len(items) >= total


def _github(start: datetime, end: datetime) -> dict[str, Any]:
    """Pull requests, issues and commits, with GitHub's own command line signed in by the owner."""
    user = programs.gh("user")
    if not isinstance(user, dict) or not user.get("login"):
        return {"login": "", "read": False, "items": [], "commits": []}
    login = user["login"]
    searches = {
        "pr_opened": ("search/issues", f"author:{login} is:pr created:{{span}}"),
        "pr_merged": ("search/issues", f"author:{login} is:pr merged:{{span}}"),
        "issue_opened": ("search/issues", f"author:{login} is:issue created:{{span}}"),
        "commits": ("search/commits", f"author:{login} author-date:{{span}}"),
    }
    with ThreadPoolExecutor(4) as pool:
        answers = dict(
            zip(
                searches,
                pool.map(lambda s: _search(*s, start, end), searches.values()),
                strict=True,
            )
        )
    items, commits = [], []
    for kind in ("pr_opened", "pr_merged", "issue_opened"):
        for row in answers[kind][0]:
            repo = row["repository_url"].split("/repos/", 1)[-1]
            merged = (row.get("pull_request") or {}).get("merged_at") or row.get("closed_at")
            at = merged if kind == "pr_merged" else row["created_at"]
            items.append(
                {
                    "kind": kind,
                    "repo": repo,
                    "at": at.replace("Z", "+00:00"),
                    "number": row["number"],
                    "title": row["title"],
                    "url": row["html_url"],
                }
            )
    for row in answers["commits"][0]:
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
        "read": all(whole for _, whole in answers.values()),
        "items": items,
        "commits": commits,
    }


# -- together ----------------------------------------------------------------------------------


def slot(when: datetime) -> str:
    local = when.astimezone()
    return f"{local.hour:02d}:{local.minute // SLOT * SLOT:02d}"


def short(repo: str) -> str:
    """A repository and its forks are one: the name alone."""
    return repo.rsplit("/", 1)[-1].lower()


def gather(day: date) -> dict[str, Any]:
    return gather_span(day, day)[day]


def gather_span(first: date, last: date) -> dict[date, dict[str, Any]]:
    """Each day from `first` to `last`, by repository, the busiest first. Git and GitHub are read once
    for the whole span (GitHub's search allows few calls a minute)."""
    start, end = bounds(first)[0], bounds(last)[1]
    folders = repositories()
    github = _github(start, end)
    with ThreadPoolExecutor(8) as pool:
        read = list(pool.map(lambda f: _read_repository(f, start, end, github["login"]), folders))
    groups: dict[date, dict[str, dict[str, Any]]] = {}

    def group(repo: str, at: str) -> dict[str, Any]:
        rows = groups.setdefault(datetime.fromisoformat(at).astimezone().date(), {})
        return rows.setdefault(
            short(repo), {"name": short(repo), "repo": repo, "commits": [], "items": [], "slots": set()}
        )

    seen: set[str] = set()
    same: set[tuple[str, str, str]] = set()
    for found in read:
        for commit in found["commits"]:
            row = group(found["repo"], commit["at"])
            _add(row, commit, found["repo"] if found["github"] else "", seen, same)
    for commit in github["commits"]:
        _add(group(commit["repo"], commit["at"]), commit, commit["repo"], seen, same)
    for item in github["items"]:
        row = group(item["repo"], item["at"])
        row["items"].append({k: item[k] for k in ("kind", "number", "title", "url", "at")})
        row["slots"].add(slot(datetime.fromisoformat(item["at"])))
    days = {}
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        rows = list(groups.get(day, {}).values())
        for row in rows:
            row["commits"].sort(key=lambda c: c["at"])
            row["slots"] = sorted(row["slots"])
        rows.sort(key=lambda r: (-len(r["slots"]), -len(r["commits"]), r["name"]))
        days[day] = {"repos": rows, "github": github["read"], "folders": len(folders)}
    return days


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
