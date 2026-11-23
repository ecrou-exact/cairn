"""Git, for a project and for a task (D-087): where each copy stands (branch, ahead and behind, changes
not committed, pull request), the task's own branches, and the two actions that only bring work in:
fetch, and pull when it fast-forwards. Nothing here commits, pushes, merges, switches or deletes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.db_class.planning import Project, Task
from app.core.utils.history import batch
from app.core.utils.logger import log_action
from app.features.folder import copies_core, programs
from app.features.worklinks import worklinks_core

ACTIONS = {
    "fetch": ("fetch", "--all", "--prune"),
    "pull": ("pull", "--ff-only"),
}


class GitError(ValueError):
    pass


def state(project: Project) -> dict[str, Any]:
    """Each copy, with the task that has its branch already."""
    from app.features.worklinks import github_work_core  # it builds on the copies

    found = copies_core.overview(project)
    taken = github_work_core._taken(project)
    for copy in found["copies"]:
        copy["task"] = taken.get(("branch", copy["branch"].lower())) if copy["branch"] else None
    return {**found, "repo": project.github_repo, "default": project.default_branch}


def task_from_copy(project: Project, folder: str) -> Task:
    """A task for the work in one copy: its pull request's title, or its branch; linked to its branch,
    its folder and its pull request; in progress while the pull request is open (D-089)."""
    from app.core.schema.planning import TaskCreate
    from app.core.schema.worklinks import WorkLinkCreate
    from app.features.tasks import tasks_core, workflow

    wanted = str(Path(folder).resolve())
    copy = next((c for c in state(project)["copies"] if str(Path(c["folder"]).resolve()) == wanted), None)
    if copy is None:
        raise GitError("This folder is not a copy of the project.")
    if copy["task"]:
        raise GitError(f"“{copy['task']['title']}” has this branch already.")
    if not copy["branch"] or copy["branch"] == project.default_branch:
        raise GitError("This copy is on the main branch: a task is for the work of a branch.")
    pull = copy["pull"]
    title = f"#{pull['number']} {pull['title']}" if pull else copy["branch"]
    with batch():
        task = tasks_core.create(
            TaskCreate(
                title=title[:200],
                project_id=project.id,
                description_md=f"The work of `{copy['branch']}`, in `{copy['folder']}`.",
            )
        )
        links = [("branch", copy["branch"]), ("folder", copy["folder"])]
        if pull:
            links.append(("pull", f"{pull['repo']}#{pull['number']}"))
        for kind, ref in links:
            worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind=kind, ref=ref))
        if (
            pull
            and pull["state"] in ("open", "draft")
            and "in_progress" in workflow.allowed_next(task.status)
        ):
            tasks_core.set_status(task.id, "in_progress")
    return task


def for_task(task: Task) -> dict[str, Any]:
    """The copies on the task's branches, and its branches that no copy has out."""
    project = task.project
    links = worklinks_core.for_target("task", task.id)
    every = [*links["own"], *links["known"], *links["inherited"]]
    branches = {w["ref"] for w in every if w["kind"] == "branch"}
    branches |= {w["branch"] for w in every if w["kind"] == "pull" and w.get("branch")}
    found = state(project) if project and project.local_path else {"copies": [], "github": True}
    copies = [c for c in found["copies"] if c["branch"] in branches]
    out = {c["branch"] for c in copies}
    elsewhere = [w for w in every if w["kind"] == "branch" and w["ref"] not in out]
    pulls = [w for w in every if w["kind"] == "pull"]
    commits = _branch_commits(project, sorted(branches)) if project and project.local_path else []
    _keep_commits(task, commits)
    return {"copies": copies, "elsewhere": elsewhere, "pulls": pulls, "branches": sorted(branches),
            "commits": commits, "github": found.get("github", True)}  # fmt: skip


MOST_COMMITS = 50


def _branch_commits(project: Project, branches: list[str]) -> list[dict[str, Any]]:
    """The commits of the task's branches that its project's main branch does not have, newest first."""
    folders = copies_core.folders(project)
    if not folders:
        return []
    main = folders[0]
    found: dict[str, dict[str, Any]] = {}
    for branch in branches:
        for ref in (branch, f"origin/{branch}"):
            log = programs.git(
                main, "log", f"--max-count={MOST_COMMITS}", "--format=%H%x1f%h%x1f%ct%x1f%an%x1f%s",
                ref, f"^{project.default_branch}", "--",
            )  # fmt: skip
            if not log:
                continue
            for line in log.splitlines():
                sha, short, when, who, subject = (line.split("\x1f") + [""] * 5)[:5]
                found.setdefault(sha, {"sha": sha, "short": short, "at": int(when or 0), "author": who,
                                       "subject": subject, "branch": branch})  # fmt: skip
            break
    return sorted(found.values(), key=lambda c: -c["at"])[: MOST_COMMITS * 2]


