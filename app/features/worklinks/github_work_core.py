"""A project's open pull requests, issues and branches, to link to a task in one click, or to make a
task for each (D-085). Read from GitHub with the owner's `gh`, and from the project's copies."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.db_class.planning import Project, Task
from app.core.db_class.worklink import WorkLink
from app.core.extensions import db
from app.core.schema.planning import TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.history import batch
from app.features.folder import copies_core, programs, scan_core
from app.features.tasks import tasks_core, workflow
from app.features.worklinks import worklinks_core

MAX_AT_ONCE = 60


class GithubWorkError(ValueError):
    pass


def _taken(project: Project) -> dict[tuple[str, str], dict[str, str]]:
    """What a task of the project links already: (kind, ref) → that task."""
    rows = db.session.execute(
        select(WorkLink.kind, WorkLink.ref, Task.id, Task.title)
        .join(Task, (WorkLink.target_type == "task") & (WorkLink.target_id == Task.id))
        .where(Task.project_id == project.id, Task.deleted_at.is_(None), WorkLink.deleted_at.is_(None))
    )
    found = {}
    for kind, ref, task_id, title in rows:
        full = (
            f"{project.github_repo or ''}{ref}" if ref.startswith("#") else ref
        )  # "#12" is the project's own
        found[(kind, full.lower())] = {"id": str(task_id), "title": title}
    return found


def _type(kind: str) -> str:
    """bug for an issue, feature otherwise, when the owner's types have them."""
    known = {t["key"] for t in workflow.types()}
    wanted = "bug" if kind == "issue" else "feature"
    return wanted if wanted in known else next(iter(known))


def choices(project: Project) -> dict[str, Any]:
    """Open pull requests and issues of the project's repository, and the branches of its copies, each
    with the task that has it already."""
    repo = project.github_repo
    taken = _taken(project)
    pulls, issues, read = [], [], True
    if repo:
        found, read = copies_core._pulls({repo.lower()})
        pulls = [p for p in found if p["state"] in ("open", "draft")]
        issues = scan_core._issues(repo)
        read = read and issues is not None
    me = (programs.gh("user") or {}).get("login", "").lower() if repo else ""
    rows = []
    for pull in pulls:
        ref = f"{pull['repo']}#{pull['number']}"
        rows.append(
            {
                "kind": "pull", "ref": ref, "number": pull["number"], "title": pull["title"],
                "url": pull["url"], "state": pull["state"], "branch": pull["branch"],
                "mine": bool(me) and pull["head"].startswith(f"{me}/"),
                "task": taken.get(("pull", ref.lower())),
            }
        )  # fmt: skip
    for issue in issues or []:
        ref = f"{repo}#{issue['number']}"
        rows.append(
            {
                "kind": "issue", "ref": ref, "number": issue["number"], "title": issue["title"],
                "url": issue["url"], "state": "open", "branch": "", "mine": issue["mine"],
                "task": taken.get(("issue", ref.lower())),
            }
        )  # fmt: skip
    branches = {}
    for folder in copies_core.folders(project) if project.local_path else []:
        for name in programs.git(folder, "branch", "--format=%(refname:short)").splitlines():
            branches.setdefault(name, str(folder))
    rows += [
        {
            "kind": "branch", "ref": name, "number": None, "title": "", "url": "", "state": "",
            "branch": name, "mine": True, "task": taken.get(("branch", name.lower())), "folder": folder,
        }
        for name, folder in sorted(branches.items())
        if name not in (project.default_branch, "main", "master")
    ]  # fmt: skip
    return {"items": rows, "github": read, "repo": repo}


def make_tasks(project: Project, refs: list[str], parent: Task | None = None) -> list[Task]:
    """A task for each chosen pull request or issue, linked to it (and to its branch), in one batch."""
    wanted = set(refs)
    if len(wanted) > MAX_AT_ONCE:
        raise GithubWorkError(f"At most {MAX_AT_ONCE} at a time.")
    chosen = [i for i in choices(project)["items"] if f"{i['kind']}:{i['ref']}" in wanted and not i["task"]]
    if not chosen:
        raise GithubWorkError("Choose a pull request or an issue that has no task yet.")
    made = []
    with batch():
        for item in chosen:
            title = f"#{item['number']} {item['title']}" if item["number"] else f"Branch {item['ref']}"
            task = tasks_core.create(
                TaskCreate(
                    title=title[:200],
                    project_id=project.id,
                    parent_id=parent.id if parent else None,
                    type="feature"
                    if item["kind"] == "pull"
                    else "bug"
                    if item["kind"] == "issue"
                    else "feature",
                    description_md=f"From {item['url'] or item['ref']}.",
                )
            )
            link = WorkLinkCreate(target_type="task", target_id=task.id, kind=item["kind"], ref=item["ref"])
            worklinks_core.add(link)
            if item["kind"] == "pull" and item["branch"]:
                worklinks_core.add(
                    WorkLinkCreate(target_type="task", target_id=task.id, kind="branch", ref=item["branch"])
                )
            made.append(task)
    return made
