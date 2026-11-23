"""Project instances (D-053): the commands that run a project — its dev server, a worker,
tests in watch mode — started from Cairn in a terminal, in the project's folder.

The command is the owner's own, split into an argv list (no shell). Windows runs `.cmd` /
`.bat` scripts (npm, yarn, pnpm…) only through `cmd.exe /c`: those, and only those, go
through it. A port the instance asks for is checked first; if it is taken, the next free
one is used, and the instance gets it as `PORT`. The ports it actually listens on are read
from the process and its children.
"""

from __future__ import annotations

import os
import shlex
import shutil
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.claude import ClaudeSession, ProjectInstance
from app.core.db_class.planning import Project
from app.core.extensions import db
from app.core.schema.instances import InstanceCreate
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action
from app.features.claude import terminal_core
from app.features.instances import survivor

PORT_SEARCH = 50  # how far past a taken port to look for a free one
LOGS_KEPT = 7 * 86400.0  # seconds an ended instance's log is kept
BATCH_SUFFIXES = (".cmd", ".bat")


class InstanceError(ValueError):
    pass


def _get(instance_id: uuid.UUID) -> ProjectInstance:
    instance = db.session.get(ProjectInstance, instance_id)
    if instance is None or instance.is_deleted:
        raise InstanceError("This instance does not exist.")
    return instance


def _changed(instance: ProjectInstance) -> None:
    publish("instance.changed", {"id": str(instance.id), "project": str(instance.project_id)})


def parse(command: str) -> list[str]:
    """The owner's command as an argv list (quotes respected; Windows paths kept)."""
    try:
        if os.name == "nt":
            parts = shlex.split(command, posix=False)
            argv = [p[1:-1] if len(p) > 1 and p[0] == p[-1] and p[0] in "\"'" else p for p in parts]
        else:
            argv = shlex.split(command)
    except ValueError as exc:
        raise InstanceError(f"This command cannot be read: {exc}.") from exc
    if not argv:
        raise InstanceError("The command is empty.")
    return argv


def argv_for(command: str, path: str | None = None) -> list[str]:
    """What is actually started: the program found on PATH; on Windows a `.cmd` / `.bat`
    script through `cmd.exe /c` (the only way Windows runs them)."""
    argv = parse(command)
    found = shutil.which(argv[0], path=path)
    if found is None:
        raise InstanceError(f"“{argv[0]}” was not found on this machine (PATH).")
    if sys.platform == "win32" and found.lower().endswith(BATCH_SUFFIXES):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", found, *argv[1:]]
    return [found, *argv[1:]]


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def free_port(wanted: int) -> int:
    for port in range(wanted, min(wanted + PORT_SEARCH, 65535) + 1):
        if port_is_free(port):
            return port
    raise InstanceError(f"No free port between {wanted} and {wanted + PORT_SEARCH}.")


def listening_ports(pid: int | None) -> list[int]:
    """Ports the process and its children listen on (what to open in the browser)."""
    if not pid:
        return []
    try:
        root = psutil.Process(pid)
        family = [root, *root.children(recursive=True)]
    except psutil.Error:
        return []
    ports: set[int] = set()
    for process in family:
        try:
            for conn in process.net_connections(kind="inet"):
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    ports.add(conn.laddr.port)
        except psutil.Error:
            continue
    return sorted(ports)


def _folder(instance: ProjectInstance) -> tuple[Project, Path]:
    project = db.session.get(Project, instance.project_id)
    if project is None or project.is_deleted:
        raise InstanceError("This instance's project no longer exists.")
    if not project.local_path:
        raise InstanceError(f"Set the local folder of “{project.name}” first (Edit the project).")
    root = Path(project.local_path).expanduser().resolve()
    folder = (root / instance.subfolder).resolve() if instance.subfolder else root
    if not folder.is_relative_to(root):
        raise InstanceError("The subfolder must stay inside the project's folder.")
    if not folder.is_dir():
        raise InstanceError(f"The folder {folder} does not exist on this machine.")
    return project, folder


# -- definitions ---------------------------------------------------------------------------


def create(data: InstanceCreate) -> ProjectInstance:
    project = db.session.get(Project, data.project_id)
    if project is None or project.is_deleted:
        raise InstanceError("This project does not exist.")
    parse(data.command)
    with batch():
        instance = ProjectInstance(**data.model_dump())
        db.session.add(instance)
        db.session.flush()
        log_action(
            "instance.create",
            target_type="instance",
            target_id=instance.id,
            meta=data.model_dump(mode="json"),
        )
        _changed(instance)
    return instance


