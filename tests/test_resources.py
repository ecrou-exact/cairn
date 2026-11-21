import io
import os
import re
import time
import uuid

import pytest
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import select

from app.core.db_class.job import Job
from app.core.db_class.resource import Resource, ResourceLink
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.schema.planning import ProjectCreate, TaskCreate
from app.core.schema.resources import LinkCreate, ResourceCreate, ResourceUpdate
from app.core.utils import history
from app.core.utils.history import batch
from app.core.utils.settings import set_setting
from app.core.utils.web import local_path
from app.features.projects import projects_core
from app.features.resources import preview_core, resources_core, storage_core
from app.features.search import search_core
from app.features.tasks import tasks_core


def _task(title="Fix login"):
    return tasks_core.create(TaskCreate(title=title))


def _png(with_exif: bool = False, fmt: str = "PNG") -> bytes:
    image = Image.new("RGB", (40, 30), (200, 80, 40))
    out = io.BytesIO()
    if with_exif:
        exif = Image.Exif()
        exif[0x010F] = "SecretCam"  # Make
        exif[0x8825] = {2: (48.0, 51.0, 24.0)}  # GPS latitude
        image.save(out, format=fmt, exif=exif)
    else:
        image.save(out, format=fmt)
    return out.getvalue()


# -- schemas and pure helpers ----------------------------------------------------------------


def test_create_schema_checks_each_kind():
    assert ResourceCreate(kind="url", url="https://example.org/docs").title is None
    for bad in (
        {"kind": "url"},
        {"kind": "url", "url": "javascript:alert(1)"},
        {"kind": "url", "url": "file:///etc/passwd"},
        {"kind": "github", "url": "https://gitlab.com/a/b"},
        {"kind": "note", "title": "Empty"},
        {"kind": "snippet", "title": "x", "body": "  "},
        {"kind": "file", "title": "x"},
        {"kind": "image", "title": "x"},
        {"kind": "note", "body": "no title"},
        {"kind": "tool", "title": "Nothing to start"},
    ):
        with pytest.raises(ValidationError):
            ResourceCreate(**bad)
    assert ResourceCreate(kind="tool", title="psql", body="psql -h localhost").body


def test_github_references():
    ref = preview_core.github_ref("https://github.com/ecrou-exact/cairn/pull/42/files")
    assert ref == {"repo": "ecrou-exact/cairn", "item": "pull request", "number": 42}
    file_ref = preview_core.github_ref("https://github.com/a/b/blob/0123abc/docs/x.md")
    assert file_ref["item"] == "file" and file_ref["path"] == "docs/x.md" and file_ref["ref"] == "0123abc"
    assert preview_core.github_title(file_ref) == "a/b: docs/x.md"
    assert preview_core.github_ref("https://example.org/a/b") is None


def test_page_head_parsing_prefers_open_graph():
    html = (
        "<html><head><title> Plain  title </title>"
        '<meta property="og:title" content="OG &amp; title">'
        '<meta name="description" content="What it is"><meta property="og:site_name" content="Site">'
        "</head><body><title>not this</title></body></html>"
    )
    assert preview_core.parse_head(html) == {
        "title": "OG & title",
        "description": "What it is",
        "site": "Site",
    }
    assert preview_core.parse_head("<title>Only</title>") == {"title": "Only"}


def test_local_path_refuses_other_sites():
    assert local_path("/tasks?state=open") == "/tasks?state=open"
    for bad in ("https://evil.example", "//evil.example", "javascript:alert(1)", "/\\evil", ""):
        assert local_path(bad) == ""


# -- core ------------------------------------------------------------------------------------


def test_link_gets_title_github_facts_and_a_preview_job(ctx):
    resource = resources_core.create(ResourceCreate(kind="github", url="https://github.com/a/b/issues/7"))
    assert resource.title == "a/b#7"
    assert resource.meta["github"]["number"] == 7
    job = db.session.scalar(select(Job).where(Job.type == "resources.preview"))
    assert job.status == "queued" and job.payload == {"resource_id": str(resource.id)}

    set_setting("resources.previews", False)
    plain = resources_core.create(ResourceCreate(kind="url", url="https://example.org/guide/"))
    assert plain.title == "example.org/guide"
    assert db.session.query(Job).filter_by(type="resources.preview").count() == 1


