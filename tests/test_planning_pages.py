import re
import uuid

from sqlalchemy import select

from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.features.projects import projects_core
from app.features.tasks import tasks_core


def _seed(app):
    with app.app_context():
        project = projects_core.create(
            ProjectCreate(name="Rulezet", description_md="# Rules\n\nThe **core**.")
        )
        task = tasks_core.create(TaskCreate(title="Fix login", project_id=project.id, description_md="Steps"))
        return project.slug, task.id


def _undo_batch(html: bytes) -> str:
    return re.search(rb"/history/([0-9a-f-]{36})/undo", html).group(1).decode()


def test_every_planning_page_renders(app, signed_in):
    slug, task_id = _seed(app)
    for url in (
        "/",
        "/tasks",
        "/tasks?view=cards&state=open&sort=due&dir=asc",
        f"/tasks/{task_id}",
        f"/tasks/{task_id}/edit",
        "/tasks/new",
        "/projects",
        "/projects?view=table",
        f"/projects/{slug}",
        f"/projects/{slug}/edit",
        "/projects/new",
        "/trash",
    ):
        response = signed_in.get(url)
        assert response.status_code == 200, url
        assert b"<style" not in response.data and b"style=" not in response.data, url
    assert signed_in.get(f"/tasks/{uuid.uuid4()}").status_code == 404
    assert signed_in.get("/projects/nope").status_code == 404


def test_quick_add_then_undo(app, signed_in):
    _seed(app)
    response = signed_in.post(
        "/tasks/quick", data={"text": "write docs for rulezet by tomorrow #docs !low", "next": "/tasks"}
    )
    assert response.status_code == 302 and response.location.endswith("/tasks")
    page = signed_in.get("/tasks")
    assert b"Added \xe2\x80\x9cwrite docs\xe2\x80\x9d" in page.data
    with app.app_context():
        task = db.session.scalar(select(Task).where(Task.title == "write docs"))
        assert (task.type, task.priority, task.project.slug) == ("docs", "low", "rulezet")
    signed_in.post(f"/history/{_undo_batch(page.data)}/undo", data={"next": "/tasks"})
    with app.app_context():
        assert db.session.scalar(select(Task).where(Task.title == "write docs")).is_deleted


def test_task_form_create_errors_and_edit(app, signed_in):
    _seed(app)
    bad = signed_in.post("/tasks/new", data={"title": "", "type": "feature", "priority": "medium"})
    assert bad.status_code == 422 and b"is-invalid" in bad.data
    created = signed_in.post(
        "/tasks/new",
        data={
            "title": "Ship v1",
            "type": "release",
            "priority": "high",
            "importance": "4",
            "urgency": "5",
            "due_on": "2030-01-15",
            "hard_deadline": "on",
            "estimate_hours": "3.5",
            "tags": "release, v1",
            "checklist": "[x] changelog\n[ ] tag",
        },
    )
    assert created.status_code == 302
    task_id = created.location.rsplit("/", 1)[1]
    with app.app_context():
        task = db.session.get(Task, uuid.UUID(task_id))
        assert (
            task.hard_deadline
            and task.estimate_hours == 3.5
            and task.checklist[0] == {"text": "changelog", "done": True}
        )
    form = signed_in.get(f"/tasks/{task_id}/edit").data
    assert b"[x] changelog" in form and b'value="2030-01-15"' in form
    signed_in.post(f"/tasks/{task_id}/checklist/1")
    with app.app_context():
        assert db.session.get(Task, uuid.UUID(task_id)).checklist[1]["done"]


def test_status_buttons_follow_the_workflow(app, signed_in):
    _, task_id = _seed(app)
    refused = signed_in.post(f"/tasks/{task_id}/status", data={"status": "in_review"}, follow_redirects=True)
    assert b"cannot go from" in refused.data
    signed_in.post(f"/tasks/{task_id}/status", data={"status": "in_progress"})
    with app.app_context():
        assert db.session.get(Task, task_id).status == "in_progress"


