import re
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.core.db_class.planning import ExternalCondition
from app.core.extensions import db
from app.core.schema.planning import ConditionCreate, TaskCreate
from app.core.utils import history
from app.core.utils.history import batch
from app.features.tasks import brief_core, conditions_core, tasks_core
from app.features.tasks.dependencies_core import refresh_derived


def test_a_condition_blocks_until_it_happens(ctx):
    task = tasks_core.create(TaskCreate(title="Upgrade to flask 3.2"))
    with batch() as added:
        condition = conditions_core.add(
            ConditionCreate(
                task_id=task.id, kind="release", label="flask 3.2", url="https://pypi.org/project/flask/"
            )
        )
    assert task.is_blocked
    line = "Waiting for (upstream release): flask 3.2 <https://pypi.org/project/flask/>"
    assert line in brief_core.task_brief(task)
    assert task.id not in [t.id for t in tasks_core.next_actions()]
    with batch() as resolved:
        conditions_core.set_resolved(condition.id, True)
    assert not task.is_blocked
    history.undo(resolved)
    assert task.is_blocked
    history.undo(added)
    assert not task.is_blocked and db.session.get(ExternalCondition, condition.id) is None


def test_a_date_condition_lifts_itself(ctx):
    task = tasks_core.create(TaskCreate(title="Announce the release"))
    soon = date.today() + timedelta(days=3)
    conditions_core.add(ConditionCreate(task_id=task.id, kind="date", label="embargo ends", until_on=soon))
    assert task.is_blocked
    refresh_derived(today=soon)
    assert not task.is_blocked
    with pytest.raises(ValidationError):
        ConditionCreate(task_id=task.id, kind="date", label="no day")
    with pytest.raises(ValidationError):
        ConditionCreate(task_id=task.id, label="x", url="javascript:alert(1)")


def test_purging_a_task_removes_its_conditions(ctx):
    task = tasks_core.create(TaskCreate(title="Wait"))
    conditions_core.add(ConditionCreate(task_id=task.id, kind="review", label="Alex"))
    tasks_core.delete(task.id)
    tasks_core.purge(task.id)
    assert db.session.query(ExternalCondition).count() == 0


def test_condition_page_and_api(app, signed_in):
    with app.app_context():
        task_id = tasks_core.create(TaskCreate(title="Merge the docs")).id
    here = f"/tasks/{task_id}"
    pr = {"kind": "pr", "label": "PR #42", "url": "https://github.com/a/b/pull/42"}
    signed_in.post(f"{here}/conditions", data=pr)
    page = signed_in.get(here)
    assert b"Why it is blocked" in page.data and b"PR #42" in page.data
    assert b"style=" not in page.data
    signed_in.post(f"{here}/conditions", data={"kind": "date", "label": "no day"})
    assert b"until which day" in signed_in.get(here).data
    with app.app_context():
        condition_id = conditions_core.for_task(task_id)[0].id
    signed_in.post(f"{here}/conditions/{condition_id}/resolved", data={"resolved": "1"})
    assert b"Why it is blocked" not in signed_in.get(here).data
    signed_in.post(f"{here}/conditions/{condition_id}/remove")
    undo = re.search(rb"/history/([0-9a-f-]{36})/undo", signed_in.get(here).data).group(1).decode()
    signed_in.post(f"/history/{undo}/undo")

    created = signed_in.post(
        "/api/conditions", json={"task_id": str(task_id), "kind": "review", "label": "Sam"}
    )
    assert created.status_code == 201
    cid = created.json["condition"]["id"]
    assert signed_in.get(f"/api/tasks/{task_id}").json["is_blocked"] is True
    assert signed_in.patch(f"/api/conditions/{cid}", json={"resolved": True}).json["condition"]["resolved_at"]
    assert len(signed_in.get(f"/api/tasks/{task_id}/conditions").json["items"]) == 2
    assert signed_in.delete(f"/api/conditions/{cid}").status_code == 200
    assert signed_in.delete(f"/api/conditions/{cid}").status_code == 404