def test_preview_job_fills_the_meta(ctx, monkeypatch):
    resource = resources_core.create(ResourceCreate(kind="url", url="https://example.org"))
    monkeypatch.setattr(preview_core, "fetch", lambda url: {"title": "Example Domain"})
    job = jobs_core.claim_next("io", "test")
    jobs_core.run(job)
    db.session.refresh(resource)
    assert resource.meta["preview"]["title"] == "Example Domain"
    resources_core.use_preview_title(resource.id)
    assert resource.title == "Example Domain"

    def fail(url):
        raise preview_core.PreviewError("The site answered 404.")

    monkeypatch.setattr(preview_core, "fetch", fail)
    resources_core.refresh_preview(resource.id)
    jobs_core.run(jobs_core.claim_next("io", "test"))
    db.session.refresh(resource)
    assert resource.meta["preview"]["error"] == "The site answered 404."


def test_undo_of_a_new_link_cancels_its_preview(ctx):
    with batch() as batch_id:
        resource = resources_core.create(ResourceCreate(kind="url", url="https://example.org"))
    history.undo(batch_id)
    assert resource.is_deleted
    assert db.session.scalar(select(Job.status).where(Job.type == "resources.preview")) == "cancelled"


def test_attach_detach_and_undo(ctx):
    task = _task()
    note = resources_core.create(ResourceCreate(kind="note", title="How to deploy", body="# Steps"))
    target = LinkCreate(target_type="task", target_id=task.id)
    with batch() as attached:
        link = resources_core.attach(note.id, target)
    with pytest.raises(resources_core.ResourceError, match="already attached"):
        resources_core.attach(note.id, target)
    assert [r.id for _, r in resources_core.for_target("task", task.id)] == [note.id]
    with batch() as detached:
        resources_core.detach(link.id)
    assert resources_core.for_target("task", task.id) == []
    history.undo(detached)
    assert len(resources_core.for_target("task", task.id)) == 1
    history.undo(attached)  # the first link is gone, but its target and resource are known
    with pytest.raises(resources_core.ResourceError, match="does not exist"):
        resources_core.attach(note.id, LinkCreate(target_type="task", target_id=uuid.uuid4()))


def test_update_keeps_kind_rules(ctx):
    snippet = resources_core.create(
        ResourceCreate(kind="snippet", title="Query", body="select 1", language="sql")
    )
    with pytest.raises(resources_core.ResourceError, match="Write the content"):
        resources_core.update(snippet.id, ResourceUpdate(body=""))
    with batch() as batch_id:
        resources_core.update(snippet.id, ResourceUpdate(title="Count rows", body="select count(*)"))
    history.undo(batch_id)
    assert (snippet.title, snippet.body) == ("Query", "select 1")


def test_upload_stores_once_and_reuses(ctx):
    task = _task()
    first, new = resources_core.upload(io.BytesIO(b"hello\n"), "../../notes.txt", None)
    assert new and first.kind == "file" and first.original_name == "notes.txt"
    path = storage_core.path_of(first.stored_name)
    assert path.read_bytes() == b"hello\n" and path.is_relative_to(storage_core.root())
    again, new = resources_core.upload(
        io.BytesIO(b"hello\n"), "copy.txt", LinkCreate(target_type="task", target_id=task.id)
    )
    assert not new and again.id == first.id
    assert len(list(storage_core.root().glob("*/*"))) == 1
    assert [r.id for _, r in resources_core.for_target("task", task.id)] == [first.id]


def test_upload_limits(ctx):
    set_setting("resources.max_upload_mb", 1)
    with pytest.raises(storage_core.StorageError, match="larger than 1 MB"):
        resources_core.upload(io.BytesIO(b"x" * (1024 * 1024 + 1)), "big.bin", None)
    with pytest.raises(storage_core.StorageError, match="empty"):
        resources_core.upload(io.BytesIO(b""), "empty.txt", None)
    assert list(storage_core.root().glob("**/*.*")) == []
    assert [p for p in storage_core.root().rglob("*") if p.is_file()] == []
    with pytest.raises(storage_core.StorageError):
        storage_core.path_of("../../etc/passwd")


def test_images_are_reencoded_without_metadata(ctx):
    jpeg, _ = resources_core.upload(io.BytesIO(_png(with_exif=True, fmt="JPEG")), "holiday.jpeg", None)
    assert jpeg.kind == "image" and jpeg.mime == "image/jpeg" and jpeg.original_name == "holiday.jpg"
    assert jpeg.meta["image"] == {"width": 40, "height": 30}
    with Image.open(storage_core.path_of(jpeg.stored_name)) as stored:
        assert not stored.getexif()
    fake, _ = resources_core.upload(io.BytesIO(b"GIF89a<script>alert(1)</script>"), "x.gif", None)
    assert fake.kind == "file" and fake.mime == "image/gif"  # kept, but only ever downloaded


