"""Every project of the machine, found then started (D-088)."""

import pytest

from app.core.schema.planning import ProjectCreate
from app.features.folder import discover_core, programs
from app.features.projects import projects_core
from app.features.recap import facts_core
from tests.test_folder import _clone, _git

LOO = ("origin", "https://github.com/me/loo.git")
UP = ("upstream", "https://github.com/Look/loo.git")


@pytest.fixture()
def machine(tmp_path, monkeypatch):
    main = _clone(tmp_path / "loo", LOO, UP)
    (main / "README.md").write_text(
        "# Loo\n\n[![badge](x)](y)\n\nLoo looks at websites and keeps what it saw.\n"
    )
    fix = _clone(tmp_path / "loo-fix", LOO, branch="fix")
    tree = tmp_path / "loo-tree"
    _git(main, "worktree", "add", "-q", "-b", "tree", str(tree))
    # The folder worked in last is the project's: whatever the machine's clock, main is the newest
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2030-01-01T00:00:00")
    _git(main, "commit", "--allow-empty", "-qm", "worked here last")
    monkeypatch.delenv("GIT_COMMITTER_DATE")
    other = _clone(tmp_path / "cairn", ("origin", "https://github.com/me/cairn.git"))
    loose = _clone(tmp_path / "notes")
    monkeypatch.setattr(facts_core, "repositories", lambda: [fix, main, tree, other, loose])
    monkeypatch.setattr(discover_core, "_me", lambda: {"t@x"})  # how the tests' commits are signed
    monkeypatch.setattr(
        programs,
        "gh",
        lambda path, *a, **k: {"parent": {"full_name": "Look/loo"}} if path == "repos/me/loo" else {},
    )
    return main, other


def test_found_then_started_once(ctx, machine):
    main, other = machine
    projects_core.create(ProjectCreate(name="Cairn", local_path=str(other)))
    found = discover_core.find()
    by = {g["name"]: g for g in found["groups"]}
    assert set(by) == {"loo", "cairn", "notes"}
    assert by["loo"]["main"] == str(main) and len(by["loo"]["copies"]) == 2
    assert by["loo"]["about"] == "Loo looks at websites and keeps what it saw."
    assert by["cairn"]["project"]["name"] == "Cairn" and by["notes"]["repo"] is None
    assert by["loo"]["mine"] > 0
    done = discover_core.make([by["loo"]["key"], by["cairn"]["key"], "/nowhere"])
    assert [p["name"] for p in done["made"]] == ["loo"] and done["skipped"] == ["cairn"]
    loo = projects_core.by_slug("loo")
    assert (loo.local_path, loo.github_repo, loo.default_branch) == (str(main), "Look/loo", "main")
    assert discover_core.make([by["loo"]["key"]])["skipped"] == ["loo"]


def test_pages_and_jobs(app, signed_in, machine):
    from app.core.jobs import jobs_core

    assert b"Look for my projects" in signed_in.get("/projects/discover").data
    signed_in.post("/projects/discover")
    with app.app_context():
        jobs_core.run(jobs_core.claim_next("io", "test"))
    page = signed_in.get("/projects/discover").data.decode()
    assert "Not in Cairn yet" in page and "Loo looks at websites" in page
    key = page.split('name="keys" value="')[1].split('"')[0]
    assert b"Choose at least one" in signed_in.post("/projects/discover/make", follow_redirects=True).data
    signed_in.post("/projects/discover/make", data={"keys": [key]})
    with app.app_context():
        jobs_core.run(jobs_core.claim_next("io", "test"))
    assert "Started:" in signed_in.get("/projects/discover").data.decode()
    assert signed_in.post("/api/projects/discover").status_code == 202


def test_a_repository_never_committed_in_is_not_chosen(ctx, machine, monkeypatch):
    monkeypatch.setattr(discover_core, "_me", lambda: {"someone else"})
    assert all(not g["mine"] for g in discover_core.find()["groups"])
