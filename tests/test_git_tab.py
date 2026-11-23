"""Git on a project and on a task (D-087)."""

import pytest

from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.features.claude import claude_core
from app.features.folder import git_core, programs
from app.features.instances import found_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core
from app.features.worklinks import worklinks_core
from tests.test_folder import _clone, _git


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(found_core, "_containers", list)
    monkeypatch.setattr(found_core, "_listeners", dict)
    monkeypatch.setattr(claude_core, "outside", list)
    monkeypatch.setattr(programs, "gh", lambda *a, **k: None)
    found_core._kept.clear()


@pytest.fixture()
def two(tmp_path, monkeypatch):
    """A remote and a clone of it that is one commit behind."""
    from app.features.recap import facts_core

    remote = _clone(tmp_path / "remote", ("origin", "https://github.com/Look/loo.git"))
    mine = tmp_path / "loo"
    _git(tmp_path, "clone", "-q", str(remote), str(mine))
    _git(remote, "commit", "--allow-empty", "-qm", "newer there")
    monkeypatch.setattr(facts_core, "repositories", list)
    return remote, mine


def test_fetch_then_pull_a_copy(ctx, two):
    remote, mine = two
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(mine)))
    git_core.act(project, str(mine), "fetch")
    (copy,) = git_core.state(project)["copies"]
    assert copy["behind"] == 1 and copy["main"]
    git_core.act(project, str(mine), "pull")
    assert git_core.state(project)["copies"][0]["behind"] == 0
    for folder, action in ((str(remote), "pull"), (str(mine), "push")):
        with pytest.raises(git_core.GitError):
            git_core.act(project, folder, action)


def test_a_pull_that_would_merge_is_refused(ctx, two):
    _, mine = two
    _git(mine, "commit", "--allow-empty", "-qm", "mine")
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(mine)))
    git_core.act(project, str(mine), "fetch")
    with pytest.raises(git_core.GitError, match="different ways"):
        git_core.act(project, str(mine), "pull")


def test_a_task_shows_its_branches(ctx, two):
    _, mine = two
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(mine)))
    task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
    sub = tasks_core.create(TaskCreate(title="Leaves", project_id=project.id, parent_id=task.id))
    _git(mine, "branch", "tree")
    for ref in ("main", "tree"):
        worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind="branch", ref=ref))
    found = git_core.for_task(sub)
    assert [c["branch"] for c in found["copies"]] == ["main"]
    assert [w["ref"] for w in found["elsewhere"]] == ["tree"] and found["elsewhere"][0]["found"]


def test_pages(app, signed_in, two):
    _, mine = two
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Loo", local_path=str(mine)))
        task_id = str(tasks_core.create(TaskCreate(title="Tree", project_id=project.id)).id)
        project_id = str(project.id)
    page = signed_in.get("/projects/loo?tab=git").data.decode()
    assert "project folder" in page and "Fetch" in page
    done = signed_in.post("/projects/loo/git/fetch", data={"folder": str(mine)}, follow_redirects=True)
    assert b"Fetch:" in done.data
    refused = signed_in.post("/projects/loo/git/pull", data={"folder": "/"}, follow_redirects=True)
    assert b"not a copy of the project" in refused.data
    assert b"No branch is linked" in signed_in.get(f"/tasks/{task_id}?tab=git").data
    assert signed_in.get(f"/api/projects/{project_id}/git").json["copies"][0]["behind"] == 1
    assert (
        signed_in.post(f"/api/projects/{project_id}/git/pull", json={"folder": str(mine)}).status_code == 200
    )
