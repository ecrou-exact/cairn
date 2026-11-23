"""Project instances (D-053): commands that run a project, started from Cairn."""

import os
import socket
import sys
import time

import pytest

from app.core.schema.instances import InstanceCreate
from app.core.schema.planning import ProjectCreate
from app.core.utils.history import batch, undo
from app.features.claude import claude_core, terminal_core
from app.features.instances import instances_core
from app.features.projects import projects_core

SERVER = """
import http.server, os, socketserver
port = int(os.environ["PORT"])
with socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler) as s:
    print("listening on", os.environ["PORT"], flush=True)
    s.serve_forever()
"""


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _until(check, timeout=20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.2)
    return check()


def test_parse_keeps_quotes_and_paths():
    assert instances_core.parse('npm run "dev server"') == ["npm", "run", "dev server"]
    with pytest.raises(instances_core.InstanceError):
        instances_core.parse("   ")
    with pytest.raises(instances_core.InstanceError, match="not found"):
        instances_core.argv_for("definitely-not-a-program-xyz")
    assert (
        instances_core.argv_for(f'"{sys.executable}" -V')[0]
        .lower()
        .endswith(("python.exe", "python", "python3"))
    )


def test_ports():
    busy = socket.socket()
    busy.bind(("127.0.0.1", 0))
    busy.listen()
    taken = busy.getsockname()[1]
    try:
        assert not instances_core.port_is_free(taken)
        assert instances_core.free_port(taken) > taken
    finally:
        busy.close()


def test_instance_runs_listens_and_stops(app, ctx, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "CAIRN_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "server.py").write_text(SERVER, encoding="utf-8")
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(tmp_path)))
    port = _free_port()
    instance = instances_core.create(
        InstanceCreate(
            project_id=project.id, name="Dev server", command=f'"{sys.executable}" server.py', port=port
        )
    )
    session = instances_core.start(instance.id)
    assert (session.kind, session.port, session.cwd) == ("instance", port, str(tmp_path))
    assert instances_core.start(instance.id).id == session.id  # never two at once
    ports = _until(lambda: instances_core.listening_ports(session.pid))
    assert port in ports
    listed = instances_core.for_project(project.id)
    assert listed[0]["running"].id == session.id and port in listed[0]["ports"]
    shown = claude_core.overview()["instances"]  # on the Claude page, with the end of its log
    assert [s["id"] for s in shown] == [str(session.id)]
    assert _until(lambda: any(f"listening on {port}" in s for s in terminal_core.preview(session.id)))
    with pytest.raises(instances_core.InstanceError, match="Stop it first"):
        instances_core.delete(instance.id)

    again = instances_core.restart(instance.id)
    assert again.id != session.id and not terminal_core.is_running(session.id)
    instances_core.stop(instance.id)
    assert _until(lambda: not terminal_core.is_running(again.id))
    with pytest.raises(instances_core.InstanceError, match="not running"):
        instances_core.stop(instance.id)

    with batch() as batch_id:
        instances_core.delete(instance.id)
    assert instances_core.for_project(project.id) == []
    undo(batch_id)
    assert [i["instance"].name for i in instances_core.for_project(project.id)] == ["Dev server"]


def test_subfolder_stays_inside(ctx, tmp_path):
    project = projects_core.create(ProjectCreate(name="Box", local_path=str(tmp_path / "box")))
    (tmp_path / "box").mkdir()
    escape = instances_core.create(
        InstanceCreate(
            project_id=project.id, name="Out", command="python -V", subfolder=os.path.join("..", "..")
        )
    )
    with pytest.raises(instances_core.InstanceError, match="inside the project"):
        instances_core.start(escape.id)


def test_instances_api_and_tab(app, signed_in, tmp_path):
    project = signed_in.post("/api/projects", json={"name": "Api site", "local_path": str(tmp_path)}).json[
        "project"
    ]
    made = signed_in.post(
        "/api/instances",
        json={"project_id": project["id"], "name": "Echo", "command": f'"{sys.executable}" -V'},
    )
    assert made.status_code == 201
    listed = signed_in.get(f"/api/instances?project={project['id']}").json["instances"]
    assert listed[0]["name"] == "Echo" and listed[0]["running"] is None
    assert signed_in.post(f"/api/instances/{made.json['instance']['id']}/stop").status_code == 409
    tab = signed_in.get(f"/projects/{project['slug']}?tab=instances").data
    assert b"Echo" in tab and b"Add a command" in tab
    assert (
        signed_in.post(
            "/api/instances", json={"project_id": project["id"], "name": "x", "command": ""}
        ).status_code
        == 422
    )


def test_running_instance_on_the_claude_page(app, signed_in, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "CAIRN_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "wait.py").write_text(
        "import time\nprint('up', flush=True)\ntime.sleep(60)\n", encoding="utf-8"
    )
    project = signed_in.post("/api/projects", json={"name": "Page site", "local_path": str(tmp_path)}).json[
        "project"
    ]
    made = signed_in.post(
        "/api/instances",
        json={"project_id": project["id"], "name": "Waiter", "command": f'"{sys.executable}" wait.py'},
    ).json["instance"]
    assert signed_in.post(f"/api/instances/{made['id']}/start").status_code in (200, 201)
    try:
        page = signed_in.get("/claude").data
        assert b"Instances running" in page and b"Waiter" in page and b"data-instance-log" in page
    finally:
        signed_in.post(f"/api/instances/{made['id']}/stop")
