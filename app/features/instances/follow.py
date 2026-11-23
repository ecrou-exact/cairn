"""Show a log file and what is added to it, until closed (D-061): run in a Cairn terminal, the
same on every OS. Standard library only. A file cut or replaced (rotation) is read again."""

from __future__ import annotations

import os
import sys
import time

TAIL = 128 * 1024
PAUSE = 0.4


def main() -> int:
    path, out = sys.argv[1], sys.stdout.buffer
    handle, place = None, 0
    while True:
        try:
            size, inode = os.stat(path).st_size, os.stat(path).st_ino
            if handle is not None and (size < place or os.fstat(handle.fileno()).st_ino != inode):
                handle.close()
                handle, place = None, 0
            if handle is None:
                handle = open(path, "rb")  # noqa: SIM115 (kept open while followed)
                if size > TAIL:
                    handle.seek(size - TAIL)
                    handle.readline()  # the first line may be cut
            data = handle.read()
            place = handle.tell()
        except FileNotFoundError:
            data = b""  # between two rotations
        except OSError as exc:
            print(f"{path}: {exc}", flush=True)
            return 1
        if data:
            out.write(data)
            out.flush()
        else:
            time.sleep(PAUSE)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
