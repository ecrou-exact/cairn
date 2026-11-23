"""Instances of a project running outside Cairn (D-061): in a terminal, an editor, a Claude, or
a container, in the project's folder or in any other copy of the same repository (a worktree, a
clone), so that several copies running at once can be told apart.

Found by what listens on a port (`psutil`, `docker ps`): its folder, its branch, its ports and
the log files it keeps open or the copy's log folders. Only those files can be followed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import psutil

from app.core.db_class.claude import ClaudeSession
from app.core.db_class.planning import Project
from app.features.claude import terminal_core, transcript_core
from app.features.claude.live_core import program
from app.features.instances import follow, instances_core

REMOTE = re.compile(r"^\s*url\s*=\s*(\S+)", re.M)
REPO = re.compile(r"[/:]([^/:]+/[^/]+?)(?:\.git)?/?$")
PUBLISHED = re.compile(r":(\d+)->")
LOG_SUFFIXES = (".log", ".out", ".err")
LOG_PLACES = ("*.log", "log/*.log", "logs/*.log", "*/logs/*.log")
RECENT_LOG = 48 * 3600.0
LOGS_SHOWN = 6
KEPT = 2.0  # seconds a machine-wide look is reused


# -- which repository a folder is in ----------------------------------------------------------


def _git(folder: Path) -> tuple[Path, Path, Path] | None:
    """(top folder, its git folder, the repository's common git folder) of a folder, or None."""
    for top in (folder, *folder.parents):
        mark = top / ".git"
        try:
            if mark.is_dir():
                return top, mark, mark.resolve()
            if mark.is_file():
                own = Path(mark.read_text(encoding="utf-8").partition("gitdir:")[2].strip())
                own = own if own.is_absolute() else top / own
                common = own / "commondir"
                if common.is_file():
                    return top, own, (own / common.read_text(encoding="utf-8").strip()).resolve()
                return top, own, own.resolve()
        except OSError:
            return None
    return None


def _repositories(common: Path) -> set[str]:
    """`owner/name` of every remote, in lower case."""
    try:
        urls = REMOTE.findall((common / "config").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return set()
    return {match[1].lower() for match in map(REPO.search, urls) if match}


def _branch(own: Path) -> str:
    try:
        head = (own / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return head.removeprefix("ref: refs/heads/") if head.startswith("ref:") else head[:8]


class _Copies:
    """Whether a folder is the project's, or another copy of its repository."""

    def __init__(self, project: Project) -> None:
        self.root = Path(project.local_path).expanduser().resolve() if project.local_path else None
        git = _git(self.root) if self.root else None
        self.common = git[2] if git else None
        self.repos = _repositories(self.common) if self.common else set()
        if project.github_repo:
            self.repos.add(project.github_repo.lower())

    def place(self, folder: str) -> dict[str, str] | None:
        path = Path(folder)
        git = _git(path)
        inside = self.root is not None and path.is_relative_to(self.root)
        same = git is not None and (
            git[2] == self.common or bool(self.repos and self.repos & _repositories(git[2]))
        )
        if not inside and not same:
            return None
        top = git[0] if git else self.root
        return {"copy": top.name, "folder": str(top), "branch": _branch(git[1]) if git else ""}


# -- what runs on the machine -----------------------------------------------------------------

_kept: dict[str, tuple[float, Any]] = {}


def _reuse(name: str, look) -> Any:
    known = _kept.get(name)
    if known is None or time.monotonic() - known[0] > KEPT:
        known = _kept[name] = (time.monotonic(), look())
    return known[1]


def _listeners() -> dict[int, set[int]]:
    """pid → the TCP ports it listens on, for the processes we may see."""
    found: dict[int, set[int]] = {}
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.pid:
                found.setdefault(conn.pid, set()).add(conn.laddr.port)
    except psutil.AccessDenied:  # macOS: only process by process
        for process in psutil.process_iter():
            try:
                for conn in process.net_connections(kind="tcp"):
                    if conn.status == psutil.CONN_LISTEN and conn.laddr:
                        found.setdefault(process.pid, set()).add(conn.laddr.port)
            except psutil.Error:
                continue
    return found


def _containers() -> list[dict[str, Any]]:
    """Running containers that publish a port, with the folder they were started from."""
    docker = shutil.which("docker")
    if docker is None:
        return []
    try:
        done = subprocess.run(  # noqa: S603  # nosec B603
            [docker, "ps", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for line in done.stdout.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        labels = dict(part.split("=", 1) for part in str(row.get("Labels", "")).split(",") if "=" in part)
        folder = labels.get("com.docker.compose.project.working_dir", "")
        ports = sorted({int(port) for port in PUBLISHED.findall(str(row.get("Ports", "")))})
        if folder and ports:
            found.append(
                {"id": str(row.get("ID")), "name": str(row.get("Names")), "folder": folder, "ports": ports}
            )
    return found


def _log_files(process: psutil.Process, folder: Path) -> list[Path]:
    """Files the process and its children write as logs, then the copy's recent log files."""
    found: dict[Path, None] = {}
    try:
        family = [process, *process.children(recursive=True)]
    except psutil.Error:
        family = [process]
    for member in family:
        try:
            for opened in member.open_files():
                path = Path(opened.path)
                if getattr(opened, "mode", "a") in ("a", "a+", "w") and path.suffix in LOG_SUFFIXES:
                    found[path] = None
        except (psutil.Error, OSError):
            continue
        if sys.platform.startswith("linux"):
            for number in (1, 2):  # its output, sent to a file
                try:
                    path = Path(f"/proc/{member.pid}/fd/{number}").resolve(strict=True)
                    if path.is_file():
                        found[path] = None
                except OSError:
                    continue
    recent = []
    for place in LOG_PLACES:
        try:
            for path in folder.glob(place):
                moved = path.stat().st_mtime
                inside = not path.is_symlink() and path.resolve().is_relative_to(folder.resolve())
                if inside and path.is_file() and time.time() - moved < RECENT_LOG:
                    recent.append((moved, path))
        except OSError:
            continue
    for _, path in sorted(recent, reverse=True):
        found[path.resolve()] = None
    return list(found)[:LOGS_SHOWN]


def for_project(project: Project) -> list[dict[str, Any]]:
    """What runs for a project outside Cairn's own terminals, by copy then port."""
    copies = _Copies(project)
    if copies.root is None and not copies.repos:
        return []
    listeners: dict[int, set[int]] = _reuse("listeners", _listeners)
    ours = terminal_core.running_pids(kind="instance")
    found = []
    for pid, ports in listeners.items():
        try:
            process = psutil.Process(pid)
            if (process.name() or "").lower() in transcript_core.CLAUDE_NAMES:
                continue
            parents = {parent.pid for parent in process.parents()}
            if (parents | {pid}) & ours:
                continue  # an instance of Cairn's, shown with its definition
            if parents & set(listeners) and _same_ports(parents & set(listeners), ports, listeners):
                continue  # a worker of one already shown
            place = copies.place(process.cwd())
            if place is None:
                continue
            folder = Path(place["folder"])
            logs = [
                {"key": str(path), "label": path.name, "path": str(path)}
                for path in _log_files(process, folder)
            ]
            found.append(
                {
                    **place,
                    "id": f"pid-{pid}",
                    "label": program(process),
                    "where": transcript_core.host_of(pid),
                    "since": process.create_time(),
                    "ports": sorted(ports),
                    "logs": logs,
                }
            )
        except (psutil.Error, OSError):
            continue
    for container in _reuse("containers", _containers):
        place = copies.place(container["folder"])
        if place is not None:
            found.append(
                {
                    **place,
                    "id": f"docker-{container['id']}",
                    "label": container["name"],
                    "where": "Docker",
                    "since": None,
                    "ports": container["ports"],
                    "logs": [{"key": f"docker-{container['id']}", "label": "Container log", "path": None}],
                }
            )
    return sorted(found, key=lambda item: (item["copy"], item["ports"]))


def _same_ports(pids: set[int], ports: set[int], listeners: dict[int, set[int]]) -> bool:
    return any(ports <= listeners[pid] for pid in pids)


# -- logs in a Cairn terminal -----------------------------------------------------------------


def open_log(project: Project, key: str) -> ClaudeSession:
    """Follow one of the logs found for a project in a terminal (the one already open, if any)."""
    instance, log = next(
        ((i, entry) for i in for_project(project) for entry in i["logs"] if entry["key"] == key), (None, None)
    )
    if instance is None:
        raise instances_core.InstanceError("This log is no longer there: the instance may have stopped.")
    title = f"{instance['copy']} · {log['label']}"
    for row in terminal_core.sessions(kind="log"):
        if row.title == title[:200] and row.cwd == instance["folder"] and terminal_core.is_running(row.id):
            return row
    if log["path"] is None:
        docker = shutil.which("docker")
        if docker is None:
            raise instances_core.InstanceError("docker was not found on this machine.")
        argv = [docker, "logs", "--follow", "--tail", "500", key.removeprefix("docker-")]
    else:
        argv = [sys.executable, str(Path(follow.__file__).resolve()), log["path"]]
    return terminal_core.open_session(
        kind="log",
        folder=Path(instance["folder"]),
        title=title,
        build=lambda session: (argv, ()),
        env=terminal_core._environment(),
        project=project,
        cli_session_id=uuid.uuid4(),
        meta={"log": log["path"] or key},
    )
