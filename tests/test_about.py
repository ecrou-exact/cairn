"""What Cairn is built with, and the footer (D-074)."""

import json
import re
import tomllib
from pathlib import Path

from app.config import ROOT_DIR
from app.features.about import about_core


def test_nothing_is_missing(ctx):
    parts = json.loads(about_core.PARTS_FILE.read_text(encoding="utf-8"))
    keys = {part["key"] for part in parts["parts"] if "key" in part}
    assert keys == {name for name in about_core.vendored() if not name.startswith("_")}
    project = tomllib.loads((Path(ROOT_DIR) / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    wanted = [*project["dependencies"], *project["optional-dependencies"]["postgres"]]
    names = {re.match(r"[A-Za-z0-9-]+", line).group(0) for line in wanted}
    assert names <= {part.get("dist") for part in parts["parts"]}
    assert {part["group"] for part in parts["parts"]} == set(parts["groups"])
    assert all(part["url"].startswith("https://") and part["about"] for part in parts["parts"])


def test_versions_are_the_real_ones(ctx):
    found = {part["name"]: part for part in about_core.built_with()["parts"]}
    assert found["xterm.js"]["version"] == "6.0.0" and found["xterm.js"]["license"] == "MIT"
    assert (found["Vitrine"]["version"], found["IBM Plex"]["version"]) == ("07ab878", "5.3.0")
    assert found["Flask"]["version"][0].isdigit() and found["Flask"]["license"]
    assert [p["name"] for p in about_core.built_with("terminal browser", "interface")["parts"]] == [
        "xterm.js"
    ]


def test_page_api_and_footer(signed_in, client):
    page = signed_in.get("/built-with").data.decode()
    assert "Vitrine" in page and "Pivotick" in page and 'class="cn-footer"' in page
    assert "Nothing matches" in signed_in.get("/built-with?q=zzzz").data.decode()
    assert "Flask" in signed_in.get("/built-with?group=nope").data.decode()
    assert len(signed_in.get("/api/built-with?group=interface").json["parts"]) == 6
    assert about_core.version() in signed_in.get("/tasks").data.decode()


def test_built_with_is_the_owners(client, owner):
    assert client.get("/built-with").status_code == 302
