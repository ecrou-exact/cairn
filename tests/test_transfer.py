"""A project from one machine to another (D-084)."""

import io

import pytest

from app import create_app
from app.core.extensions import db
from app.core.schema.comments import CommentCreate
from app.core.schema.planning import DependencyCreate, ProjectCreate, TaskCreate, TaskUpdate
from app.core.schema.worklinks import WorkLinkCreate
from app.features.comments import comments_core
from app.features.projects import projects_core, transfer_core
from app.features.tasks import dependencies_core, tasks_core
from app.features.worklinks import worklinks_core


def _work_machine():
    project = projects_core.create(ProjectCreate(name="Loo", local_path="/work/loo"))
    first = tasks_core.create(TaskCreate(title="Tree", project_id=project.id))
    sub = tasks_core.create(TaskCreate(title="Leaves", project_id=project.id, parent_id=first.id))
    then = tasks_core.create(TaskCreate(title="Ship", project_id=project.id))
    dependencies_core.add(DependencyCreate(from_task_id=first.id, to_task_id=then.id, kind="blocks"))
    comments_core.create(
        CommentCreate(target_type="task", target_id=sub.id, kind="comment", body_md="half done")
    )
    worklinks_core.add(WorkLinkCreate(target_type="task", target_id=first.id, kind="branch", ref="tree"))
    db.session.commit()
    return project, first, then


@pytest.fixture()
def home(tmp_path):
    other = create_app("testing")
    other.config["CAIRN_DATA_DIR"] = tmp_path / "home"
    other.config["CAIRN_UPLOAD_DIR"] = tmp_path / "home" / "uploads"
    other.config["CAIRN_DATA_DIR"].mkdir()
    with other.app_context():
        db.create_all()
    yield other
    with other.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_a_project_goes_home_and_back(ctx, home):
    project, first, then = _work_machine()
    blob = transfer_core.export(project)
    with home.app_context():
        seen = transfer_core.preview(blob, "/home/loo")
        assert not seen["exists"] and seen["counts"]["task"]["new"] == 3
        assert projects_core.options() == []  # nothing written by the preview
        there, _ = transfer_core.bring(blob, "/home/loo")
        assert there.local_path == "/home/loo" and len(tasks_core.subtasks(first.id)) == 1
        assert db.session.get(type(first), then.id).blocked_by_count == 1
        assert [w["ref"] for w in worklinks_core.for_target("task", first.id, deep=False)["own"]] == ["tree"]
        tasks_core.update(then.id, TaskUpdate(title="Ship 2.0"))
        db.session.commit()
        back = transfer_core.export(db.session.get(type(project), project.id))
    tasks_core.update(first.id, TaskUpdate(title="Tree, newer here"))
    db.session.commit()
    seen = transfer_core.preview(back)
    assert seen["exists"] and seen["counts"]["task"]["updated"] == 1 and seen["counts"]["task"]["kept"] >= 1
    transfer_core.bring(back)
    assert tasks_core.get_task(then.id).title == "Ship 2.0"
    assert tasks_core.get_task(first.id).title == "Tree, newer here"
    assert projects_core.get_project(project.id).local_path == "/work/loo"  # this machine's own


def test_what_is_not_a_project_file_is_refused(ctx):
    for blob in (b"nope", b'{"cairn_export": 9}', b'{"cairn_export": 1, "tables": {}}'):
        with pytest.raises(transfer_core.TransferError):
            transfer_core.read(blob)


def test_pages(app, signed_in):
    with app.app_context():
        _work_machine()
    blob = signed_in.get("/projects/loo/export").data
    assert blob[:2] == b"\x1f\x8b"
    shown = signed_in.post("/projects/import", data={"file": (io.BytesIO(blob), "loo.cairn")})
    page = shown.data.decode()
    assert "brought up to date" in page
    token = page.split("/projects/import/")[1][:32]
    done = signed_in.post(f"/projects/import/{token}", follow_redirects=True).data.decode()
    assert "is up to date with the file" in done
    assert b"no longer waiting" in signed_in.post(f"/projects/import/{token}", follow_redirects=True).data
    bad = signed_in.post("/projects/import", data={"file": (io.BytesIO(b"x"), "x")}, follow_redirects=True)
    assert b"not a file exported by Cairn" in bad.data
    assert signed_in.post("/projects/import/../x").status_code == 404


def test_the_exchange_folder(app, signed_in, tmp_path):
    from app.core.utils.settings import set_setting

    with app.app_context():
        _work_machine()
    assert (
        b"Set an exchange folder" in signed_in.post("/projects/loo/export/save", follow_redirects=True).data
    )
    shared = tmp_path / "shared"
    shared.mkdir()
    with app.app_context():
        set_setting("projects.transfer_folder", str(shared))
        db.session.commit()
    assert (
        b"Saved in the exchange folder"
        in signed_in.post("/projects/loo/export/save", follow_redirects=True).data
    )
    (name,) = [p.name for p in shared.iterdir()]
    assert name in signed_in.get("/projects/import").data.decode()
    seen = signed_in.post("/projects/import", data={"name": name}).data.decode()
    assert "brought up to date" in seen
    assert (
        b"not in the exchange folder"
        in signed_in.post("/projects/import", data={"name": "../x.cairn"}, follow_redirects=True).data
    )
