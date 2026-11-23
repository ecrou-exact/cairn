"""A project's copies on the machine, and what is taken from its folder (D-081)."""

import os
import shutil
import subprocess

import pytest

from app.core.db_class.planning import Task
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.claude import claude_core
from app.features.folder import copies_core, programs, scan_core
from app.features.instances import found_core, instances_core
from app.features.projects import projects_core
from app.features.recap import facts_core
from app.features.resources import resources_core
from app.features.tasks import tasks_core


def _git(folder, *args):
    who = {f"GIT_{w}_{k}": "t@x" for w in ("AUTHOR", "COMMITTER") for k in ("NAME", "EMAIL")}
    subprocess.run(  # noqa: S603
        [shutil.which("git"), "-C", str(folder), *args],
        check=True,
        capture_output=True,
        env={**os.environ, **who},
    )


def _clone(folder, *remotes, branch="main"):
    folder.mkdir()
    _git(folder, "init", "-q", "-b", branch)
    for name, url in remotes:
        _git(folder, "remote", "add", name, url)
    _git(folder, "commit", "--allow-empty", "-qm", f"on {branch}")
    return folder


ORIGIN = ("origin", "https://github.com/Look/loo.git")
FORK = ("fork", "git@github.com:me/loo.git")


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(found_core, "_containers", list)
    monkeypatch.setattr(found_core, "_listeners", dict)
    monkeypatch.setattr(claude_core, "outside", list)
    found_core._kept.clear()


def _pull(number, branch, head, **more):
    base = {"ref": "main", "repo": {"full_name": "Look/loo"}}
    row = {"number": number, "title": "T", "html_url": f"https://x/{number}", "state": "open", "base": base}
    return {**row, "head": {"ref": branch, "repo": {"full_name": head} if head else None}, **more}


def test_one_project_whatever_its_copies(ctx, tmp_path, monkeypatch):
    main = _clone(tmp_path / "loo", ORIGIN, FORK)
    work = _clone(tmp_path / "loo-pr3", ORIGIN, FORK, branch="capture-list")
    (work / "new.txt").write_text("x")
    only_fork = _clone(tmp_path / "loo-mine", FORK, branch="stats")
    other = _clone(tmp_path / "other", ("origin", "https://github.com/Look/else.git"))
    tree = tmp_path / "elsewhere"
    _git(main, "worktree", "add", "-q", "-b", "tree", str(tree))
    monkeypatch.setattr(facts_core, "repositories", lambda: [main, work, only_fork, other])
    pulls = [
        _pull(1, "capture-list", "me/loo", state="closed"),
        _pull(2, "capture-list", "me/loo", draft=True),
        _pull(3, "capture-list", "someone/loo"),
        _pull(4, "stats", "me/loo", state="closed", merged_at="2026-11-01"),
        _pull(5, "tree", None),
    ]
    monkeypatch.setattr(
        programs, "gh", lambda path, *f, **k: pulls if "Look/loo" in path.replace("look", "Look") else []
    )
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(main)))
    found = copies_core.overview(project)
    by = {c["name"]: c for c in found["copies"]}
    assert set(by) == {"loo", "loo-pr3", "loo-mine", "elsewhere"} and found["github"]
    assert found["copies"][0]["name"] == "loo" and by["loo"]["main"]
    assert (
        by["elsewhere"]["worktree"]
        and by["elsewhere"]["branch"] == "tree"
        and by["elsewhere"]["pull"] is None
    )
    assert (by["loo-pr3"]["pull"]["number"], by["loo-pr3"]["pull"]["state"]) == (2, "draft")
    assert by["loo-pr3"]["changes"] == 1 and by["loo-mine"]["pull"]["state"] == "merged"
    monkeypatch.setattr(programs, "gh", lambda *a, **k: None)
    assert copies_core.overview(project)["github"] is False


SKILL = "---\nname: deploy\ndescription: How to deploy\n---\nRun it."


