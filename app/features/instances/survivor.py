"""A running instance seen from Cairn (D-070): the same face as `pty_host.Pty` over a runner that
is not Cairn's child. Its output is read from the log, its keys go to the runner's socket."""

from __future__ import annotations

import codecs
import json
import os
import shutil
import signal
import socket
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import psutil
from flask import current_app

from app.features.instances import runner

START_WAIT = 8.0
POLL = 0.25
SOCKET_MAX = 100  # bytes: 104 on macOS, 108 on Linux
TAIL = 512 * 1024
STOP_WAIT = runner.GRACE + 3.0


def available() -> bool:
    return os.name == "posix"


def folder() -> Path:
    path = Path(current_app.config["CAIRN_DATA_DIR"]) / "instances"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def log_path(session_id: uuid.UUID) -> Path:
    return folder() / f"{session_id}.log"


def _state_path(session_id: uuid.UUID) -> Path:
    return folder() / f"{session_id}.json"


def _socket_path(session_id: uuid.UUID) -> Path:
    """In a short, private folder: a Unix socket's path is limited to about 100 characters."""
    base, name = os.environ.get("XDG_RUNTIME_DIR"), f"{session_id.hex[:20]}.sock"
    places = [Path(base) / "cairn"] if base else []
    places += [Path(top) / f"cairn-{os.getuid()}" for top in (tempfile.gettempdir(), "/tmp")]  # noqa: S108  # nosec B108
    place = next((p for p in places if len(os.fsencode(p / name)) <= SOCKET_MAX), places[-1])
    place.mkdir(mode=0o700, exist_ok=True)
    stat = place.lstat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077 or place.is_symlink():
        raise OSError(f"{place} is not private")
    return place / name


def _read_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _runner(pid: Any, session_id: uuid.UUID) -> psutil.Process | None:
    """The runner of this session if it is alive: a reused pid is not taken for it."""
    try:
        process = psutil.Process(int(pid))
        if process.status() == psutil.STATUS_ZOMBIE:
            return None
        argv = process.cmdline()
    except (psutil.Error, TypeError, ValueError):
        return None
    return process if any(str(session_id) in arg for arg in argv) else None


class Survivor:
    survives = True  # Cairn stopping does not stop it

    def __init__(self, session_id: uuid.UUID, state: Path, log: Path, sock: Path, pid: int) -> None:
        self.session_id, self._state, self._log, self._sock, self._pid = session_id, state, log, sock, pid
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._handle = None
        self._place = 0
        self._left = threading.Event()

    @property
    def pid(self) -> int:
        return self._pid

    def _alive(self) -> bool:
        return not _read_state(self._state).get("ended") and _runner(self._pid, self.session_id) is not None

    def _new(self) -> bytes:
        """What the log gained; read again from its start when it was cut or replaced."""
        try:
            stat = self._log.stat()
            if self._handle is not None:
                own = os.fstat(self._handle.fileno())
                if own.st_ino != stat.st_ino or stat.st_size < self._place:
                    rest = self._handle.read()
                    self._handle.close()
                    self._handle, self._place = self._log.open("rb"), 0
                    self._handle.seek(0, 2)  # the new file holds what was already shown
                    self._place = self._handle.tell()
                    return rest
            else:
                self._handle = self._log.open("rb")
                if stat.st_size > TAIL:
                    self._handle.seek(stat.st_size - TAIL)
                    self._handle.readline()
            data = self._handle.read(65536)
            self._place = self._handle.tell()
            return data
        except FileNotFoundError:
            return b""

    def read(self) -> str:
        while not self._left.is_set():
            alive = self._alive()  # before reading: what it printed last is not missed
            data = self._new()
            if data:
                return self._decoder.decode(data)
            if not alive:
                break
            time.sleep(POLL)
        if self._handle is not None:
            self._handle.close()
        raise EOFError

    def _send(self, order: dict[str, Any]) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(self._sock))
            client.sendall(json.dumps(order).encode() + b"\n")

    def write(self, text: str) -> None:
        self._send({"in": text})

    def resize(self, cols: int, rows: int) -> None:
        self._send({"size": [cols, rows]})

    def leave(self) -> None:
        """Stop following it; it goes on."""
        self._left.set()

    def exit_code(self) -> int | None:
        code = _read_state(self._state).get("exit_code")
        return code if isinstance(code, int) else None

    def kill(self) -> None:
        process = _runner(self._pid, self.session_id)
        if process is None:
            return
        try:
            process.send_signal(signal.SIGTERM)
            _, alive = psutil.wait_procs([process], timeout=STOP_WAIT)
            for left in alive:
                for child in left.children(recursive=True):
                    child.kill()
                left.kill()
        except psutil.NoSuchProcess:
            return


def launch(
    session_id: uuid.UUID, argv: list[str], *, cwd: str, env: dict[str, str], cols: int, rows: int
) -> Survivor:
    """Start a program under a runner of its own. On Linux through the session's systemd: outside
    Cairn's service, which stops everything it started."""
    state, log, sock = _state_path(session_id), log_path(session_id), _socket_path(session_id)
    spec = folder() / f"{session_id}.spec.json"
    content = {
        "argv": argv,
        "cwd": cwd,
        "env": env,
        "cols": cols,
        "rows": rows,
        "state": str(state),
        "log": str(log),
        "socket": str(sock),
    }
    with os.fdopen(os.open(spec, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as out:
        json.dump(content, out)
    command = [sys.executable, str(Path(runner.__file__).resolve()), str(spec)]
    systemd = shutil.which("systemd-run") if sys.platform.startswith("linux") else None
    if systemd and not current_app.testing:
        unit = f"--unit=cairn-instance-{session_id.hex[:12]}"
        command = [systemd, "--user", "--collect", "--quiet", unit, "-p", "KillMode=mixed", "--", *command]
    process = None
    try:
        process = subprocess.Popen(  # noqa: S603  # nosec B603
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + START_WAIT
        while time.monotonic() < deadline:
            found = _read_state(state)
            if found.get("error"):
                raise OSError(found["error"])
            if found.get("pid"):
                threading.Thread(target=process.wait, daemon=True).start()  # no zombie left behind
                return Survivor(session_id, state, log, sock, int(found["pid"]))
            time.sleep(0.05)
        raise OSError("its runner did not start")
    except OSError:
        spec.unlink(missing_ok=True)
        state.unlink(missing_ok=True)
        if process is not None and process.poll() is None:
            process.terminate()
        raise


def find(session_id: uuid.UUID) -> Survivor | None:
    """A session's runner still alive from before Cairn restarted."""
    state = _state_path(session_id)
    found = _read_state(state)
    if found.get("ended") or _runner(found.get("pid"), session_id) is None:
        return None
    return Survivor(session_id, state, log_path(session_id), _socket_path(session_id), int(found["pid"]))


def tail(session_id: uuid.UUID, size: int = 20_000) -> str:
    """The end of a session's log, kept after it ended."""
    try:
        with log_path(session_id).open("rb") as log:
            log.seek(0, 2)
            log.seek(max(0, log.tell() - size))
            return log.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def ended_code(session_id: uuid.UUID) -> int | None:
    code = _read_state(_state_path(session_id)).get("exit_code")
    return code if isinstance(code, int) else None


def prune(keep: set[uuid.UUID], older_than: float) -> int:
    """Delete the logs and states of sessions that ended long ago."""
    removed = 0
    for path in folder().iterdir():
        try:
            owner = uuid.UUID(path.name.split(".")[0])
            if owner not in keep and time.time() - path.stat().st_mtime > older_than:
                path.unlink()
                removed += 1
        except (ValueError, OSError):
            continue
    return removed
