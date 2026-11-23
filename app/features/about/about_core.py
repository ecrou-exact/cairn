"""What Cairn is built with (D-074). What each part does is in `built_with.json`; versions and
licences are read where they are true: `vendor.json` for the front end, the installed packages,
and PATH for the programs of the machine. A test keeps the list complete."""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from functools import cache
from importlib import metadata
from pathlib import Path
from typing import Any

from flask import current_app

from app.config import ROOT_DIR

PARTS_FILE = Path(__file__).with_name("built_with.json")
SOURCE = "https://github.com/ecrou-exact/cairn"
LICENSE = "AGPL-3.0-or-later"


@cache
def version() -> str:
    with (Path(ROOT_DIR) / "pyproject.toml").open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


def vendored() -> dict[str, Any]:
    path = Path(current_app.static_folder) / "vendor" / "vendor.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _license(about: metadata.PackageMetadata) -> str:
    named = about.get("License-Expression")
    if named:
        return named
    for line in about.get_all("Classifier") or []:
        if line.startswith("License :: OSI Approved ::"):
            return line.rsplit("::", 1)[1].strip()
    words = (about.get("License") or "").strip().splitlines()
    return words[0][:60] if words else ""


def _short(text: str) -> str:
    """The version alone: its number, or the first characters of a commit."""
    commit = re.search(r"\b([0-9a-f]{7})[0-9a-f]{33}\b", text)
    number = re.search(r"\d+(?:\.\d+)+", text.split(" (")[0])
    return commit.group(1) if commit else number.group(0) if number else text


def _facts(part: dict[str, Any], front: dict[str, Any]) -> dict[str, Any]:
    if "key" in part:
        row = front[part["key"]]
        return {"version": _short(row["version"]), "license": row["license"], "here": True}
    if "dist" in part:
        try:
            about = metadata.metadata(part["dist"])
        except metadata.PackageNotFoundError:
            return {"version": "", "license": "", "here": False}
        return {"version": about["Version"], "license": _license(about), "here": True}
    return {"version": "", "license": "", "here": shutil.which(part["program"]) is not None}


def built_with(search: str = "", group: str = "") -> dict[str, Any]:
    """The parts, by group; `search` in their names and what they do, `group` one of the groups."""
    data, front = json.loads(PARTS_FILE.read_text(encoding="utf-8")), vendored()
    words = search.lower().split()
    parts = [
        {
            "name": part["name"],
            "group": part["group"],
            "icon": part["icon"],
            "url": part["url"],
            "about": part["about"],
            "from": "front end" if "key" in part else "Python" if "dist" in part else "program",
            **_facts(part, front),
        }
        for part in data["parts"]
        if (not group or part["group"] == group)
        and all(word in f"{part['name']} {part['about']}".lower() for word in words)
    ]
    return {"groups": data["groups"], "parts": parts, "version": version(), "total": len(data["parts"])}
