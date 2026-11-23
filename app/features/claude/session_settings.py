"""What Claude Code is told, through `--settings`, in every session Cairn opens (D-056, D-064):
Cairn's status line, and permission rules the session's own mode does not lift. Cairn assumes
the owner approves changes; with a permissive mode (auto) Claude Code would not ask, so the
rules ask for them. What they refuse are files that would give a session the owner's rights in
Cairn. A rule covers Claude Code's tools: it is not a sandbox for the commands it runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import current_app

from app.core.security.vault import KEY_FILE_NAME
from app.features.claude import limits_core, main_core, mcp_server

ASK_COMMANDS = ("git push", "git merge", "systemctl", "gh pr merge", "gh release")


def _rule(tool: str, path: Path, pattern: str = "") -> str:
    """A rule on an absolute path (`//path` in Claude Code's syntax)."""
    return f"{tool}(//{path.as_posix().lstrip('/')}{pattern})"


def permissions(cwd: str) -> dict[str, list[str]]:
    data, code = Path(current_app.config["CAIRN_DATA_DIR"]).resolve(), main_core.code_folder()
    private = [(code / ".env", ""), (data / KEY_FILE_NAME, ""), (data, "/*.db*"), (data / "claude", "/**")]
    deny = [_rule(tool, path, pattern) for path, pattern in private for tool in ("Read", "Edit")]
    ask = [f"mcp__{mcp_server.SERVER_NAME}__{name}" for name in mcp_server.WRITE_TOOLS]
    if cwd == str(main_core.folder()):  # it reads other Claudes' notes and may change Cairn itself
        ask.append(_rule("Edit", code, "/**"))
        ask += [f"Bash({command} *)" for command in ASK_COMMANDS]
    return {"deny": deny, "ask": ask}


def settings_json(cwd: str) -> str:
    return json.dumps({"statusLine": limits_core.status_line(), "permissions": permissions(cwd)})
