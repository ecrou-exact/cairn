"""Claude fills a project from its folder (D-090)."""

import io

from PIL import Image

from app.core.schema.claude import SessionStart
from app.core.schema.planning import ProjectCreate
from app.features.claude import mcp_server, terminal_core
from app.features.projects import projects_core
from tests.test_claude_mcp import _call, _data


def test_the_fill_preset_asks_for_everything(tmp_path):
    data = SessionStart(preset="fill", detail="the docs folder", folder=str(tmp_path))
    message = terminal_core._first_message(data, None)
    assert "set_project_logo" in message and "found_in_project" in message and "the docs folder" in message
    assert terminal_core._title(data, "Loo", None) == "Fill Loo"
    assert "fill" in {key for key in terminal_core.PRESET_INFO}


def test_logo_and_links(app, tmp_path):
    folder = tmp_path / "loo"
    (folder / "docs").mkdir(parents=True)
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(out, format="PNG")
    (folder / "docs" / "logo.png").write_bytes(out.getvalue())
    (tmp_path / "secret.png").write_bytes(out.getvalue())
    with app.app_context():
        projects_core.create(ProjectCreate(name="Loo", local_path=str(folder)))
    server = mcp_server.build(app, None)
    assert (
        _data(_call(server, "set_project_logo", {"path": "docs/logo.png", "project": "loo"}))["logo"]
        == "docs/logo.png"
    )
    for path in ("../secret.png", str(tmp_path / "secret.png"), "docs"):
        assert _call(server, "set_project_logo", {"path": path, "project": "loo"}).is_error
    links = [{"label": "Docs", "url": "https://loo.example/docs"}]
    _call(server, "update_project", {"project": "loo", "links": links})
    with app.app_context():
        project = projects_core.by_slug("loo")
        assert project.image_name and project.links[0]["label"] == "Docs"
    assert "set_project_logo" in mcp_server.WRITE_TOOLS
