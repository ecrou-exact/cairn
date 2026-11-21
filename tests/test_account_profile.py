import io

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.db_class.connection import Connection
from app.core.db_class.secret import Secret
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.security.secret_core import get_secret
from app.core.utils.settings import set_setting
from app.features.account import account_core
from app.features.connections import connections_core
from app.features.resources import preview_core, storage_core

TOKEN = "ghp_" + "x" * 36


def _drain():
    while (job := jobs_core.claim_next("io", "test")) is not None:
        jobs_core.run(job)


def _picture(fmt="PNG", size=(300, 200)) -> io.BytesIO:
    out = io.BytesIO()
    image = Image.new("RGB", size, (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"
    image.save(out, format=fmt, exif=exif)
    out.seek(0)
    return out


def test_profile_name_initials_and_picture(app, signed_in):
    page = signed_in.get("/account/profile")
    assert page.status_code == 200 and b"style=" not in page.data
    signed_in.post("/account/profile", data={"display_name": "  Ada   Lovelace ", "bio": "Writes rules."})
    with app.app_context():
        owner = account_core.get_owner()
        assert (owner.display_name, owner.initials, owner.bio) == ("Ada Lovelace", "AL", "Writes rules.")
    assert b">AL<" in signed_in.get("/").data  # initials in the header
    signed_in.post(
        "/account/profile/avatar",
        data={"avatar": (_picture("JPEG"), "me.jpg")},
        content_type="multipart/form-data",
    )
    with app.app_context():
        name = account_core.get_owner().avatar_name
        with Image.open(storage_core.path_of(name)) as stored:
            assert stored.size == (256, 256) and not stored.getexif()
    with signed_in.get("/account/avatar") as served:
        assert served.mimetype == "image/jpeg" and "sandbox" in served.headers["Content-Security-Policy"]
    bad = signed_in.post(
        "/account/profile/avatar", data={"avatar": (io.BytesIO(b"not an image"), "x.png")},
        content_type="multipart/form-data", follow_redirects=True,
    )  # fmt: skip
    assert b"Use a PNG, JPEG" in bad.data
    signed_in.post("/account/profile/avatar/remove")
    with app.app_context():
        assert account_core.get_owner().avatar_name is None
        assert not storage_core.path_of(name).exists()
    assert signed_in.get("/account/avatar").status_code == 404


def test_connection_lifecycle(ctx, monkeypatch):
    monkeypatch.setitem(
        connections_core.CHECKS, "github", lambda token: {"identity": "ada", "facts": {"scopes": ["repo"]}}
    )
    first = connections_core.add("github", "Work", TOKEN)
    assert first.is_default and first.state == "checking" and first.hint.endswith(TOKEN[-4:])
    assert get_secret(first.secret_name) == TOKEN
    assert TOKEN not in str(
        db.session.scalar(select(Secret).where(Secret.name == first.secret_name)).ciphertext
    )
    jobs_core.run(jobs_core.claim_next("io", "test"))
    db.session.refresh(first)
    assert (first.state, first.identity) == ("ok", "ada")
    assert connections_core.token_for("github") == TOKEN

    second = connections_core.add("github", "Personal", "ghp_" + "y" * 36)
    assert not second.is_default
    connections_core.make_default(second.id)
    assert connections_core.token_for("github").startswith("ghp_y")
    connections_core.remove(second.id)
    db.session.refresh(first)
    assert first.is_default and get_secret(f"connection:{second.id}") is None

    def refuse(token):
        raise connections_core.ConnectionError_("GitHub refused the token (revoked or mistyped).")

    monkeypatch.setitem(connections_core.CHECKS, "github", refuse)
    connections_core.request_check(first.id)
    _drain()
    db.session.refresh(first)
    assert first.state == "failed" and "refused" in first.error

    with pytest.raises(connections_core.ConnectionError_):
        connections_core.add("github", "x", "short")
    other = connections_core.add("other", "", "abc123456789")
    assert other.label == "Other service" and other.state == "unchecked"
    assert connections_core.token_for("anthropic") is None


def test_github_previews_use_the_connected_account(ctx, monkeypatch):
    from app.core.schema.resources import ResourceCreate
    from app.features.resources import resources_core

    monkeypatch.setitem(connections_core.CHECKS, "github", lambda token: {"identity": "ada", "facts": {}})
    connections_core.add("github", "Work", TOKEN)
    jobs_core.run(jobs_core.claim_next("io", "test"))
    seen = {}

    def api(ref, token):
        seen["token"] = token
        return {"title": "Fix the private thing", "site": "GitHub"}

    monkeypatch.setattr(preview_core, "github_api", api)
    monkeypatch.setattr(preview_core, "fetch", lambda url: pytest.fail("the public page must not be fetched"))
    set_setting("resources.previews", True)
    resource = resources_core.create(
        ResourceCreate(kind="github", url="https://github.com/acme/secret/issues/4")
    )
    jobs_core.run(jobs_core.claim_next("io", "test"))
    db.session.refresh(resource)
    assert seen["token"] == TOKEN and resource.meta["preview"]["title"] == "Fix the private thing"


def test_connections_page(app, signed_in, monkeypatch):
    assert signed_in.get("/connections").status_code == 200
    signed_in.post("/connections", data={"provider": "anthropic", "label": "", "token": "sk-ant-" + "z" * 40})
    page = signed_in.get("/connections")
    assert (
        b"Claude (Anthropic API)" in page.data and b"z" * 40 not in page.data and b"style=" not in page.data
    )
    with app.app_context():
        connection = db.session.scalar(select(Connection))
        cid = connection.id
    signed_in.post(f"/connections/{cid}/rename", data={"label": "Main key"})
    signed_in.post(f"/connections/{cid}/remove")
    with app.app_context():
        assert db.session.scalar(select(Connection)) is None
    assert signed_in.post("/connections", data={"provider": "nope", "token": "x"}).status_code == 400


def test_claude_code_on_this_machine(ctx, monkeypatch, tmp_path):
    import subprocess

    fake = tmp_path / "claude.exe"
    fake.write_text("not run")
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="2.1.330 (Claude Code)\n", stderr="")

    monkeypatch.setattr(connections_core.subprocess, "run", run)
    connection = connections_core.add("claude_code", "", "", str(fake))
    assert (
        connection.label == "Claude Code (this machine)" and connection.is_default and connection.hint == ""
    )
    _drain()
    db.session.refresh(connection)
    assert (connection.state, connection.identity) == ("ok", "2.1.330 (Claude Code)")
    assert calls == [[str(fake), "--version"]]  # an argv list, never a shell
    assert connections_core.claude_code_path() == str(fake)
    with pytest.raises(connections_core.ConnectionError_, match="no token"):
        connections_core.replace_token(connection.id, "x" * 20)
    with pytest.raises(connections_core.ConnectionError_, match="No file"):
        connections_core.add("claude_code", "", "", str(tmp_path / "missing"))
    monkeypatch.setattr(connections_core.shutil, "which", lambda name: None)
    other = connections_core.add("claude_code", "Second", "")
    _drain()
    db.session.refresh(other)
    assert other.state == "failed" and "not found" in other.error
    connections_core.remove(connection.id)
