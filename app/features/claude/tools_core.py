"""The tools Claude has and uses (D-072): Cairn's own, with what each does and whether the owner
is asked; and every tool called in recent conversations, counted from their transcripts. Only
the end of each transcript is read (as for the context gauge), and again only when it changed.
Names and counts: what a tool was given or answered is not kept."""

from __future__ import annotations

import asyncio
import json
import time
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

from flask import current_app

from app.core.utils.settings import get_setting
from app.features.claude import mcp_server, transcript_core

DAYS = 7
KINDS = {"cairn": "Cairn", "claude": "Claude Code", "server": "Other MCP servers", "skill": "Skills"}


@cache
def _described() -> dict[str, str]:
    """What Cairn's tools say of themselves."""
    server = mcp_server.build(current_app._get_current_object(), None)
    tools = asyncio.run(server.list_tools())
    return {tool.name: " ".join((tool.description or "").split()) for tool in tools}


_counted: dict[Path, tuple[float, dict[str, list[float]]]] = {}


def _calls(path: Path) -> dict[str, list[float]]:
    """tool → [how many calls, how many failed, when the last] in the end of a transcript."""
    moved = path.stat().st_mtime
    known = _counted.get(path)
    if known and known[0] == moved:
        return known[1]
    found: dict[str, list[float]] = {}
    names: dict[str, str] = {}
    for line in transcript_core.tail_lines(path):
        if '"tool_use"' not in line and '"tool_result"' not in line:
            continue
        try:
            entry = json.loads(line)
            content = entry["message"]["content"]
        except (ValueError, KeyError, TypeError):
            continue
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and entry.get("type") == "assistant":
                name, data = str(block.get("name", "")), block.get("input")
                if name == "Skill" and isinstance(data, dict):
                    name = f"skill:{data.get('skill') or 'skill'}"
                names[str(block.get("id"))] = name
                row = found.setdefault(name[:120], [0, 0, 0.0])
                row[0] += 1
                row[2] = max(row[2], transcript_core.epoch(str(entry.get("timestamp") or "")))
            elif block.get("type") == "tool_result" and block.get("is_error"):
                name = names.get(str(block.get("tool_use_id")))
                if name:
                    found[name[:120]][1] += 1
    if len(_counted) > 500:
        _counted.clear()
    _counted[path] = (moved, found)
    return found


def _kind(name: str) -> str:
    if name.startswith("skill:"):
        return "skill"
    if name.startswith(f"mcp__{mcp_server.SERVER_NAME}__"):
        return "cairn"
    return "server" if name.startswith("mcp__") else "claude"


def _label(name: str) -> tuple[str, str]:
    """(label, where it comes from)"""
    if name.startswith("skill:"):
        return name.removeprefix("skill:"), "skill"
    if name.startswith("mcp__"):
        _, server, tool = [*name.split("__", 2), "", ""][:3]
        return tool, server
    return name, "Claude Code"


def overview(search: str = "", kind: str = "") -> dict[str, Any]:
    """Every tool, the most used first; `search` in names and descriptions, `kind` one of KINDS."""
    since = time.time() - DAYS * 86400
    calls: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    last: dict[str, float] = {}
    conversations: Counter[str] = Counter()
    read = 0
    for path in transcript_core.projects_root().glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime < since:
                continue
            found = _calls(path)
        except OSError:
            continue
        read += 1
        for name, (count, wrong, at) in found.items():
            calls[name] += int(count)
            failed[name] += int(wrong)
            last[name] = max(last.get(name, 0.0), at)
            conversations[name] += 1
    described = _described()
    ours = {f"mcp__{mcp_server.SERVER_NAME}__{name}" for name in described}
    allowed = bool(get_setting("claude.cairn_writes_allowed"))  # D-102
    words, rows = search.lower().split(), []
    for name in {*calls, *ours}:
        label, source = _label(name)
        about = described.get(label, "") if _kind(name) == "cairn" else ""
        row = {
            "name": name,
            "label": label,
            "source": source,
            "kind": _kind(name),
            "about": about,
            "asks": label in mcp_server.WRITE_TOOLS and not allowed if name in ours else None,
            "calls": calls[name],
            "failed": failed[name],
            "conversations": conversations[name],
            "last": last.get(name) or None,
        }
        text = f"{label} {source} {about}".lower()
        if (not kind or row["kind"] == kind) and all(word in text for word in words):
            rows.append(row)
    rows.sort(key=lambda row: (-row["calls"], row["source"], row["label"]))
    return {
        "tools": rows,
        "kinds": KINDS,
        "days": DAYS,
        "conversations": read,
        "calls": sum(calls.values()),
        "most": max([row["calls"] for row in rows], default=0),
    }
