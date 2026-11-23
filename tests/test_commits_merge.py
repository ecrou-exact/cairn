"""Commits kept on a task; a pull request merged by the owner (D-099)."""

import pytest

from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.core.utils.actor import acting_as
from app.features.claude import claude_core
from app.features.comments import comments_core
from app.features.folder import git_core, programs
from app.features.instances import found_core
from app.features.projects import projects_core
from app.features.recap import facts_core
from app.features.tasks import tasks_core
from app.features.worklinks import worklinks_core
from tests.test_folder import _clone, _git

PULL = {
    "number": 7, "title": "Tree", "html_url": "https://github.com/Look/loo/pull/7", "state": "open",
    "draft": False, "head": {"ref": "tree"}, "base": {"ref": "main"}, "body": "", "mergeable": True,
    "mergeable_state": "clean",
}  # fmt: skip


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(found_core, "_containers", list)
    monkeypatch.setattr(found_core, "_listeners", dict)
    monkeypatch.setattr(claude_core, "outside", list)
    monkeypatch.setattr(facts_core, "repositories", list)
    main = _clone(tmp_path / "loo", ("origin", "https://github.com/Look/loo.git"))
    _git(main, "switch", "-q", "-c", "tree")
    _git(main, "commit", "--allow-empty", "-qm", "draw the tree")
    _git(main, "switch", "-q", "main")
    calls = []

    def gh(path, *fields, method="GET"):
        calls.append((method, path, fields))
        if method == "PUT":
            return {"merged": True, "sha": "abc1234def5678"}
        return PULL if path.endswith("/pulls/7") else None

    monkeypatch.setattr(programs, "gh", gh)
    return main, calls


def test_commits_kept_and_merge(ctx, setup):
    main, calls = setup
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(main), github_repo="Look/loo"))
    task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind="pull", ref="Look/loo#7"))
    found = git_core.for_task(task)
    assert [c["subject"] for c in found["commits"]] == ["draw the tree"]
    git_core.for_task(task)  # again: kept once
    commits = [
        w for w in worklinks_core.for_target("task", task.id, deep=False)["own"] if w["kind"] == "commit"
    ]
    assert len(commits) == 1 and "draw the tree" in commits[0]["note"]
    with acting_as("claude:x"), pytest.raises(git_core.GitError, match="owner"):
        git_core.merge(task, "Look/loo#7", "squash")
    done = git_core.merge(task, "Look/loo#7", "squash")
    assert (
        done["sha"].startswith("abc1234")
        and ("PUT", "repos/Look/loo/pulls/7/merge", ("merge_method=squash",)) in calls
    )
    assert "Merged Look/loo#7" in comments_core.for_target("task", task.id)[0].body_md
    with pytest.raises(git_core.GitError):
        git_core.merge(task, "Look/loo#8", "squash")


def test_the_button(app, signed_in, setup):
    main, _ = setup
    with app.app_context():
        project = projects_core.create(
            ProjectCreate(name="Loo", local_path=str(main), github_repo="Look/loo")
        )
        task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
        worklinks_core.add(
            WorkLinkCreate(target_type="task", target_id=task.id, kind="pull", ref="Look/loo#7")
        )
        task_id = str(task.id)
    page = signed_in.get(f"/tasks/{task_id}?tab=git").data.decode()
    assert "Merge into main" in page and "draw the tree" in page
    done = signed_in.post(
        f"/tasks/{task_id}/merge", data={"pull": "Look/loo#7", "method": "squash"}, follow_redirects=True
    )
    assert b"Merged Look/loo#7" in done.data