def test_dependencies_from_the_task_page(app, signed_in):
    _, task_id = _seed(app)
    with app.app_context():
        other = tasks_core.create(TaskCreate(title="Design schema")).id
    signed_in.post(f"/tasks/{task_id}/dependencies", data={"direction": "blocked_by", "other_id": str(other)})
    page = signed_in.get(f"/tasks/{task_id}").data
    assert b"Why it is blocked" in page and b"Design schema" in page
    cycle = signed_in.post(
        f"/tasks/{other}/dependencies",
        data={"direction": "blocked_by", "other_id": str(task_id)},
        follow_redirects=True,
    )
    assert b"would create a cycle" in cycle.data
    missing = signed_in.post(
        f"/tasks/{task_id}/dependencies", data={"direction": "blocks", "other_id": ""}, follow_redirects=True
    )
    assert b"Pick a task" in missing.data


def test_project_form_delete_and_trash(app, signed_in):
    created = signed_in.post(
        "/projects/new",
        data={
            "name": "Vitrine",
            "color": "sea",
            "status": "active",
            "weight": "1.5",
            "links": "Docs | https://example.org",
        },
    )
    assert created.status_code == 302 and created.location.endswith("/projects/vitrine")
    bad = signed_in.post("/projects/new", data={"name": "X", "github_repo": "not a repo", "color": "sea"})
    assert bad.status_code == 422 and b"github_repo-error" in bad.data
    signed_in.post("/tasks/quick", data={"text": "first release for vitrine"})
    signed_in.post("/projects/vitrine/delete")
    trash = signed_in.get("/trash").data
    assert b"Vitrine" in trash and b"first release" in trash
    with app.app_context():
        project_id = db.session.scalar(select(Project.id).where(Project.slug == "vitrine"))
    signed_in.post(f"/trash/projects/{project_id}/restore")
    assert signed_in.get("/projects/vitrine").status_code == 200
    signed_in.post("/projects/vitrine/delete")
    signed_in.post(f"/trash/projects/{project_id}/purge")
    with app.app_context():
        assert db.session.get(Project, project_id) is None
        assert db.session.scalar(select(Task).where(Task.title == "first release")) is None


def test_timer_from_the_pages(app, signed_in):
    _, task_id = _seed(app)
    signed_in.post(f"/tasks/{task_id}/timer/start")
    assert b"<cn-timer" in signed_in.get("/").data
    signed_in.post("/timer/stop", data={"next": "/"})
    assert b"<cn-timer" not in signed_in.get("/").data


def test_planning_api(app, signed_in):
    project = signed_in.post("/api/projects", json={"name": "API project"}).json["project"]
    task = signed_in.post("/api/tasks", json={"title": "API task", "project_id": project["id"]}).json["task"]
    assert task["status"] == "todo" and task["score"] > 0
    assert signed_in.post("/api/tasks", json={"title": "x", "type": "nope"}).status_code == 422
    assert signed_in.post("/api/tasks", json={"title": "x", "unknown": 1}).status_code == 422
    updated = signed_in.patch(f"/api/tasks/{task['id']}", json={"priority": "critical"}).json
    assert updated["task"]["priority"] == "critical"
    assert signed_in.post(f"/api/history/{updated['batch']}/undo").status_code == 200
    assert signed_in.get(f"/api/tasks/{task['id']}").json["priority"] == "medium"
    preview = signed_in.post("/api/tasks/parse", json={"text": "api task !high"}).json
    assert preview["title"] == "api task" and preview["similar"][0]["title"] == "API task"
    found = signed_in.get("/api/search?q=api").json
    assert found["projects"][0]["name"] == "API project" and found["tasks"][0]["title"] == "API task"
    listing = signed_in.get(f"/api/tasks?project={project['id']}&sort=priority").json
    assert listing["total"] == 1
    assert signed_in.post(f"/api/tasks/{task['id']}/status", json={"status": "in_review"}).status_code == 422
    assert signed_in.delete(f"/api/tasks/{uuid.uuid4()}").status_code == 404


def test_projects_as_cards_or_as_a_graph(signed_in):
    signed_in.post("/api/projects", json={"name": "Pandora"})
    cards, graph = signed_in.get("/projects").data, signed_in.get("/projects?mode=graph").data
    assert b"cn-project-cards" in cards and b"data-graph-canvas" not in cards
    assert b"data-graph-canvas" in graph and b"cn-project-cards" not in graph
