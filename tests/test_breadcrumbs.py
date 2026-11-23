"""Where you are, on every page (D-094)."""

from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.projects import projects_core
from app.features.tasks import tasks_core


def _trail(page):
    return page.split('class="cn-trail"')[1].split("</nav>")[0] if 'class="cn-trail"' in page else ""


def test_the_trail(app, signed_in):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Loo"))
        task = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
        sub = tasks_core.create(TaskCreate(title="Leaves", project_id=project.id, parent_id=task.id))
        sub_id = str(sub.id)
    trail = _trail(signed_in.get(f"/tasks/{sub_id}?tab=git").data.decode())
    for part in ('href="/projects"', 'href="/projects/loo"', ">Tree<", ">Leaves<", ">Git<"):
        assert part in trail
    assert ">Bring in<" in _trail(signed_in.get("/projects/loo/bring").data.decode())
    assert ">Rules<" in _trail(signed_in.get("/day/rules").data.decode())
    assert _trail(signed_in.get("/projects").data.decode()) == ""  # a section's own page needs none