def _keep_commits(task: Task, commits: list[dict[str, Any]]) -> None:
    """A trace on the task of the commits made for it: they stay linked when the branch is gone (D-099)."""
    from sqlalchemy import select

    from app.core.db_class.worklink import WorkLink
    from app.core.extensions import db
    from app.core.schema.worklinks import WorkLinkCreate

    known = set(
        db.session.scalars(
            select(WorkLink.ref).where(
                WorkLink.target_type == "task", WorkLink.target_id == task.id, WorkLink.kind == "commit"
            )
        )
    )
    new = [c for c in commits if c["sha"] not in known]
    if not new:
        return
    with batch():
        for commit in new:
            worklinks_core.add(
                WorkLinkCreate(
                    target_type="task", target_id=task.id, kind="commit", ref=commit["sha"],
                    note=f"{commit['subject'][:400]} ({commit['branch']})",
                )
            )  # fmt: skip


# -- merging a pull request (D-099) -------------------------------------------------------------------

MERGE_METHODS = ("merge", "squash", "rebase")


def merge(task: Task, ref: str, method: str) -> dict[str, Any]:
    """Merge one of the task's pull requests on GitHub, by the owner only; the merge commit and a
    comment stay on the task. Never forced: GitHub refuses what is not mergeable."""
    from app.core.schema.comments import CommentCreate
    from app.core.schema.worklinks import WorkLinkCreate
    from app.core.utils.actor import current_actor
    from app.features.comments import comments_core

    if current_actor() != "user":
        raise GitError("Only the owner merges.")
    if method not in MERGE_METHODS:
        raise GitError("Merge, squash or rebase.")
    links = worklinks_core.for_target("task", task.id)
    pull = next(
        (w for w in [*links["own"], *links["inherited"]] if w["kind"] == "pull" and w["ref"] == ref), None
    )
    if pull is None or not pull.get("found"):
        raise GitError("This pull request is not linked to the task, or GitHub did not answer.")
    if pull["state"] == "merged":
        raise GitError("This pull request is merged already.")
    if pull["state"] != "open":
        raise GitError("Only an open pull request, not a draft nor a closed one, is merged.")
    repo, number = pull["repo"], pull["number"]
    answer = programs.gh(f"repos/{repo}/pulls/{number}/merge", f"merge_method={method}", method="PUT")
    if not isinstance(answer, dict) or not answer.get("merged"):
        raise GitError("GitHub did not merge it: look at its checks and reviews on GitHub.")
    sha = answer.get("sha", "")
    with batch():
        if sha:
            worklinks_core.add(
                WorkLinkCreate(target_type="task", target_id=task.id, kind="commit", ref=sha,
                               note=f"Merge of {repo}#{number} ({method})")
            )  # fmt: skip
        comments_core.create(
            CommentCreate(
                target_type="task", target_id=task.id, kind="comment",
                body_md=f"Merged {repo}#{number} into `{pull.get('base') or 'its base'}` ({method}), "
                f"commit `{sha[:12]}`.",
            )
        )  # fmt: skip
        log_action("git.merge", target_type="task", target_id=task.id,
                   meta={"pull": f"{repo}#{number}", "method": method, "sha": sha})  # fmt: skip
    return {"merged": True, "sha": sha, "pull": f"{repo}#{number}"}


def act(project: Project, folder: str, action: str) -> str:
    """Fetch or pull one copy of the project; refused for a folder that is not one of its copies."""
    if action not in ACTIONS:
        raise GitError("Only fetch and pull are done from here.")
    wanted = Path(folder).resolve()
    if wanted not in [Path(f).resolve() for f in copies_core.folders(project)]:
        raise GitError("This folder is not a copy of the project.")
    done, said = programs.git_told(wanted, *ACTIONS[action])
    with batch():
        log_action(
            f"git.{action}",
            target_type="project",
            target_id=project.id,
            meta={"folder": str(wanted), "done": done},
            level="info" if done else "warning",
        )
    if not done:
        if action == "pull" and ("diverg" in said or "Not possible to fast-forward" in said):
            raise GitError(
                "Not pulled: this branch and the remote one went different ways. Merge or rebase it yourself."
            )
        if action == "pull" and ("overwritten" in said or "uncommitted" in said or "local changes" in said):
            raise GitError(
                "Not pulled: changes not committed here would be overwritten. Commit or stash them first."
            )
        raise GitError(f"git {action} failed: {said[-300:]}")
    return said or "Already up to date."
