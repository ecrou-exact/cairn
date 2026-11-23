"""What a project already has that Cairn can take (D-081): to-do lists in its files, GitHub's issues and
boards, its skills, the commands that run it. Read only, and only text: nothing found is run. The owner
chooses; tasks come as a proposal they review, a skill is shown in full before it is taken."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.changesets import MAX_ITEMS, ChangesetCreate
from app.core.schema.instances import InstanceCreate
from app.core.schema.resources import LinkCreate, ResourceCreate
from app.core.utils.history import batch
from app.features.changesets import changesets_core
from app.features.folder import programs
from app.features.instances import instances_core
from app.features.resources import resources_core

MAX_FILE = 200_000
MAX_FOUND = 300  # of each kind
TODO_NAME = re.compile(r"^(to[-_ ]?do|roadmap|backlog|tasks?|plan)s?([-_. ].*)?$", re.I)
TODO_SUFFIXES = {".md", ".markdown", ".txt", ".org", ".rst", ""}
PLACES = (".", "docs", "doc", ".github", "notes")
ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(?:\[( |x|X|-)\]\s+)?(.+?)\s*$")
BOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[[ xX-]\]\s", re.M)
NAME = re.compile(r"^name:\s*(.+)$", re.M)
ABOUT = re.compile(r"^description:\s*(.+)$", re.M)
BOARDS = """query($owner:String!,$name:String!){repository(owner:$owner,name:$name){projectsV2(first:5){nodes{
title items(first:100){nodes{isArchived content{__typename ... on DraftIssue{title body}
... on Issue{title url state}}}}}}}}"""


class ScanError(ValueError):
    pass


def _key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]


def _text(path: Path, root: Path) -> str:
    """A file of the project, never one a link leads to elsewhere."""
    try:
        if not path.is_file() or not path.resolve().is_relative_to(root) or path.stat().st_size > MAX_FILE:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _todo_files(root: Path) -> list[Path]:
    found = []
    for place in PLACES:
        try:
            for path in sorted((root / place).iterdir()):
                if path.suffix.lower() in TODO_SUFFIXES and TODO_NAME.match(path.stem):
                    found.append(path)
        except OSError:
            continue
    readme = next((p for p in (root / "README.md", root / "readme.md") if p.is_file()), None)
    return [*found, *([readme] if readme else [])]


def _todos(root: Path) -> list[dict[str, Any]]:
    found = []
    for path in _todo_files(root):
        text = _text(path, root)
        boxes = bool(BOX.search(text))
        if path.stem.lower() == "readme" and not boxes:
            continue
        heading, fenced = "", False
        for line in text.splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            if fenced:
                continue
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                continue
            match = ITEM.match(line)
            if match is None or (boxes and match[2] is None) or (match[2] or "").lower() == "x":
                continue
            file = str(path.relative_to(root))
            title = match[3].strip("*_` ")[:200]
            if title:
                found.append(
                    {"key": _key("todo", file, title), "title": title, "file": file, "under": heading}
                )
    return list({item["key"]: item for item in found}.values())[:MAX_FOUND]


def _issues(repo: str) -> list[dict[str, Any]] | None:
    answer = programs.gh(f"repos/{repo}/issues", "state=open", "per_page=100")
    if not isinstance(answer, list):
        return None
    return [
        {
            "key": _key("issue", row["html_url"]),
            "title": row["title"][:200],
            "url": row["html_url"],
            "number": row["number"],
            "labels": [label["name"] for label in row.get("labels", [])],
            "mine": any(True for _ in row.get("assignees") or []),
        }
        for row in answer
        if "pull_request" not in row
    ]


def _boards(repo: str) -> list[dict[str, Any]] | None:
    """The open cards of the repository's GitHub projects; None when the sign-in may not read them."""
    owner, _, name = repo.partition("/")
    answer = programs.gh("graphql", f"query={BOARDS}", f"owner={owner}", f"name={name}", method="POST")
    try:
        boards = answer["data"]["repository"]["projectsV2"]["nodes"]
    except (KeyError, TypeError):
        return None
    found = []
    for board in boards:
        for card in board["items"]["nodes"]:
            content = card.get("content") or {}
            if card.get("isArchived") or not content.get("title") or content.get("state") == "CLOSED":
                continue
            url = content.get("url", "")
            key = _key("issue", url) if url else _key("card", board["title"], content["title"])
            found.append({"key": key, "title": content["title"][:200], "url": url, "under": board["title"]})
    return found[:MAX_FOUND]


def _skills(root: Path) -> list[dict[str, Any]]:
    found = []
    for path in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        text = _text(path, root)
        if text:
            name, about = NAME.search(text), ABOUT.search(text)
            found.append(
                {
                    "key": _key("skill", str(path)),
                    "name": (name[1] if name else path.parent.name).strip("\"' ")[:200],
                    "about": (about[1] if about else "").strip("\"' ")[:1000],
                    "folder": str(path.parent),
                    "text": text,
                }
            )
    return found


