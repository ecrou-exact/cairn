"""Instances found outside Cairn (D-061): copies of a repository, ports, logs."""

import json
import socket
import subprocess
import sys
import time

import pytest

from app.core.schema.planning import ProjectCreate
from app.features.claude import terminal_core
from app.features.instances import found_core, instances_core
from app.features.projects import projects_core

SERVER = """
import socket, sys, time
s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen()
log = open("app.log", "a"); log.write("port %d\\n" % s.getsockname()[1]); log.flush()
print(s.getsockname()[1], flush=True)
time.sleep(120)
"""


def _repo(folder, remote):
    (folder / ".git").mkdir(parents=True)
    (folder / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (folder / ".git" / "config").write_text(f'[remote "origin"]\n\turl = {remote}\n')
    return folder


@pytest.fixture
def serve():
    running = []

    def start(folder):
        process = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", SERVER], cwd=folder, stdout=subprocess.PIPE, text=True
        )
        running.append(process)
        port = int(process.stdout.readline())
        found_core._kept.clear()
        return process, port

    yield start
    for process in running:
        process.kill()
        process.wait()
        process.stdout.close()


@pytest.fixture(autouse=True)
def no_docker(monkeypatch):
    found_core._kept.clear()
    monkeypatch.setattr(found_core, "_containers", list)


def test_copies_of_a_repository_are_told_apart(ctx, tmp_path, serve):
    main = _repo(tmp_path / "lookyloo", "https://github.com/Lookyloo/lookyloo.git")
    clone = _repo(tmp_path / "lookyloo-fix", "git@github.com:lookyloo/Lookyloo.git")
    other = _repo(tmp_path / "other", "https://github.com/x/other.git")
    tree = tmp_path / "lookyloo-tree"
    tree.mkdir()
    own = main / ".git" / "worktrees" / "lookyloo-tree"
    own.mkdir(parents=True)
    (own / "commondir").write_text("../..\n")
    (own / "HEAD").write_text("ref: refs/heads/tree-modals\n")
    (tree / ".git").write_text(f"gitdir: {own}\n")
    ports = {folder.name: serve(folder)[1] for folder in (main, clone, other, tree)}
    project = projects_core.create(ProjectCreate(name="Lookyloo", local_path=str(main)))
    found = found_core.for_project(project)
    assert [(i["copy"], i["branch"], i["ports"]) for i in found] == [
        ("lookyloo", "main", [ports["lookyloo"]]),
        ("lookyloo-fix", "main", [ports["lookyloo-fix"]]),
        ("lookyloo-tree", "tree-modals", [ports["lookyloo-tree"]]),
    ]
    assert all(i["logs"][0]["label"] == "app.log" for i in found)


def test_a_log_is_followed_in_a_terminal(ctx, tmp_path, serve):
    folder = _repo(tmp_path / "site", "https://github.com/x/site.git")
    (tmp_path / "secret.log").write_text("secret")
    _, port = serve(folder)
    if sys.platform != "win32":
        (folder / "linked.log").symlink_to(tmp_path / "secret.log")
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(folder)))
    key = str(folder / "app.log")
    session = found_core.open_log(project, key)
    assert found_core.open_log(project, key).id == session.id  # already open
    with (folder / "app.log").open("a") as log:
        log.write("added later\n")
    deadline, seen = time.monotonic() + 15, ""
    while "added later" not in seen and time.monotonic() < deadline:
        seen = "".join(text for _, text in terminal_core.output(session.id, 0, wait=0.3)[0])
    assert f"port {port}" in seen and "added later" in seen
    (item,) = found_core.for_project(project)
    assert [log["label"] for log in item["logs"]] == ["app.log"]  # a link elsewhere is left out
    with pytest.raises(instances_core.InstanceError, match="no longer there"):
        found_core.open_log(project, str(tmp_path / "secret.log"))  # not one of its logs


