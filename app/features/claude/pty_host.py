"""One program in a pseudo-terminal, the same on every OS (D-050).

Windows uses ConPTY through `pywinpty`; Linux and macOS use `ptyprocess`. Both read and
write text (UTF-8), resize, report the exit status and can be killed. The program is given
as an argv list: no shell is ever involved.
"""

from __future__ import annotations

import codecs
import os
import signal
import sys
import threading
from typing import Any

STOP_GRACE = 2.0  # seconds a program has to end after a hang-up before it is killed


class Pty:
    def __init__(self, process: Any) -> None:
        self._process = process
        self._reaped = threading.Event()

    @classmethod
    def spawn(cls, argv: list[str], *, cwd: str, env: dict[str, str], cols: int, rows: int) -> Pty:
        if sys.platform == "win32":
            from winpty import PtyProcess

            process = PtyProcess.spawn(argv, cwd=cwd, env=env, dimensions=(rows, cols))
        else:
            from ptyprocess import PtyProcessUnicode

            process = PtyProcessUnicode.spawn(argv, cwd=cwd, env=env, dimensions=(rows, cols))
            # ptyprocess decodes strictly: one invalid byte would end the reader
            process.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        return cls(process)

    @property
    def pid(self) -> int:
        return int(self._process.pid)

    def read(self) -> str:
        """The next output (blocks until there is some). Raises EOFError once it has ended."""
        return self._process.read(65536)

    def write(self, text: str) -> None:
        self._process.write(text)

    def resize(self, cols: int, rows: int) -> None:
        self._process.setwinsize(rows, cols)

    def exit_code(self) -> int | None:
        """The exit status, for the reader once it has seen the end: on Linux and macOS it
        waits for the program, then releases the terminal."""
        if sys.platform != "win32":
            self._process.wait()
            self._reaped.set()
            self._process.fileobj.close()
        return getattr(self._process, "exitstatus", None)

    def kill(self) -> None:
        """Stop the program; the reader then sees the end and releases the terminal.

        On Windows `close` also frees the sockets pywinpty keeps (`terminate` alone leaves
        them open). On Linux and macOS ptyprocess' `close` must not be called while another
        thread reads: it waits for the buffer's lock, held until the program prints. Signals
        go to the program's process group instead (it leads its own session)."""
        if sys.platform == "win32":
            self._process.close(force=True)
            return
        for signals in ((signal.SIGHUP, signal.SIGCONT), (signal.SIGKILL,)):
            for number in signals:
                if self._reaped.is_set():
                    return
                try:
                    os.killpg(self.pid, number)
                except ProcessLookupError:
                    return
            self._reaped.wait(STOP_GRACE)
