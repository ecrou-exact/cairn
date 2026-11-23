"""The global search finds a task by its id, a pull request, a branch, a commit (D-086)."""

from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.worklinks import WorkLinkCreate
from app.features.projects import projects_core
from app.features.search import search_core
from app.features.tasks import tasks_core
from app.features.worklinks import worklinks_core


def _titles(query):
    return [t.title for t in search_core.search(query)["tasks"]]


def test_a_task_is_found_by_what_it_is_linked_to(ctx):
    project = projects_core.create(ProjectCreate(name="Loo", github_repo="Look/loo"))
    task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id, description_md="the side panel"))
    sub = tasks_core.create(TaskCreate(title="Leaves", project_id=project.id, parent_id=task.id))
    other = tasks_core.create(TaskCreate(title="Other #2000", project_id=project.id))
    for kind, ref in (("pull", "Look/loo#1451"), ("branch", "web-tree-modals")):
        worklinks_core.add(WorkLinkCreate(target_type="task", target_id=task.id, kind=kind, ref=ref))
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=sub.id, kind="commit", ref="3f2a9c1d"))
    for query in ("#1451", "1451", "https://github.com/Look/loo/pull/1451", "tree-modals", "side panel"):
        assert _titles(query) == ["Tree"], query
    assert _titles("#1451") == ["Tree"]
    assert _titles("3f2a9c1") == ["Leaves"]
    assert _titles(str(sub.id)) == ["Leaves"] and _titles(sub.id.hex[:8]) == ["Leaves"]
    assert _titles(str(other.id)[:13]) == ["Other #2000"]


def test_the_palette_shows_a_subtasks_parent(app, signed_in):
    with app.app_context():
        task = tasks_core.create(TaskCreate(title="Tree"))
        sub = tasks_core.create(TaskCreate(title="Leaves", parent_id=task.id))
        ref = sub.id.hex[:8]
    (found,) = signed_in.get(f"/api/search?q={ref}").json["tasks"]
    assert (found["title"], found["parent"]) == ("Leaves", "Tree")


def test_a_github_address_finds_its_project_and_task(ctx):
    loo = projects_core.create(ProjectCreate(name="Lookyloo", github_repo="Lookyloo/lookyloo"))
    other = projects_core.create(ProjectCreate(name="Other", github_repo="else/other"))
    mine = tasks_core.create(TaskCreate(title="Explore pages", project_id=loo.id))
    same_number = tasks_core.create(TaskCreate(title="Other 1446", project_id=other.id))
    short = tasks_core.create(TaskCreate(title="By number", project_id=loo.id))
    worklinks_core.add(
        WorkLinkCreate(target_type="task", target_id=mine.id, kind="pull", ref="Lookyloo/lookyloo#1446")
    )
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=same_number.id, kind="pull", ref="#1446"))
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=short.id, kind="issue", ref="#9"))
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=short.id, kind="branch", ref="web-tree"))
    found = search_core.search("https://github.com/Lookyloo/lookyloo/pull/1446")
    assert [p.name for p in found["projects"]] == ["Lookyloo"]
    assert [t.title for t in found["tasks"]] == ["Explore pages"]
    assert _titles("https://github.com/Lookyloo/lookyloo/issues/9") == ["By number"]
    assert _titles("https://github.com/Lookyloo/lookyloo/tree/web-tree") == ["By number"]
    assert [p.name for p in search_core.search("github.com/else/other")["projects"]] == ["Other"]


def test_an_address_of_no_project_offers_to_start_it(app, signed_in, monkeypatch):
    from app.features.claude import terminal_core

    with app.app_context():
        projects_core.create(ProjectCreate(name="Lookyloo", github_repo="Lookyloo/lookyloo"))
    found = signed_in.get("/api/search?q=https://github.com/Lookyloo/lookyloo/pull/1446").json
    assert found["github"] == {
        "repo": "Lookyloo/lookyloo",
        "kind": "pull",
        "what": "1446",
        "known": True,
        "git": "/projects/lookyloo?tab=git&pull=1446",
    }
    new = signed_in.get("/api/search?q=https://github.com/acme/tool/pull/7").json["github"]
    assert new["known"] is False
    launched = []
    monkeypatch.setattr(terminal_core, "_launch", lambda *a, **k: launched.append(a) or None)
    with app.app_context():
        terminal_core.start_from_github("https://github.com/acme/tool/pull/7")
        message = launched[0][3]
        assert "git clone" in message and "gh pr checkout 7" in message and "start_project" in message
        try:
            terminal_core.start_from_github("https://github.com/Lookyloo/lookyloo")
        except terminal_core.TerminalError as exc:
            assert "already" in str(exc)
        else:
            raise AssertionError("a known repository is not started twice")


def test_a_pull_request_of_a_project_leads_to_its_branch(app, signed_in, tmp_path, monkeypatch):
    from app.features.claude import claude_core
    from app.features.folder import programs
    from app.features.instances import found_core
    from app.features.recap import facts_core
    from tests.test_folder import _clone, _git

    monkeypatch.setattr(found_core, "_containers", list)
    monkeypatch.setattr(found_core, "_listeners", dict)
    monkeypatch.setattr(claude_core, "outside", list)
    monkeypatch.setattr(facts_core, "repositories", list)
    main = _clone(tmp_path / "loo", ("origin", "https://github.com/Look/loo.git"))
    _git(main, "worktree", "add", "-q", "-b", "menus", str(tmp_path / "loo-menus"))
    pull = {
        "number": 1450, "title": "Menus", "html_url": "https://x/1450", "state": "open", "draft": True,
        "base": {"ref": "main", "repo": {"full_name": "Look/loo"}},
        "head": {"ref": "menus", "repo": {"full_name": "look/loo"}},
    }  # fmt: skip
    monkeypatch.setattr(
        programs, "gh", lambda path, *f, **k: [pull] if path.endswith("/pulls") and "page=1" in f else None
    )
    with app.app_context():
        projects_core.create(ProjectCreate(name="Loo", local_path=str(main), github_repo="Look/loo"))
    found = signed_in.get("/api/search?q=https://github.com/Look/loo/pull/1450").json["github"]
    assert found["git"] == "/projects/loo?tab=git&pull=1450"
    page = signed_in.get(found["git"]).data.decode()
    assert 'id="wanted-copy"' in page and "is on <strong>menus</strong>" in page and "create its task" in page
    assert "No copy on this machine" in signed_in.get("/projects/loo?tab=git&pull=9").data.decode()