@pytest.fixture()
def full(tmp_path, monkeypatch):
    root = _clone(tmp_path / "loo", ORIGIN)
    (root / "TODO.md").write_text(
        "# Soon\n- [ ] Faster tree\n- [x] Old\n- a remark\n```\n- [ ] code\n```\n- [ ] Known\n"
    )
    (root / "README.md").write_text("- a feature\n")
    (root / "package.json").write_text('{"scripts": {"dev": "vite", "lint": "x"}}')
    (root / "Procfile").write_text("web: python app.py\n")
    (root / ".claude" / "skills" / "deploy").mkdir(parents=True)
    (root / ".claude" / "skills" / "deploy" / "SKILL.md").write_text(SKILL)
    secret = tmp_path / "secret.md"
    secret.write_text("- [ ] stolen\n")
    (root / "ROADMAP.md").symlink_to(secret)
    issue = {"html_url": "https://github.com/Look/loo/issues/7", "number": 7, "title": "Broken <b>link</b>"}

    def gh(path, *fields, method="GET"):
        if path == "graphql":
            cards = [
                {"content": {"title": "A card"}},
                {"content": {"title": issue["title"], "url": issue["html_url"], "state": "OPEN"}},
                {"content": {"title": "Over", "state": "CLOSED"}},
            ]
            return {
                "data": {
                    "repository": {"projectsV2": {"nodes": [{"title": "Board", "items": {"nodes": cards}}]}}
                }
            }
        if path.endswith("/pulls"):
            return []
        return [issue, {**issue, "html_url": "https://x/8", "pull_request": {}}]

    monkeypatch.setattr(programs, "gh", gh)
    return root


def _project(root):
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(root), github_repo="Look/loo"))
    tasks_core.create(TaskCreate(title="known", project_id=project.id))
    return project


def test_what_a_project_has_is_found_once(ctx, full):
    project = _project(full)
    found = scan_core.scan(project)
    assert [t["title"] for t in found["todos"]] == ["Faster tree"] and found["todos"][0]["under"] == "Soon"
    assert [i["number"] for i in found["issues"]] == [7] and [c["title"] for c in found["cards"]] == [
        "A card"
    ]
    assert [s["name"] for s in found["skills"]] == ["deploy"]
    assert {c["command"] for c in found["commands"]} == {"npm run dev", "python app.py"}
    keys = [found[kind][0]["key"] for kind in ("todos", "issues", "skills", "commands")]
    taken = scan_core.bring(project, keys)
    assert len(taken["changeset"].items) == 2 and taken["changeset"].status == "proposed"
    assert db.session.scalars(db.select(Task.title)).all() == ["known"]  # only proposed
    assert [r.kind for _, r in resources_core.for_target("project", project.id)] == ["skill"]
    assert len(instances_core.for_project(project.id)) == 1
    again = scan_core.scan(project)
    assert again["skills"] == [] and len(again["commands"]) == 1
    with pytest.raises(scan_core.ScanError):
        scan_core.bring(project, ["0" * 16])


def test_what_github_refuses_is_said(ctx, full, monkeypatch):
    monkeypatch.setattr(programs, "gh", lambda *a, **k: None)
    found = scan_core.scan(_project(full))
    assert not found["issues_read"] and not found["boards_read"] and found["todos"]


def test_pages_and_api(app, signed_in, full, monkeypatch):
    monkeypatch.setattr(facts_core, "repositories", list)
    with app.app_context():
        ref = str(_project(full).id)
    page = signed_in.get("/projects/loo/bring").data.decode()
    assert "Faster tree" in page and "Broken &lt;b&gt;" in page and "stolen" not in page
    found = signed_in.get(f"/api/projects/{ref}/found").json
    key = found["todos"][0]["key"]
    answer = signed_in.post("/projects/loo/bring", data={"keys": [key]})
    assert "/changesets/" in answer.headers["Location"]
    assert b"Choose at least one" in signed_in.post("/projects/loo/bring", follow_redirects=True).data
    assert signed_in.post(f"/api/projects/{ref}/bring", json={"keys": ["nope"]}).status_code == 422
    assert signed_in.post(f"/api/projects/{ref}/bring", json={"keys": [key]}).status_code == 201
    assert b"project folder" in signed_in.get("/projects/loo/copies").data
    assert signed_in.get(f"/api/projects/{ref}/copies").json["copies"][0]["main"]
    assert signed_in.get("/projects/none/copies").status_code == 404
    assert b"Bring in" in signed_in.get("/projects/loo").data


def test_a_submodule_is_not_the_project(ctx, tmp_path, monkeypatch):
    main = _clone(tmp_path / "loo", ORIGIN)
    with (main / ".git" / "config").open("a") as config:
        config.write('[submodule "data"]\n\turl = https://github.com/misp/data.git\n')
    other = _clone(tmp_path / "misp-data", ("origin", "https://github.com/misp/data.git"))
    inner = main / "modules"
    _clone(inner, ("origin", "https://github.com/x/inner.git"))
    monkeypatch.setattr(facts_core, "repositories", lambda: [main, other, inner])
    project = projects_core.create(ProjectCreate(name="Loo", local_path=str(main)))
    assert copies_core.folders(project) == [main.resolve()]