def delete(instance_id: uuid.UUID) -> None:
    instance = _get(instance_id)
    if running(instance.id) is not None:
        raise InstanceError("Stop it first.")
    with batch():
        instance.deleted_at = utcnow()
        log_action("instance.delete", target_type="instance", target_id=instance.id)
        _changed(instance)


def _undo_create(row) -> None:
    instance = db.session.get(ProjectInstance, uuid.UUID(row.target_id))
    if instance is not None and instance.deleted_at is None:
        instance.deleted_at = utcnow()
        _changed(instance)


def _undo_delete(row) -> None:
    instance = db.session.get(ProjectInstance, uuid.UUID(row.target_id))
    if instance is not None:
        instance.deleted_at = None
        _changed(instance)


register_undo("instance.create", _undo_create)
register_undo("instance.delete", _undo_delete)


def for_project(project_id: uuid.UUID) -> list[dict[str, Any]]:
    """A project's instances, each with its running session (and ports) or its last run."""
    found = []
    for instance in db.session.scalars(
        select(ProjectInstance)
        .where(ProjectInstance.project_id == project_id, ProjectInstance.deleted_at.is_(None))
        .order_by(ProjectInstance.name)
    ):
        runs = terminal_core.sessions(kind="instance", instance_id=instance.id, limit=1)
        last = runs[0] if runs else None
        live = last if last is not None and terminal_core.is_running(last.id) else None
        found.append(
            {
                "instance": instance,
                "running": live,
                "last": last,
                "ports": listening_ports(live.pid) if live else [],
            }
        )
    return found


def running_count(project_id: uuid.UUID) -> int:
    return sum(
        terminal_core.is_running(row.id)
        for row in terminal_core.sessions(kind="instance", project_id=project_id)
    )


# -- running -------------------------------------------------------------------------------


def running(instance_id: uuid.UUID) -> ClaudeSession | None:
    runs = terminal_core.sessions(kind="instance", instance_id=instance_id, limit=1)
    return runs[0] if runs and terminal_core.is_running(runs[0].id) else None


def start(instance_id: uuid.UUID, cols: int = 120, rows: int = 32) -> ClaudeSession:
    """Start the instance (or give the one already running: never two at once)."""
    instance = _get(instance_id)
    already = running(instance.id)
    if already is not None:
        return already
    project, folder = _folder(instance)
    env = terminal_core._environment()
    argv = argv_for(instance.command, env.get("PATH"))
    port = free_port(instance.port) if instance.port else None
    if port is not None:
        env["PORT"] = str(port)
    return terminal_core.open_session(
        kind="instance",
        folder=folder,
        title=instance.name,
        build=lambda session: (argv, ()),
        env=env,
        project=project,
        instance_id=instance.id,
        port=port,
        cols=cols,
        rows=rows,
        meta={"command": instance.command, "port": port, "asked_port": instance.port},
        spawn=_outlive if survivor.available() else None,
    )


def _outlive(session: ClaudeSession, argv: list[str], **options) -> survivor.Survivor:
    return survivor.launch(session.id, argv, **options)


def reattach() -> int:
    """As Cairn starts: follow again the instances that went on without it (D-070); those that
    ended meanwhile are closed with how they ended. Returns how many still run."""
    if not survivor.available():
        return 0
    rows = list(
        db.session.scalars(
            select(ClaudeSession).where(ClaudeSession.kind == "instance", ClaudeSession.status == "running")
        )
    )
    alive = 0
    for row in rows:
        found = survivor.find(row.id)
        if found is not None:
            terminal_core.reattach(row, found)
            alive += 1
        elif not terminal_core.is_running(row.id):
            terminal_core.record_end(row.id, survivor.ended_code(row.id), "It ended while Cairn was closed")
    survivor.prune({row.id for row in rows}, LOGS_KEPT)
    return alive


def stop(instance_id: uuid.UUID) -> None:
    live = running(_get(instance_id).id)
    if live is None:
        raise InstanceError("It is not running.")
    terminal_core.stop(live.id)


def restart(instance_id: uuid.UUID, cols: int = 120, rows: int = 32, wait: float = 10.0) -> ClaudeSession:
    live = running(_get(instance_id).id)
    if live is not None:
        terminal_core.stop(live.id)
        deadline = time.monotonic() + wait
        while terminal_core.is_running(live.id) and time.monotonic() < deadline:
            time.sleep(0.1)
    return start(instance_id, cols, rows)
