"""Starred and pinned projects; a task from a copy (D-089)."""

import pytest

from app.core.schema.planning import ProjectCreate
from app.features.claude import claude_core
from app.features.folder import git_core, programs
from app.features.instances import found_core
from app.features.projects import projects_core
from app.features.recap import facts_core
from app.features.worklinks import worklinks_core
from tests.test_folder import _clone, _git


def test_star_and_pin(app, signed_in):
    with app.app_context():
        for name in ("Alpha", "Zulu"):
            projects_core.create(ProjectCreate(name=name))
    signed_in.post("/projects/zulu/star")
    listing = signed_in.get("/projects?view=table").data.decode()
    assert listing.index("Zulu") < listing.index("Alpha")
    assert "Pinned" not in signed_in.get("/").data.decode()
    signed_in.post("/projects/alpha/pin")
    page = signed_in.get("/").data.decode()
    assert "nav-pinned" in page and "/projects/alpha" in page
    signed_in.post("/projects/alpha/pin")
    assert "nav-pinned" not in signed_in.get("/").data.decode()
    assert signed_in.post("/projects/none/star").status_code == 404
    signed_in.post("/projects/alpha/hide")
    assert '/projects/alpha"' not in signed_in.get("/projects?view=table").data.decode()
    hidden = signed_in.get("/projects?hidden=1&view=table").data.decode()
    assert "/projects/alpha" in hidden and '/projects/zulu"' not in hidden and "Hidden" in hidden


@pytest.fixture()
def copies(tmp_path, monkeypatch):
    monkeypatch.setattr(found_core, "_containers", list)
    monkeypatch.setattr(found_core, "_listeners", dict)
    monkeypatch.setattr(claude_core, "outside", list)
    found_core._kept.clear()
    main = _clone(tmp_path / "loo", ("origin", "https://github.com/Look/loo.git"))
    tree = tmp_path / "loo-tree"
    _git(main, "worktree", "add", "-q", "-b", "tree", str(tree))
    monkeypatch.setattr(facts_core, "repositories", list)
    pull = {
        "number": 7, "title": "New tree", "html_url": "https://x/7", "state": "open", "draft": True,
        "base": {"ref": "main", "repo": {"full_name": "Look/loo"}},
        "head": {"ref": "tree", "repo": {"full_name": "look/loo"}},
    }  # fmt: skip
    monkeypatch.setattr(
        programs, "gh", lambda path, *f, **k: [pull] if path.endswith("/pulls") and "page=1" in f else None
    )
    return main, tree


def test_a_task_from_a_copy(ctx, copies):
    main, tree = copies
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(main), github_repo="Look/loo"))
    task = git_core.task_from_copy(project, str(tree))
    assert task.title == "#7 New tree" and task.status == "in_progress"
    kinds = {w["kind"]: w["ref"] for w in worklinks_core.for_target("task", task.id, deep=False)["own"]}
    assert kinds == {"branch": "tree", "folder": str(tree), "pull": "Look/loo#7"}
    rows = {c["branch"]: c for c in git_core.state(project)["copies"]}
    assert rows["tree"]["task"]["title"] == "#7 New tree"
    for folder in (str(tree), str(main), "/"):
        with pytest.raises(git_core.GitError):
            git_core.task_from_copy(project, folder)


def test_the_button(app, signed_in, copies):
    main, tree = copies
    with app.app_context():
        projects_core.create(ProjectCreate(name="Loo", local_path=str(main), github_repo="Look/loo"))
    assert "Create a task" in signed_in.get("/projects/loo?tab=git").data.decode()
    done = signed_in.post("/projects/loo/git/task", data={"folder": str(tree)}, follow_redirects=True)
    assert b"Task made: #7 New tree" in done.data
    assert (
        b"has this branch already"
        in signed_in.post("/projects/loo/git/task", data={"folder": str(tree)}, follow_redirects=True).data
    )


def test_the_projects_graph_leaves_hidden_ones_out(ctx):
    from app.core.schema.planning import ProjectUpdate
    from app.features.graph import graph_core

    shown = projects_core.create(ProjectCreate(name="Shown"))
    gone = projects_core.create(ProjectCreate(name="Gone"))
    projects_core.update(shown.id, ProjectUpdate(starred=True))
    projects_core.update(gone.id, ProjectUpdate(hidden=True))
    labels = {n["data"]["label"]: n["data"] for n in graph_core.project_plan()["nodes"]}
    assert "Gone" not in labels and labels["Shown"]["starred"]


def test_projects_are_grouped_by_owner(app, signed_in):
    with app.app_context():
        for name, repo in (
            ("Zed", "acme/zed"),
            ("Alpha", "zorg/alpha"),
            ("Loose", None),
            ("Beta", "acme/beta"),
        ):
            projects_core.create(ProjectCreate(name=name, github_repo=repo))
    page = signed_in.get("/projects").data.decode()
    order = [page.index(f'/projects/{slug}"') for slug in ("beta", "zed", "alpha", "loose")]
    assert order == sorted(order)
    assert page.index("</i> acme</h2>") < page.index("</i> zorg</h2>") < page.index(">No repository</h2>")