def test_trash_restore_and_purge_remove_the_file(ctx):
    task = _task()
    resource, _ = resources_core.upload(
        io.BytesIO(_png()), "shot.png", LinkCreate(target_type="task", target_id=task.id)
    )
    path = storage_core.path_of(resource.stored_name)
    resources_core.delete(resource.id)
    assert resources_core.for_target("task", task.id) == []
    assert [r.id for r in resources_core.deleted_resources()] == [resource.id]
    resources_core.restore(resource.id)
    assert len(resources_core.for_target("task", task.id)) == 1
    resources_core.delete(resource.id)
    resources_core.purge(resource.id)
    assert not path.exists()
    assert db.session.scalar(select(ResourceLink)) is None


def test_purging_a_task_or_project_drops_its_links(ctx):
    project = projects_core.create(ProjectCreate(name="Rulezet"))
    task = tasks_core.create(TaskCreate(title="Ship", project_id=project.id))
    note = resources_core.create(ResourceCreate(kind="note", title="Runbook", body="steps"))
    resources_core.attach(note.id, LinkCreate(target_type="task", target_id=task.id))
    resources_core.attach(note.id, LinkCreate(target_type="project", target_id=project.id))
    projects_core.delete(project.id)
    projects_core.purge(project.id)
    assert db.session.scalar(select(ResourceLink)) is None
    assert not db.session.get(Resource, note.id).is_deleted  # the library keeps it


def test_orphan_files_are_cleaned(ctx):
    kept, _ = resources_core.upload(io.BytesIO(b"keep"), "keep.txt", None)
    stray = storage_core.root() / "ab" / ("ab" + "0" * 30)
    stray.parent.mkdir(exist_ok=True)
    stray.write_bytes(b"left over")
    old = time.time() - 3 * 86400
    os.utime(stray, (old, old))
    os.utime(storage_core.path_of(kept.stored_name), (old, old))
    assert storage_core.remove_orphan_files() == 1
    assert storage_core.path_of(kept.stored_name).exists() and not stray.exists()


def test_search_and_library_filters(ctx):
    task = _task()
    note = resources_core.create(ResourceCreate(kind="note", title="Deploy runbook", body="x"))
    resources_core.create(ResourceCreate(kind="url", url="https://docs.example.org/deploy"))
    resources_core.attach(note.id, LinkCreate(target_type="task", target_id=task.id))
    assert len(search_core.search("deploy")["resources"]) == 2
    assert [r.id for r in resources_core.list_resources({"used": "yes"}).items] == [note.id]
    assert [r.kind for r in resources_core.list_resources({"kind": "url"}).items] == ["url"]
    assert resources_core.list_resources({"sort": "uses", "dir": "desc"}).items[0].id == note.id


# -- pages and API ---------------------------------------------------------------------------


def _seed(app):
    with app.app_context():
        project = projects_core.create(ProjectCreate(name="Rulezet"))
        task = tasks_core.create(TaskCreate(title="Fix login", project_id=project.id))
        set_setting("resources.previews", False)
        made = [
            resources_core.create(ResourceCreate(kind="url", url="https://example.org")),
            resources_core.create(ResourceCreate(kind="github", url="https://github.com/a/b/pull/3")),
            resources_core.create(ResourceCreate(kind="note", title="Note", body="# Hi")),
            resources_core.create(
                ResourceCreate(kind="snippet", title="SQL", body="select 1", language="sql")
            ),
            resources_core.create(ResourceCreate(kind="tool", title="DB", body="psql", url="https://x.org")),
            resources_core.create(ResourceCreate(kind="file", title="Spec", path="/srv/spec.pdf")),
            resources_core.upload(io.BytesIO(_png()), "shot.png", None)[0],
            resources_core.upload(io.BytesIO(b"%PDF-1.4"), "doc.pdf", None)[0],
        ]
        for resource in made:
            resources_core.attach(resource.id, LinkCreate(target_type="task", target_id=task.id))
        return project.slug, task.id, [r.id for r in made]


