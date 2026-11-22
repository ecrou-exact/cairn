"""One program in a pseudo-terminal, the same on every OS (D-050).

Windows uses ConPTY through `pywinpty`; Linux and macOS use `ptyprocess`. Both read and
write text (UTF-8), resize, report the exit status and can be killed. The program is given
as an argv list: no shell is ever involved.
"""

from __future__ import annotations

import sys
from typing import Any


class Pty:
    def __init__(self, process: Any) -> None:
        self._process = process

    @classmethod
    def spawn(cls, argv: list[str], *, cwd: str, env: dict[str, str], cols: int, rows: int) -> Pty:
        if sys.platform == "win32":
            from winpty import PtyProcess

            process = PtyProcess.spawn(argv, cwd=cwd, env=env, dimensions=(rows, cols))
        else:
            from ptyprocess import PtyProcessUnicode

            process = PtyProcessUnicode.spawn(argv, cwd=cwd, env=env, dimensions=(rows, cols))
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

    def alive(self) -> bool:
        return bool(self._process.isalive())

    def exit_code(self) -> int | None:
        return getattr(self._process, "exitstatus", None)

    def kill(self) -> None:
        """Stop the program and release the terminal (`close` also frees the sockets
        pywinpty keeps; `terminate` alone leaves them open)."""
        self._process.close(force=True)
