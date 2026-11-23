"""Claude runs one version of a project (D-091)."""

from app.core.schema.claude import SessionStart
from app.core.schema.planning import ProjectCreate
from app.features.claude import terminal_core
from app.features.projects import projects_core
from tests.test_folder import _clone


def test_the_run_message(tmp_path):
    data = SessionStart(preset="run", folder=str(tmp_path), detail="with docker")
    message = terminal_core._first_message(data, None)
    assert "free port" in message and "inside this folder only" in message and "with docker" in message
    assert terminal_core._title(data, "Loo", None) == "Run Loo"


def test_the_button_runs_only_a_copy(app, signed_in, tmp_path, monkeypatch):
    from app.features.recap import facts_core

    monkeypatch.setattr(facts_core, "repositories", list)
    main = _clone(tmp_path / "loo", ("origin", "https://github.com/Look/loo.git"))
    with app.app_context():
        projects_core.create(ProjectCreate(name="Loo", local_path=str(main)))
    started = []
    monkeypatch.setattr(
        terminal_core, "start", lambda data: started.append(data) or type("S", (), {"id": "x"})()
    )
    assert "Run with Claude" in signed_in.get("/projects/loo?tab=git").data.decode()
    signed_in.post("/projects/loo/git/run", data={"folder": str(main)})
    assert started[0].preset == "run" and started[0].folder == str(main)
    refused = signed_in.post("/projects/loo/git/run", data={"folder": "/"}, follow_redirects=True)
    assert b"not a copy of the project" in refused.data and len(started) == 1