def _commands(root: Path) -> list[dict[str, Any]]:
    """The commands its own files give to run it."""
    found: list[tuple[str, str, str]] = []
    try:
        scripts = json.loads(_text(root / "package.json", root) or "{}").get("scripts", {})
        found += [
            (name, f"npm run {name}", "package.json") for name in scripts if name in ("dev", "start", "serve")
        ]
    except (ValueError, AttributeError, TypeError):
        pass
    for line in _text(root / "Procfile", root).splitlines():
        name, _, command = line.partition(":")
        if command.strip() and re.fullmatch(r"[\w-]{1,40}", name):
            found.append((name, command.strip(), "Procfile"))
    if any((root / name).is_file() for name in ("compose.yml", "compose.yaml", "docker-compose.yml")):
        found.append(("compose", "docker compose up", "compose file"))
    try:
        scripts = tomllib.loads(_text(root / "pyproject.toml", root)).get("project", {}).get("scripts", {})
        runner = (
            "uv run"
            if (root / "uv.lock").is_file()
            else "poetry run"
            if (root / "poetry.lock").is_file()
            else ""
        )
        found += [
            (n, f"{runner} {n}".strip(), "pyproject.toml") for n in scripts if n in ("start", "serve", "run")
        ]
    except (tomllib.TOMLDecodeError, AttributeError, TypeError):
        pass
    return [
        {"key": _key("command", name, command), "name": name, "command": command[:1000], "file": file}
        for name, command, file in found
    ]


def scan(project: Project, *, github: bool = True) -> dict[str, Any]:
    """What is there and not in Cairn yet."""
    root = Path(project.local_path).expanduser().resolve() if project.local_path else None
    root = root if root is not None and root.is_dir() else None
    issues = _issues(project.github_repo) if github and project.github_repo else []
    boards = _boards(project.github_repo) if github and project.github_repo else []
    listed = {issue["key"] for issue in issues or []}
    known = {
        " ".join(title.lower().split())
        for title in db.session.scalars(
            db.select(Task.title).where(Task.project_id == project.id, Task.deleted_at.is_(None))
        )
    }
    have = {r.path for _, r in resources_core.for_target("project", project.id) if r.kind == "skill"}
    commands = {item["instance"].command for item in instances_core.for_project(project.id)}

    def new(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in items if " ".join(item["title"].lower().split()) not in known]

    return {
        "todos": new(_todos(root)) if root else [],
        "issues": new(issues or []),
        "issues_read": issues is not None,
        "cards": new([card for card in boards or [] if card["key"] not in listed]),
        "boards_read": boards is not None,
        "skills": [s for s in _skills(root) if s["folder"] not in have] if root else [],
        "commands": [c for c in _commands(root) if c["command"] not in commands] if root else [],
        "notes": [n for n in ("CLAUDE.md", "AGENTS.md") if root and (root / n).is_file()],
    }


def bring(project: Project, keys: list[str]) -> dict[str, Any]:
    """Take what the owner chose: the tasks as a proposal to review, the rest at once."""
    chosen, found = set(keys), scan(project)
    tasks = [i for kind in ("todos", "issues", "cards") for i in found[kind] if i["key"] in chosen]
    skills = [i for i in found["skills"] if i["key"] in chosen]
    commands = [i for i in found["commands"] if i["key"] in chosen]
    if not (tasks or skills or commands):
        raise ScanError("Choose something that is still there.")
    if len(tasks) > MAX_ITEMS:
        raise ScanError(f"At most {MAX_ITEMS} tasks at a time: take the others next.")
    link = LinkCreate(target_type="project", target_id=project.id)
    changeset = None
    if tasks:
        data = ChangesetCreate.model_validate(
            {
                "title": f"Tasks found in {project.name}"[:200],
                "reason": "From the project's own to-do lists and GitHub, as chosen.",
                "items": [_item(n, task, project) for n, task in enumerate(tasks)],
            }
        )
        changeset = changesets_core.propose(data, project.id)
    with batch():
        for skill in skills:
            resources_core.create(
                ResourceCreate(
                    kind="skill", title=skill["name"], description_md=skill["about"], path=skill["folder"]
                ),
                link,
            )
        for command in commands:
            instances_core.create(
                InstanceCreate(project_id=project.id, name=command["name"], command=command["command"])
            )
    return {"changeset": changeset, "skills": len(skills), "commands": len(commands)}


def _item(place: int, task: dict[str, Any], project: Project) -> dict[str, Any]:
    source = (
        task.get("url") or f"`{task['file']}`" if task.get("url") or task.get("file") else "a GitHub board"
    )
    under = f", under {task['under']}" if task.get("under") else ""
    return {
        "op": "create_task",
        "key": f"t{place}",
        "title": task["title"],
        "project": str(project.id),
        "description": f"From {source}{under}.",
    }
