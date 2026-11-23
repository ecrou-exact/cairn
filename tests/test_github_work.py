"""A task per pull request or issue, and links picked from the project (D-085)."""

import pytest

from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.features.folder import programs
from app.features.projects import projects_core
from app.features.tasks import tasks_core
from app.features.worklinks import github_work_core, worklinks_core
from tests.test_folder import ORIGIN, _clone, _git

PULLS = [
    {
        "number": n, "title": f"PR {n}", "html_url": f"https://github.com/Look/loo/pull/{n}", "state": state,
        "draft": False, "merged_at": None, "base": {"ref": "main", "repo": {"full_name": "Look/loo"}},
        "head": {"ref": f"b{n}", "repo": {"full_name": "me/loo"}},
    }
    for n, state in ((1, "open"), (2, "open"), (3, "closed"))
]  # fmt: skip
ISSUES = [
    {"html_url": "https://github.com/Look/loo/issues/9", "number": 9, "title": "Broken", "assignees": []}
]


@pytest.fixture(autouse=True)
def github(monkeypatch):
    def gh(path, *fields, **kw):
        if path == "user":
            return {"login": "me"}
        if path.endswith("/pulls"):
            return PULLS if "page=1" in fields else []
        if path.endswith("/issues"):
            return ISSUES
        if path.endswith("/issues/9"):
            return {"number": 9, "title": "Broken", "html_url": ISSUES[0]["html_url"], "state": "open"}
        return None

    monkeypatch.setattr(programs, "gh", gh)


def _project(tmp_path):
    root = _clone(tmp_path / "loo", ORIGIN)
    _git(root, "branch", "work-on-tree")
    return projects_core.create(ProjectCreate(name="Loo", local_path=str(root), github_repo="Look/loo"))


def test_a_task_per_pull_request(ctx, tmp_path):
    project = _project(tmp_path)
    found = github_work_core.choices(project)
    by = {(i["kind"], i["ref"]): i for i in found["items"]}
    assert set(by) == {
        ("pull", "Look/loo#1"),
        ("pull", "Look/loo#2"),
        ("issue", "Look/loo#9"),
        ("branch", "work-on-tree"),
    }
    assert by[("pull", "Look/loo#1")]["mine"]
    made = github_work_core.make_tasks(project, ["pull:Look/loo#1", "issue:Look/loo#9"])
    assert [t.title for t in made] == ["#1 PR 1", "#9 Broken"] and made[1].type == "bug"
    links = worklinks_core.for_target("task", made[0].id, deep=False)["own"]
    assert {(w["kind"], w["ref"]) for w in links} == {("pull", "Look/loo#1"), ("branch", "b1")}
    again = {(i["kind"], i["ref"]): i["task"] for i in github_work_core.choices(project)["items"]}
    assert again[("pull", "Look/loo#1")]["title"] == "#1 PR 1" and again[("pull", "Look/loo#2")] is None
    with pytest.raises(github_work_core.GithubWorkError):
        github_work_core.make_tasks(project, ["pull:Look/loo#1"])  # it has its task
    task = tasks_core.create(TaskCreate(title="By hand", project_id=project.id))
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind="pull", ref="#2"))
    assert {(i["kind"], i["ref"]): i["task"] for i in github_work_core.choices(project)["items"]}[
        ("pull", "Look/loo#2")
    ]
    url = WorkLinkCreate(
        target_type="task", target_id=task.id, kind="issue", ref="https://github.com/Look/loo/issues/9"
    )
    assert url.ref == "Look/loo#9"


def test_pages(app, signed_in, tmp_path):
    with app.app_context():
        project = _project(tmp_path)
        task_id = str(tasks_core.create(TaskCreate(title="Tree", project_id=project.id)).id)
    page = signed_in.get("/projects/loo/github").data.decode()
    assert "#1 PR 1" in page and "#3" not in page and "work-on-tree" in page
    done = signed_in.post("/projects/loo/github", data={"refs": ["pull:Look/loo#2"]}, follow_redirects=True)
    assert b"1 task made" in done.data
    assert b"Choose a pull request" in signed_in.post("/projects/loo/github", follow_redirects=True).data
    linked = signed_in.get(f"/tasks/{task_id}?tab=linked").data.decode()
    assert "Pick from the project" in linked and "#1 PR 1" in linked and "#2 PR 2" not in linked
    assert "A task per pull request" in signed_in.get("/projects/loo").data.decode()
