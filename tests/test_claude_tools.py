"""Claude's tools page (D-072) and instances started with the machine (D-073)."""

import json
import os
import sys
import time

from app.core.extensions import db
from app.core.schema.instances import InstanceCreate
from app.core.schema.planning import ProjectCreate
from app.core.utils.history import batch, undo
from app.features.claude import tools_core, transcript_core
from app.features.instances import instances_core
from app.features.projects import projects_core


def _use(n, name, **data):
    block = {"type": "tool_use", "id": f"t{n}", "name": name, "input": data}
    return {"type": "assistant", "timestamp": "2026-11-23T10:00:00Z", "message": {"content": [block]}}


def _failed(n):
    block = {"type": "tool_result", "tool_use_id": f"t{n}", "is_error": True}
    return {"type": "user", "message": {"content": [block]}}


def test_tools_are_counted(ctx, signed_in, tmp_path, monkeypatch):
    monkeypatch.setattr(transcript_core, "projects_root", lambda: tmp_path)
    folder = tmp_path / "repo"
    folder.mkdir()
    entries = [
        _use(1, "Bash", command="SECRET"),
        _failed(1),
        _use(2, "Bash"),
        _use(3, "mcp__cairn__take_note"),
        _use(4, "mcp__github__list_issues"),
        _use(5, "Skill", skill="review"),
    ]
    path = folder / "a.jsonl"
    path.write_text("\n".join([*(json.dumps(e) for e in entries), "cut {"]))
    old = folder / "old.jsonl"
    old.write_text(json.dumps(_use(9, "Old")))
    os.utime(old, (time.time() - 30 * 86400,) * 2)
    found = {tool["label"]: tool for tool in tools_core.overview()["tools"]}
    assert (found["Bash"]["calls"], found["Bash"]["failed"], found["Bash"]["kind"]) == (2, 1, "claude")
    assert found["take_note"]["asks"] and found["take_note"]["calls"] == 1 and found["take_note"]["about"]
    assert found["schedule"]["asks"] is False and found["schedule"]["calls"] == 0  # known, not used
    assert (found["list_issues"]["source"], found["review"]["kind"]) == ("github", "skill")
    assert "Old" not in found
    assert [t["label"] for t in tools_core.overview("take note", "cairn")["tools"]] == ["take_note"]
    page = signed_in.get("/claude/tools").data
    assert b"take_note" in page and b"asks you" in page and b"SECRET" not in page
    assert signed_in.get("/api/claude/tools?kind=skill").json["tools"][0]["label"] == "review"
    assert signed_in.get("/api/claude/tools?kind=x").status_code == 422


def test_instances_start_once_with_the_machine(app, ctx, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    (tmp_path / "run").mkdir(mode=0o700)
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(tmp_path)))
    command = f'"{sys.executable}" -c "import time; time.sleep(60)"'
    make = lambda name: instances_core.create(  # noqa: E731
        InstanceCreate(project_id=project.id, name=name, command=command)
    )
    wanted, other = make("Wanted"), make("Other")
    with batch() as batch_id:
        instances_core.set_autostart(wanted.id, True)
    undo(batch_id)
    assert not wanted.autostart
    instances_core.set_autostart(wanted.id, True)
    gone = make("Gone")
    instances_core.set_autostart(gone.id, True)
    gone.command = "definitely-not-a-program-xyz"
    db.session.commit()
    assert instances_core.start_with_machine(app) == 1  # one that cannot start stops nothing else
    assert instances_core.running(wanted.id) and not instances_core.running(other.id)
    instances_core.stop(wanted.id)
    deadline = time.monotonic() + 15
    while instances_core.running(wanted.id) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert instances_core.start_with_machine(app) == 0  # Cairn restarted: it stays stopped
    assert instances_core.running(wanted.id) is None


def test_autostart_form_and_api(signed_in, tmp_path):
    project = signed_in.post("/api/projects", json={"name": "Site", "local_path": str(tmp_path)}).json[
        "project"
    ]
    made = signed_in.post(
        "/api/instances", json={"project_id": project["id"], "name": "Web", "command": "python -V"}
    ).json["instance"]["id"]
    signed_in.post(f"/instances/{made}/autostart")
    (row,) = signed_in.get(f"/api/instances?project={project['id']}").json["instances"]
    assert row["autostart"] is True
    assert signed_in.put(f"/api/instances/{made}/autostart", json={"on": False}).json["autostart"] is False