def test_every_resource_page_renders(app, signed_in):
    slug, task_id, ids = _seed(app)
    urls = [
        "/resources",
        "/resources?view=table&sort=uses",
        f"/tasks/{task_id}",
        f"/projects/{slug}",
        "/trash",
    ]
    urls += [
        f"/resources/new?kind={k}&attach=task:{task_id}"
        for k in ("url", "github", "note", "snippet", "tool", "file")
    ]
    urls += [f"/resources/{rid}" for rid in ids] + [f"/resources/{rid}/edit" for rid in ids]
    for url in urls:
        response = signed_in.get(url)
        assert response.status_code == 200, url
        assert b"<style" not in response.data and b"style=" not in response.data, url
    assert signed_in.get("/resources/new?kind=image").status_code == 404
    assert signed_in.get(f"/resources/{uuid.uuid4()}").status_code == 404
    back = signed_in.get("/resources/new?kind=note&next=javascript:alert(1)")
    assert b"javascript:" not in back.data


def test_files_are_served_safely(app, signed_in):
    _, _, ids = _seed(app)
    with signed_in.get(f"/resources/{ids[6]}/file") as image:  # a streamed file: close it
        assert image.mimetype == "image/png" and "sandbox" in image.headers["Content-Security-Policy"]
        assert image.headers["X-Content-Type-Options"] == "nosniff"
        assert image.data[1:4] == b"PNG"
    with signed_in.get(f"/resources/{ids[7]}/file") as document:
        assert document.mimetype == "application/octet-stream"
        assert document.headers["Content-Disposition"].startswith("attachment")
    assert signed_in.get(f"/resources/{ids[0]}/file").status_code == 404


def test_upload_form_and_panel_actions(app, signed_in):
    _, task_id, _ = _seed(app)
    here = f"/tasks/{task_id}"
    response = signed_in.post(
        "/resources/upload",
        data={"files": [(io.BytesIO(b"a,b\n1,2\n"), "data.csv")], "attach": f"task:{task_id}", "next": here},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302 and response.location.endswith(here)
    page = signed_in.get(here)
    assert "Uploaded “data.csv”".encode() in page.data
    signed_in.post("/resources/quick", data={"url": "not a url", "attach": f"task:{task_id}", "next": here})
    assert b"full web address" in signed_in.get(here).data
    signed_in.post(
        "/resources/quick", data={"url": "https://github.com/a/b/issues/9", "attach": f"task:{task_id}"}
    )
    created = signed_in.post(
        "/resources/new",
        data={"kind": "note", "title": "Plan", "body": "steps", "attach": f"task:{task_id}", "next": here},
    )
    assert created.location.endswith(here)
    assert "Added “Plan”".encode() in signed_in.get(here).data
    with app.app_context():
        titles = [r.title for _, r in resources_core.for_target("task", task_id)]
        assert {"data.csv", "a/b#9", "Plan"} <= set(titles)
        link = db.session.scalar(select(ResourceLink).where(ResourceLink.target_id == task_id))
    signed_in.post(f"/resources/links/{link.id}/detach", data={"next": here})
    page = signed_in.get(here).data
    assert b"Detached" in page
    undo = re.search(rb"/history/([0-9a-f-]{36})/undo", page).group(1).decode()
    signed_in.post(f"/history/{undo}/undo", data={"next": here})
    with app.app_context():
        assert db.session.get(ResourceLink, link.id) is None  # restored as a new link
        assert len(resources_core.for_target("task", task_id)) == len(titles)


def test_resource_api(app, signed_in):
    _, task_id, _ = _seed(app)
    created = signed_in.post("/api/resources", json={"kind": "note", "title": "API note", "body": "x"})
    assert created.status_code == 201
    rid = created.json["resource"]["id"]
    assert signed_in.post("/api/resources", json={"kind": "url", "url": "ftp://x"}).status_code == 422
    assert signed_in.patch(f"/api/resources/{rid}", json={"tags": ["Ops"]}).json["resource"]["tags"] == [
        "ops"
    ]
    link = signed_in.post(
        f"/api/resources/{rid}/links", json={"target_type": "task", "target_id": str(task_id)}
    )
    assert link.status_code == 201
    listed = signed_in.get(f"/api/tasks/{task_id}/resources").json["items"]
    assert rid in [item["resource"]["id"] for item in listed]
    uploaded = signed_in.post(
        "/api/resources/upload",
        data={"file": (io.BytesIO(_png()), "again.png"), "attach": f"task:{task_id}"},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200 and uploaded.json["new"] is False  # same image as the seed
    assert signed_in.get("/api/resources?kind=image").json["total"] == 1
    assert signed_in.get("/api/search?q=api").json["resources"][0]["title"] == "API note"
    assert signed_in.delete(f"/api/resource-links/{link.json['link']['id']}").status_code == 200
    assert signed_in.delete(f"/api/resources/{rid}").status_code == 200
    assert signed_in.get(f"/api/resources/{rid}").status_code == 404