def test_containers_by_their_compose_folder(ctx, tmp_path, monkeypatch):
    folder = _repo(tmp_path / "site", "https://github.com/x/site.git")
    row = {
        "ID": "abc",
        "Names": "site-web-1",
        "Ports": "0.0.0.0:8080->80/tcp, [::]:8080->80/tcp, 9000/tcp",
        "Labels": f"a=b,com.docker.compose.project.working_dir={folder}",
    }
    done = subprocess.CompletedProcess([], 0, stdout=json.dumps(row) + "\nnot json\n")
    monkeypatch.undo()
    monkeypatch.setattr(found_core.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(found_core.subprocess, "run", lambda *a, **k: done)
    monkeypatch.setattr(found_core, "_listeners", dict)
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(folder)))
    (item,) = found_core.for_project(project)
    assert (item["where"], item["ports"], item["copy"]) == ("Docker", [8080], "site")


def test_tab_and_api(signed_in, tmp_path, serve):
    folder = _repo(tmp_path / "site", "https://github.com/x/site.git")
    _, port = serve(folder)
    project = signed_in.post("/api/projects", json={"name": "Site", "local_path": str(folder)}).json[
        "project"
    ]
    page = signed_in.get(f"/projects/{project['slug']}?tab=instances").data.decode()
    assert f'href="http://localhost:{port}/" target="_blank"' in page and "Running outside Cairn" in page
    assert "site <span" in page  # the name of the copy
    (item,) = signed_in.get(f"/api/instances?project={project['id']}").json["outside"]
    opened = signed_in.post(
        "/instances/log", data={"project_id": project["id"], "key": item["logs"][0]["key"]}
    )
    assert "/claude/sessions/" in opened.location
    assert b"Close this log?" in signed_in.get(opened.location).data
    refused = signed_in.post("/api/instances/log", json={"project_id": project["id"], "key": "/etc/passwd"})
    assert refused.status_code == 409


def test_nothing_without_a_folder(ctx):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        assert found_core.for_project(projects_core.create(ProjectCreate(name="Loose"))) == []


def test_one_outside_can_be_stopped(ctx, tmp_path, serve, monkeypatch):
    folder = _repo(tmp_path / "site", "https://github.com/x/site.git")
    process, _ = serve(folder)
    project = projects_core.create(ProjectCreate(name="Site", local_path=str(folder)))
    other = projects_core.create(ProjectCreate(name="Other", local_path=str(tmp_path / "none")))
    (item,) = found_core.for_project(project)
    with pytest.raises(instances_core.InstanceError, match="no longer running"):
        found_core.stop(other, item["id"])  # not one of that project
    listener = int(item["id"].removeprefix("pid-"))  # under a launcher on Windows and macOS
    monkeypatch.setattr(found_core.transcript_core, "own_ancestors", lambda: {listener})
    with pytest.raises(instances_core.InstanceError, match="Cairn itself"):
        found_core.stop(project, item["id"])
    monkeypatch.undo()
    assert process.poll() is None
    monkeypatch.setattr(found_core, "_containers", list)
    found_core.stop(project, item["id"])
    process.wait(5)
    assert found_core.for_project(project) == []


def test_every_instance_of_the_machine_on_one_page(app, signed_in, tmp_path, serve):
    ours = _repo(tmp_path / "flowintel", "https://github.com/flowintel/flowintel.git")
    other = _repo(tmp_path / "loose-tool", "https://github.com/x/loose-tool.git")
    with app.app_context():
        projects_core.create(ProjectCreate(name="Flowintel", local_path=str(ours)))
    port, loose = serve(ours)[1], serve(other)[1]
    found = signed_in.get("/api/instances/running").json
    (group,) = found["groups"]
    assert group["project"]["name"] == "Flowintel" and group["outside"][0]["ports"] == [port]
    assert loose in [p for item in found["loose"] for p in item["ports"]]
    page = signed_in.get("/instances").data.decode()
    assert "/projects/flowintel" in page and f"localhost:{port}" in page
    assert "Make it a project" in page and "loose-tool" in page
    only = signed_in.get("/instances?q=flowintel").data.decode()
    assert f"localhost:{port}" in only and f"localhost:{loose}" not in only
    made = signed_in.get(f"/projects/new?folder={other}").data.decode()
    assert str(other) in made
