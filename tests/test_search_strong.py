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
