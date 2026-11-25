"""What Claude Code is told, through `--settings`, in every session Cairn opens (D-056, D-064):
Cairn's status line, and permission rules the session's own mode does not lift. Writing in Cairn
follows the session's mode (D-101): asked in the default mode, not in auto, where a question at
every step teaches the owner to accept everything, a push to main included. In Cairn's main folder,
changing Cairn's code, pushing and merging stay asked. With `claude.cairn_writes_allowed` (D-102),
writing in Cairn is allowed in every mode. What the rules refuse are files that would
give a session the owner's rights in Cairn. A rule covers Claude Code's tools: it is not a sandbox
for the commands it runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import current_app

from app.core.security.vault import KEY_FILE_NAME
from app.core.utils.settings import get_setting
from app.features.claude import limits_core, main_core, mcp_server

ASK_COMMANDS = ("git push", "git merge", "systemctl", "gh pr merge", "gh release")


def _rule(tool: str, path: Path, pattern: str = "") -> str:
    """A rule on an absolute path (`//path` in Claude Code's syntax)."""
    return f"{tool}(//{path.as_posix().lstrip('/')}{pattern})"


def permissions(cwd: str) -> dict[str, list[str]]:
    data, code = Path(current_app.config["CAIRN_DATA_DIR"]).resolve(), main_core.code_folder()
    private = [(code / ".env", ""), (data / KEY_FILE_NAME, ""), (data, "/*.db*"), (data / "claude", "/**")]
    deny = [_rule(tool, path, pattern) for path, pattern in private for tool in ("Read", "Edit")]
    ask: list[str] = []
    if cwd == str(main_core.folder()):  # it reads other Claudes' notes and may change Cairn itself
        ask.append(_rule("Edit", code, "/**"))
        ask += [f"Bash({command} *)" for command in ASK_COMMANDS]
    allow = cairn_writes() if get_setting("claude.cairn_writes_allowed") else []
    return {"deny": deny, "ask": ask, "allow": allow}


def cairn_writes() -> list[str]:
    """Cairn's tools that change something, as Claude Code names them."""
    return [f"mcp__{mcp_server.SERVER_NAME}__{name}" for name in mcp_server.WRITE_TOOLS]


def settings_json(cwd: str) -> str:
    return json.dumps({"statusLine": limits_core.status_line(), "permissions": permissions(cwd)})
