"""A paused project is out of what to do until resumed (D-095)."""

from app.core.schema.planning import ProjectCreate, ProjectUpdate, TaskCreate
from app.features.graph import graph_core
from app.features.projects import projects_core
from app.features.tasks import tasks_core


def test_paused_is_left_out_then_back(ctx):
    live = projects_core.create(ProjectCreate(name="Live"))
    rest = projects_core.create(ProjectCreate(name="Rest"))
    tasks_core.create(TaskCreate(title="Do this", project_id=live.id))
    tasks_core.create(TaskCreate(title="Later", project_id=rest.id))
    tasks_core.create(TaskCreate(title="Loose"))
    projects_core.update(rest.id, ProjectUpdate(status="paused"))
    assert {t.title for t in tasks_core.next_actions()} == {"Do this", "Loose"}
    assert {t.title for t in tasks_core.list_tasks({}).items} == {"Do this", "Loose"}
    assert [t.title for t in tasks_core.list_tasks({"project": str(rest.id)}).items] == ["Later"]
    assert [t.title for t in tasks_core.next_actions(project_id=rest.id)] == ["Later"]
    assert "Rest" not in {n["data"]["label"] for n in graph_core.project_plan()["nodes"]}
    projects_core.update(rest.id, ProjectUpdate(status="active"))
    assert "Later" in {t.title for t in tasks_core.next_actions()}


def test_the_buttons_and_tasks_first(app, signed_in):
    with app.app_context():
        projects_core.create(ProjectCreate(name="Rest"))
    page = signed_in.get("/projects/rest").data.decode()
    assert 'id="tasks"' in page and "Pause: out of what to do" in page
    done = signed_in.post("/projects/rest/pause", follow_redirects=True).data.decode()
    assert "paused: out of what to do" in done and "Resume it" in done
    assert b"resumed" in signed_in.post("/projects/rest/resume", follow_redirects=True).data
