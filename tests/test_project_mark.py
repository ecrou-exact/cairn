"""A project's icon or picture, and its folder opened on the machine (D-067)."""

import io
import os
import time

import pytest
from PIL import Image

from app.core.schema.planning import ProjectCreate, ProjectUpdate
from app.features.projects import open_core, projects_core
from app.features.resources import storage_core


def _png(size=(80, 40)):
    out = io.BytesIO()
    Image.new("RGBA", size, (200, 40, 40, 0)).save(out, format="PNG")
    out.seek(0)
    return out


def test_icons_solid_or_brand():
    for icon in ("fa-rocket", "fa-brands fa-docker"):
        assert ProjectCreate(name="P", icon=icon).icon == icon
        assert len(icon) <= 40
    for bad in ("rocket", "fa-x onclick", "fa-solid fa-x"):
        with pytest.raises(ValueError):
            ProjectUpdate(icon=bad)


def test_a_picture_replaces_the_icon(app, signed_in):
    sent = {"name": "Pandora", "icon": "fa-brands fa-docker", "weight": "1", "status": "active"}
    made = signed_in.post("/projects/new", data={**sent, "color": "moss", "image": (_png(), "logo.png")})
    assert made.status_code == 302
    page = signed_in.get("/projects").data.decode()
    assert "/projects/pandora/image?v=" in page
    picture = signed_in.get("/projects/pandora/image")
    assert picture.mimetype == "image/png"
    with Image.open(io.BytesIO(picture.data)) as image:
        assert image.size == (256, 256) and image.mode == "RGBA"
    picture.close()
    with app.app_context():
        stored = projects_core.by_slug("pandora").image_name
        path = storage_core.path_of(stored)
        os.utime(path, (time.time() - 200_000,) * 2)
        storage_core.remove_orphan_files()
        assert path.is_file()  # known: the clean-up keeps it
    signed_in.post("/projects/pandora/edit", data={**sent, "color": "moss", "remove_image": "1"})
    assert signed_in.get("/projects/pandora/image").status_code == 404 and not path.exists()
    assert "fa-brands fa-docker" in signed_in.get("/projects").data.decode()
    bad = {**sent, "color": "moss", "image": (io.BytesIO(b"<svg onload=x>"), "x.png")}
    signed_in.post("/projects/pandora/edit", data=bad)
    assert signed_in.get("/projects/pandora/image").status_code == 404


def test_the_profile_picture_survives_the_clean_up(app, signed_in):
    signed_in.post("/account/profile/avatar", data={"avatar": (_png(), "me.png")})
    with app.app_context():
        for path in storage_core.root().glob("*/*"):
            os.utime(path, (time.time() - 200_000,) * 2)
        assert storage_core.remove_orphan_files() == 0
    shown = signed_in.get("/account/avatar")
    assert shown.status_code == 200
    shown.close()


def test_a_folder_is_opened_as_one_argument(ctx, tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(
        open_core.shutil, "which", lambda name: None if name == "systemd-run" else f"/bin/{name}"
    )
    monkeypatch.setattr(open_core.subprocess, "Popen", lambda argv, **k: started.append((argv, k)))
    folder = tmp_path / "my project; rm -rf"
    folder.mkdir()
    project = projects_core.create(ProjectCreate(name="P", local_path=str(folder)))
    open_core.open_folder(project, "editor")
    argv, options = started[0]
    assert argv == ["/bin/code", str(folder)] and "shell" not in options
    assert not [key for key in options["env"] if key.startswith("CAIRN_")]
    gone = projects_core.create(ProjectCreate(name="Gone", local_path=str(tmp_path / "gone")))
    loose = projects_core.create(ProjectCreate(name="Loose"))
    for refused in (gone, loose):
        with pytest.raises(projects_core.ProjectError):
            open_core.open_folder(refused, "files")
    monkeypatch.setattr(open_core.shutil, "which", lambda name: None)
    with pytest.raises(projects_core.ProjectError, match="not found"):
        open_core.open_folder(project, "editor")


def test_the_folder_opens_by_post_only(signed_in, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(open_core, "open_folder", lambda project, kind: opened.append(kind))
    project = signed_in.post("/api/projects", json={"name": "P", "local_path": str(tmp_path)}).json["project"]
    page = signed_in.get(f"/projects/{project['slug']}").data
    assert b"/open/files" in page and b"VS Code" in page
    assert signed_in.get("/projects/p/open/files").status_code == 405
    assert signed_in.post("/projects/p/open/editor").status_code == 302 and opened == ["editor"]
    assert signed_in.post("/projects/p/open/other").status_code == 404
