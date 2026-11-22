import re
import uuid

import pytest
from sqlalchemy import select

from app.core.db_class.comment import Comment
from app.core.extensions import db
from app.core.schema.comments import CommentCreate, CommentUpdate
from app.core.schema.planning import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate
from app.core.schema.resources import LinkCreate, ResourceCreate
from app.core.utils import history
from app.core.utils.history import batch
from app.core.utils.settings import set_setting
from app.features.comments import comments_core
from app.features.projects import projects_core
from app.features.resources import resources_core
from app.features.tasks import brief_core, tasks_core


def _family():
    project = projects_core.create(ProjectCreate(name="Rulezet", github_repo="ecrou-exact/rulezet"))
    parent = tasks_core.create(TaskCreate(title="Release v2", project_id=project.id))
    task = tasks_core.create(
        TaskCreate(title="Write the changelog", project_id=project.id, parent_id=parent.id)
    )
    return project, parent, task


def _say(target, text, kind="comment"):
    target_type = "project" if hasattr(target, "slug") else "task"
    return comments_core.create(
        CommentCreate(target_type=target_type, target_id=target.id, kind=kind, body_md=text)
    )


def test_comment_lifecycle_and_undo(ctx):
    _, _, task = _family()
    with batch() as created:
        comment = _say(task, "First *draft*")
    assert comment.created_by == "user" and comments_core.author_label(comment.created_by) == "You"
    with batch() as edited:
        comments_core.update(comment.id, CommentUpdate(body_md="Second draft"))
    assert comment.edited_at is not None
    history.undo(edited)
    assert comment.body_md == "First *draft*"
    history.undo(created)
    assert comment.is_deleted and comments_core.for_target("task", task.id) == []
    comments_core.restore(comment.id)
    comments_core.delete(comment.id)
    assert [c.id for c in comments_core.deleted_comments()] == [comment.id]
    comments_core.purge(comment.id)
    assert db.session.get(Comment, comment.id) is None
    with pytest.raises(comments_core.CommentError):
        comments_core.create(CommentCreate(target_type="task", target_id=uuid.uuid4(), body_md="x"))


def test_corrections_come_from_project_parents_and_task(ctx):
    project, parent, task = _family()
    _say(project, "Commits follow gitchangelog: `new: [scope] message`.", "correction")
    _say(parent, "Never bump the major version.", "correction")
    own = _say(task, "Write it in English.", "correction")
    _say(task, "Just a note, not for Claude.")
    retired = _say(task, "Use a table.", "correction")
    comments_core.update(retired.id, CommentUpdate(active=False))
    found = comments_core.corrections_for_task(task, tasks_core.ancestors(task))
    assert [source for source, _ in found] == ["project Rulezet", "parent task Release v2", "this task"]
    assert found[-1][1].id == own.id


def test_brief_has_everything_a_run_needs(ctx):
    project, _parent, task = _family()
    projects_core.update(project.id, ProjectUpdate(claude_instructions_md="Run `manage.py check` first."))
    tasks_core.update(
        task.id,
        TaskUpdate(
            description_md="Summarise the merged PRs.",
            acceptance_md="- every PR listed",
            claude_instructions_md="Keep it short.",
            checklist=[{"text": "collect PRs", "done": True}, {"text": "write"}],
        ),
    )
    _say(project, "No AI attribution in commits.", "correction")
    set_setting("resources.previews", False)
    snippet = resources_core.create(
        ResourceCreate(kind="snippet", title="Log", body="git log ```weird``` --oneline", language="bash")
    )
    resources_core.attach(snippet.id, LinkCreate(target_type="task", target_id=task.id))
    docs = resources_core.create(ResourceCreate(kind="url", url="https://keepachangelog.com", title="Guide"))
    resources_core.attach(docs.id, LinkCreate(target_type="project", target_id=project.id))

    text = brief_core.task_brief(task)
    for expected in (
        "# Task: Write the changelog",
        "repository `ecrou-exact/rulezet`",
        "Part of: Release v2",
        "## What to do",
        "- [x] collect PRs",
        "### From the project Rulezet",
        "### For this task",
        "No AI attribution in commits.",
        "**Guide** (link): <https://keepachangelog.com>",
        "````bash",
    ):
        assert expected in text, expected
    assert text.index("From the project") < text.index("For this task")
    assert brief_core.fence("a ``` b").startswith("````")


