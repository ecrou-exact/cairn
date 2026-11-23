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


def test_quick_add_opens_the_full_form_with_the_same_words(signed_in):
    project = signed_in.post("/api/projects", json={"name": "Rulezet"}).json["project"]
    parent = signed_in.post("/api/tasks", json={"title": "Parent", "project_id": project["id"]}).json["task"]
    pages = ("/", "/tasks", f"/projects/{project['slug']}?tab=tasks", f"/tasks/{parent['id']}")
    for page in pages:  # wherever a task is added in one line
        assert "/tasks/quick/full" in signed_in.get(page).data.decode(), page
    words = {"text": "Fix the login +rulezet #bug !high ~2h", "csrf_token": "secret-token"}
    went = signed_in.post("/tasks/quick/full", data=words)
    assert went.status_code == 302 and "secret-token" not in went.location
    form = signed_in.get(went.location).data.decode()
    assert 'value="Fix the login"' in form
    for field, value in (("type", "bug"), ("priority", "high"), ("project_id", project["id"])):
        select = form.split(f'name="{field}"')[1].split("</select>")[0]
        chosen = [option for option in select.split("<option") if "selected" in option]
        assert len(chosen) == 1 and f'value="{value}"' in chosen[0], field
    assert 'name="estimate_hours"' in form and 'value="2"' in form
    child = signed_in.post("/tasks/quick/full", data={"text": "", "parent_id": parent["id"]})
    assert f"parent_id={parent['id']}" in child.location
    assert signed_in.get(child.location).status_code == 200
    odd = signed_in.get("/tasks/new?text=%3Cb%3Ex&project_id=nope")
    assert odd.status_code == 200 and b"&lt;b&gt;x" in odd.data
    assert len(signed_in.get("/api/tasks").json["items"]) == 1  # nothing was created


def test_quick_add_through_the_api(app, signed_in):
    from app.core.schema.planning import TaskCreate
    from app.features.tasks import tasks_core

    with app.app_context():
        parent = tasks_core.create(TaskCreate(title="Tree"))
        parent_id = str(parent.id)
    made = signed_in.post("/api/tasks/quick", json={"text": "leaf !high", "parent_id": parent_id})
    assert made.status_code == 201 and made.json["task"]["title"] == "leaf"
    with app.app_context():
        assert [t.title for t in tasks_core.subtasks(parent.id)] == ["leaf"]
    assert signed_in.post("/api/tasks/quick", json={"text": "#bug"}).status_code in (409, 422)
