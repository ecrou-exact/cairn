"""Runs one instance outside Cairn's own process (D-070), so that it outlives a restart of Cairn.
Linux and macOS. Started as `python runner.py <spec.json>`; the spec holds the environment, so it
is readable by its owner only and removed as soon as it is read.

The program gets a pseudo-terminal. What it prints goes to a log file (cut when it grows), keys
and sizes come from a Unix socket, its pid and how it ended are in a state file. SIGTERM stops
the program and its children, then the runner.
"""

from __future__ import annotations

import contextlib
import json
import os
import select
import signal
import socket
import sys
import time
from pathlib import Path

LOG_MAX = 4 * 1024 * 1024
LOG_KEPT = 1024 * 1024
GRACE = 5.0
BUFFER_MAX = 1024 * 1024  # a client that sends no line end is dropped


def write_state(path: Path, **values) -> None:
    partial = path.with_name(f"{path.name}.{os.getpid()}")
    partial.write_text(json.dumps(values), encoding="utf-8")
    partial.replace(path)


class Log:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = self._open()

    def _open(self):
        return os.fdopen(os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "ab", 0)

    def write(self, data: bytes) -> None:
        self.handle.write(data)
        if self.handle.tell() > LOG_MAX:
            self.handle.close()
            kept = self.path.read_bytes()[-LOG_KEPT:]
            partial = self.path.with_name(f"{self.path.name}.new")
            with os.fdopen(os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as new:
                new.write(kept.partition(b"\n")[2])
            partial.replace(self.path)
            self.handle = self._open()


def main() -> int:
    from ptyprocess import PtyProcess

    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_path.unlink()
    state, sock_path = Path(spec["state"]), Path(spec["socket"])
    log = Log(Path(spec["log"]))
    stopping: list[float] = []
    signal.signal(signal.SIGTERM, lambda *_: stopping.append(time.monotonic()))
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        child = PtyProcess.spawn(
            spec["argv"], cwd=spec["cwd"], env=spec["env"], dimensions=(spec["rows"], spec["cols"])
        )
    except Exception as exc:
        write_state(state, pid=os.getpid(), ended=True, exit_code=127, error=str(exc)[:300])
        return 1
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock_path.unlink(missing_ok=True)
        server.bind(str(sock_path))
        sock_path.chmod(0o600)
        server.listen(4)
    except OSError as exc:  # told, instead of a program nobody can reach
        child.terminate(force=True)
        write_state(state, pid=os.getpid(), ended=True, exit_code=126, error=f"its socket: {exc}"[:300])
        return 1
    write_state(state, pid=os.getpid(), child=child.pid, ended=False)

    clients: dict[int, tuple[socket.socket, bytes]] = {}

    def obey(line: bytes) -> None:
        try:
            order = json.loads(line)
            if isinstance(order.get("in"), str):
                child.write(order["in"].encode())
            elif isinstance(order.get("size"), list):
                cols, rows = (max(1, min(int(n), 1000)) for n in order["size"])
                child.setwinsize(rows, cols)
        except (ValueError, TypeError, AttributeError, OSError):
            return

    def signal_child(number: int) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, number)

    hung_up = killed = False
    while True:
        if stopping and not hung_up:
            hung_up = True
            signal_child(signal.SIGHUP)
            signal_child(signal.SIGTERM)
        if stopping and not killed and time.monotonic() - stopping[0] > GRACE:
            killed = True
            signal_child(signal.SIGKILL)
        ready, _, _ = select.select([child.fd, server, *clients], [], [], 0.5)
        if child.fd in ready:
            try:
                data = os.read(child.fd, 65536)
            except OSError:  # Linux: the terminal is closed, the program has ended
                data = b""
            if not data:
                break
            log.write(data)
        if server in ready:
            client, _ = server.accept()
            client.setblocking(False)
            clients[client.fileno()] = (client, b"")
        for fd in [fd for fd in ready if fd in clients]:
            client, pending = clients[fd]
            try:
                data = client.recv(65536)
            except OSError:
                data = b""
            pending += data
            *lines, pending = pending.split(b"\n")
            for line in lines:
                obey(line)
            if not data or len(pending) > BUFFER_MAX:
                client.close()
                del clients[fd]
            else:
                clients[fd] = (client, pending)
    while child.isalive():  # it closed its terminal and goes on: still stopped when asked
        if stopping:
            waited = time.monotonic() - stopping[0]
            signal_child(signal.SIGKILL if waited > GRACE else signal.SIGTERM)
        time.sleep(0.2)
    signal_child(signal.SIGHUP)  # what it left in its group
    code = child.exitstatus if child.exitstatus is not None else -(child.signalstatus or 0)
    write_state(state, pid=os.getpid(), child=child.pid, ended=True, exit_code=code)
    server.close()
    sock_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