def test_comment_pages_and_actions(app, signed_in):
    with app.app_context():
        project, _, task = _family()
        slug, task_id = project.slug, task.id
    here = f"/tasks/{task_id}"
    signed_in.post(
        "/comments",
        data={"target": f"task:{task_id}", "body_md": "Use **pytest**", "kind": "correction", "next": here},
    )
    page = signed_in.get(f"{here}?tab=discussion")  # the task page in tabs (D-047)
    assert b"Correction kept" in page.data and b"Claude gets 1 correction" in page.data
    assert b"Brief for Claude" in signed_in.get(f"{here}?tab=claude").data
    assert b"<style" not in page.data and b"style=" not in page.data
    assert b'aria-current="page"' in page.data and b"tab=discussion" in page.data
    with app.app_context():
        comment = db.session.scalar(select(Comment))
    assert signed_in.get(f"/comments/{comment.id}/edit").status_code == 200
    signed_in.post(f"/comments/{comment.id}/edit", data={"body_md": "Use pytest -q"})
    signed_in.post(f"/comments/{comment.id}/active", data={"active": "0", "next": here})
    with app.app_context():
        comment = db.session.get(Comment, comment.id)
        assert (comment.body_md, comment.kind, comment.active) == ("Use pytest -q", "comment", False)
    signed_in.post("/comments", data={"target": f"project:{uuid.uuid4()}", "body_md": "x"})
    assert signed_in.post("/comments", data={"target": "nope", "body_md": "x"}).status_code == 400
    signed_in.post(f"/comments/{comment.id}/delete", data={"next": here})
    undo = re.search(rb"/history/([0-9a-f-]{36})/undo", signed_in.get(here).data).group(1).decode()
    signed_in.post(f"/history/{undo}/undo")
    assert signed_in.get(f"/projects/{slug}").status_code == 200
    assert signed_in.get("/trash").status_code == 200
    brief = signed_in.get(f"/tasks/{task_id}/brief.md")
    assert brief.mimetype == "text/markdown" and b"# Task: Write the changelog" in brief.data


def test_comment_api(app, signed_in):
    with app.app_context():
        _, _, task = _family()
        task_id = task.id
    created = signed_in.post(
        "/api/comments",
        json={"target_type": "task", "target_id": str(task_id), "kind": "correction", "body_md": "Hi"},
    )
    assert created.status_code == 201 and created.json["comment"]["author"] == "You"
    cid = created.json["comment"]["id"]
    assert (
        signed_in.post(
            "/api/comments", json={"target_type": "task", "target_id": str(task_id), "body_md": ""}
        ).status_code
        == 422
    )
    assert signed_in.patch(f"/api/comments/{cid}", json={"active": False}).json["comment"]["active"] is False
    assert [c["id"] for c in signed_in.get(f"/api/tasks/{task_id}/comments").json["items"]] == [cid]
    assert "# Task: Write the changelog" in signed_in.get(f"/api/tasks/{task_id}/brief").json["markdown"]
    assert signed_in.delete(f"/api/comments/{cid}").status_code == 200
    assert signed_in.get(f"/api/tasks/{uuid.uuid4()}/brief").status_code == 404


def test_checklist_items_keep_done_false_on_update(ctx):
    task = tasks_core.create(TaskCreate(title="x"))
    tasks_core.update(task.id, TaskUpdate.model_validate({"checklist": [{"text": "a"}]}))
    assert task.checklist == [{"text": "a", "done": False}]


def test_related_tasks_resources_and_schedule(ctx):
    from datetime import date, timedelta

    from app.features.tasks import related_core

    set_setting("resources.previews", False)
    soon = date.today() + timedelta(days=14)
    task = tasks_core.create(
        TaskCreate(title="Write the release changelog", tags=["release"], due_on=soon, estimate_hours=2)
    )
    twin = tasks_core.create(TaskCreate(title="Write the release changelog again"))
    tagged = tasks_core.create(
        TaskCreate(title="Tag the version", tags=["release"], due_on=soon, estimate_hours=3)
    )
    tasks_core.create(TaskCreate(title="Unrelated thing about dogs"))
    sub = tasks_core.create(TaskCreate(title="Write the release changelog intro", parent_id=task.id))
    guide = resources_core.create(
        ResourceCreate(kind="url", url="https://keepachangelog.com", title="Changelog guide")
    )

    found = related_core.related_for(task)
    ids = [m.task.id for m in found.tasks]
    assert ids[0] == twin.id and tagged.id in ids and sub.id not in ids
    assert "almost the same title" in found.tasks[0].why
    assert [r.id for r, _ in found.resources] == [guide.id]
    assert found.schedule.booked_hours == 3 and found.schedule.booked_tasks == 1
    assert found.schedule.fits is True

    text = brief_core.task_brief(task)
    assert "## Possibly related" in text and "Changelog guide" in text and "\n\n## Subtasks\n\n" in text
