"""A Claude Code conversation in a terminal, read from its transcript as it grows (D-075): for a
session Cairn did not open, whose own terminal cannot be mirrored. Read-only: nothing typed here
reaches it. Run by Cairn as `python conversation_view.py <transcript.jsonl>`.

Standard library only. What a conversation holds (a command's output, a web page…) never drives
this terminal: control characters are removed before anything is printed.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any

TAIL = 3 * 1024 * 1024
PAUSE = 0.5
RESULT_LINES = 10
DIFF_LINES = 14
LINE_MAX = 400
RESET, BOLD, DIM, RED, GREEN, ORANGE, BAR = (
    "\x1b[0m",
    "\x1b[1m",
    "\x1b[2m",
    "\x1b[31m",
    "\x1b[32m",
    "\x1b[38;5;209m",
    "\x1b[48;5;237m",
)
ESCAPES = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?|\x1b.")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
ABOUT = ("description", "file_path", "notebook_path", "pattern", "query", "url", "skill", "prompt")
CHANGES = {"Edit": ("old_string", "new_string"), "Write": (None, "content")}


def clean(text: Any) -> str:
    plain = ESCAPES.sub("", str(text)).replace("\r\n", "\n").replace("\t", "    ")
    return CONTROL.sub("", plain)


def lines_of(text: Any, most: int) -> list[str]:
    found = clean(text).strip("\n").split("\n")
    shown = [line[:LINE_MAX] + ("…" if len(line) > LINE_MAX else "") for line in found[:most]]
    if len(found) > most:
        shown.append(f"… +{len(found) - most} lines")
    return shown


def words(content: Any) -> str:
    """The text of a message or a tool's answer."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict):
            kind = block.get("type")
            if kind == "text":
                parts.append(str(block.get("text", "")))
            elif kind == "image":
                parts.append("[image]")
    return "\n".join(part for part in parts if part)


def call(name: str, data: dict[str, Any]) -> list[str]:
    about = next(
        (data[key] for key in ABOUT if isinstance(data.get(key), str) and data[key]),
        "",
    )
    if name == "Bash" and isinstance(data.get("command"), str):
        about = data["command"]
    head = lines_of(about, 1)[0] if about else ""
    out = [f"{GREEN}●{RESET} {BOLD}{clean(name)[:80]}{RESET}({head[:160]})"]
    if name in CHANGES:
        old, new = CHANGES[name]
        if old:
            out += [f"    {RED}- {line}{RESET}" for line in lines_of(data.get(old, ""), DIFF_LINES)]
        out += [f"    {GREEN}+ {line}{RESET}" for line in lines_of(data.get(new, ""), DIFF_LINES)]
    return out


def render(entry: Any) -> list[str]:
    """One transcript line, as it would read in Claude Code; nothing for what it does not show."""
    if not isinstance(entry, dict) or entry.get("isSidechain") or entry.get("isMeta"):
        return []
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content, out = message.get("content"), []
    if entry.get("type") == "user":
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                colour = RED if block.get("is_error") else DIM
                answer = lines_of(words(block.get("content")) or "(nothing)", RESULT_LINES)
                out += [f"  {colour}{'⎿ ' if n == 0 else '  '}{line}{RESET}" for n, line in enumerate(answer)]
        asked = clean(words(content)).strip()
        if asked and not asked.startswith("<"):
            mine = enumerate(lines_of(asked, 60))
            out += ["", *(f"{BAR}{BOLD}{'  ' if n else '❯ '}{line}{RESET}" for n, line in mine), ""]
    elif entry.get("type") == "assistant":
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and str(block.get("text", "")).strip():
                said = enumerate(lines_of(block["text"], 400))
                out += ["", *(f"{'  ' if n else ORANGE + '● ' + RESET}{line}" for n, line in said), ""]
            elif block.get("type") == "tool_use":
                data = block.get("input")
                out += call(str(block.get("name", "")), data if isinstance(data, dict) else {})
    return out


def show(raw: bytes) -> None:
    try:
        out = render(json.loads(raw))
    except (ValueError, RecursionError):
        return
    if out:
        sys.stdout.write("\r\n".join(out) + "\r\n")


def main() -> int:
    path, pending = sys.argv[1], b""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="")
    print(f"{DIM}Read-only: this conversation runs in another terminal.{RESET}\r\n", flush=True)
    with open(path, "rb") as handle:
        size = os.fstat(handle.fileno()).st_size
        if size > TAIL:
            handle.seek(size - TAIL)
            handle.readline()
            print(f"{DIM}… the beginning is not shown{RESET}\r\n")
        while True:
            data = handle.read(1024 * 1024)
            if not data:
                sys.stdout.flush()
                time.sleep(PAUSE)
                continue
            *complete, pending = (pending + data).split(b"\n")
            for raw in complete:
                show(raw)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(0)
