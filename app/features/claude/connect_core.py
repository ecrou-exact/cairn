"""Cairn in every Claude Code of this machine (D-080): `manage.py claude-connect on | off | status | show`.

Three things of the owner's own Claude Code configuration, shown first, put and removed together: the
MCP server (by `claude mcp`), a skill that says when to use it, and rules so that what writes in Cairn
is asked for in every permission mode. Nothing that is not Cairn's is changed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
import time
from pathlib import Path

from app.config import ROOT_DIR
from app.features.claude import mcp_server

MARK = "Written by Cairn (manage.py claude-connect)"
SKILL = Path(__file__).with_name("outside_skill.md")


class ConnectError(ValueError):
    pass


def _home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def skill_file() -> Path:
    return _home() / "skills" / "cairn" / "SKILL.md"


def settings_file() -> Path:
    return _home() / "settings.json"


HOOK = "claude-hook"


def hook_command() -> str:
    return " ".join(f'"{part}"' for part in server_command()).replace('"mcp"', HOOK)


def session_context(raw: str) -> str:
    """What Claude Code is told when a session starts in a Cairn project's folder (D-100)."""
    import json as _json

    from app import create_app
    from app.features.projects import place_core
    from app.features.tasks import tasks_core

    cwd = (_json.loads(raw or "{}") or {}).get("cwd") or os.getcwd()
    with create_app().app_context():
        project = place_core.project_for(cwd)
        if project is None:
            return ""
        nxt = [t.title for t in tasks_core.next_actions(limit=3, project_id=project.id)]
        return (
            f"This folder is the project “{project.name}” in Cairn, the owner's planning workspace "
            f"(server `cairn`, /cairn). Keep it true as you work: find the task you work on (this_project, "
            "list_tasks) or create it, set_task_status, tick_checklist and the subtasks as they are done, "
            "link_work the branch and the pull request, and before you say the work is done comment_on_task "
            "with what was done. The owner relies on Cairn to find everything later."
            + (f" Next in this project: {'; '.join(nxt)}." if nxt else "")
        )


def _hooks_mine(entry: dict) -> bool:
    return any(HOOK in str(hook.get("command", "")) for hook in entry.get("hooks", []))


def rules() -> list[str]:
    return [f"mcp__{mcp_server.SERVER_NAME}__{name}" for name in mcp_server.WRITE_TOOLS]


def server_command() -> list[str]:
    return [sys.executable, str(ROOT_DIR / "manage.py"), "mcp"]


def _claude() -> str:
    found = shutil.which("claude")
    if found is None:
        raise ConnectError("Claude Code was not found on this machine.")
    return found


def _mcp(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603  # nosec B603
            [_claude(), "mcp", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
            cwd=Path.home(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConnectError(f"Claude Code did not answer: {exc}") from exc


def _registered() -> bool:
    return _mcp("get", mcp_server.SERVER_NAME).returncode == 0


def _settings() -> dict:
    path = settings_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConnectError(f"{path} cannot be read: nothing was changed.") from exc
    if not isinstance(data, dict):
        raise ConnectError(f"{path} is not a settings file: nothing was changed.")
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict) or not isinstance(permissions.get("ask", []), list):
        raise ConnectError(f"{path} has rules Cairn does not understand: nothing was changed.")
    return data


def _write(data: dict) -> None:
    """Whole or not at all, with a copy of what was there."""
    path = settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(f"settings.json.cairn-{time.strftime('%Y%m%d-%H%M%S')}.bak"))
    target = path.resolve()  # the file itself when settings.json is a link
    draft = target.with_name(f"{target.name}.cairn-new")
    draft.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if target.exists():
        shutil.copymode(target, draft)
    draft.replace(target)


def _ours() -> bool:
    try:
        return MARK in skill_file().read_text(encoding="utf-8")
    except OSError:
        return False


def show() -> str:
    command = " ".join(f'"{part}"' if " " in part else part for part in server_command())
    return "\n".join(
        [
            "Put in your Claude Code, for every folder of this machine:",
            "",
            "1. The MCP server, by this command:",
            f"   claude mcp add --scope user {mcp_server.SERVER_NAME} -- {command}",
            "",
            f"2. Rules in {settings_file()} (permissions.ask), so that writing in Cairn is always asked:",
            *(f"   {rule}" for rule in rules()),
            "",
            f"3. A session start hook in {settings_file()}: in a Cairn project's folder, Claude is told so",
            "   and to keep its tasks true; silent anywhere else:",
            f"   {hook_command()}",
            "",
            f"4. A skill, {skill_file()}:",
            "",
            *(f"   {line}".rstrip() for line in SKILL.read_text(encoding="utf-8").splitlines()),
            "",
            "Removed by: manage.py claude-connect off",
        ]
    )


def status() -> dict[str, bool]:
    data = _settings()
    asked = data.get("permissions", {}).get("ask", [])
    hook = any(_hooks_mine(e) for e in data.get("hooks", {}).get("SessionStart", []))
    return {"server": _registered(), "rules": set(rules()) <= set(asked), "skill": _ours(), "hook": hook}


def on() -> None:
    """Everything is checked before anything is changed; safe to run again after an update."""
    data = _settings()
    if skill_file().exists() and not _ours():
        raise ConnectError(f"{skill_file()} exists and is not Cairn's: nothing was changed.")
    known = _mcp("get", mcp_server.SERVER_NAME)
    if known.returncode == 0 and "manage.py" not in known.stdout:
        raise ConnectError("Another MCP server is named “cairn”: nothing was changed.")
    if known.returncode == 0:
        _mcp("remove", "--scope", "user", mcp_server.SERVER_NAME)
    added = _mcp("add", "--scope", "user", mcp_server.SERVER_NAME, "--", *server_command())
    if added.returncode:
        raise ConnectError((added.stderr or added.stdout).strip()[:300] or "claude mcp add failed.")
    permissions = data.setdefault("permissions", {})
    asked = permissions.setdefault("ask", [])
    missing = [rule for rule in rules() if rule not in asked]
    starts = data.setdefault("hooks", {}).setdefault("SessionStart", [])
    mine = {"hooks": [{"type": "command", "command": hook_command(), "timeout": 20}]}
    hook_changed = [e for e in starts if _hooks_mine(e)] != [mine]
    if hook_changed:
        starts[:] = [e for e in starts if not _hooks_mine(e)] + [mine]
    if missing or hook_changed:
        asked += missing
        _write(data)
    skill_file().parent.mkdir(parents=True, exist_ok=True)
    skill_file().write_text(SKILL.read_text(encoding="utf-8"), encoding="utf-8")


def off() -> None:
    data = _settings()
    if "manage.py" in _mcp("get", mcp_server.SERVER_NAME).stdout:
        _mcp("remove", "--scope", "user", mcp_server.SERVER_NAME)
    permissions = data.get("permissions", {})
    asked = permissions.get("ask", [])
    mine = f"mcp__{mcp_server.SERVER_NAME}__"
    kept = [rule for rule in asked if not str(rule).startswith(mine)]
    hooks = data.get("hooks", {})
    starts = hooks.get("SessionStart", [])
    if any(_hooks_mine(e) for e in starts):
        hooks["SessionStart"] = [e for e in starts if not _hooks_mine(e)]
        if not hooks["SessionStart"]:
            del hooks["SessionStart"]
        if not hooks:
            del data["hooks"]
        _write(data)
    if kept != asked:
        permissions["ask"] = kept
        if not kept:
            del permissions["ask"]
        if not permissions:
            del data["permissions"]
        _write(data)
    if _ours():
        skill_file().unlink()
        if not any(skill_file().parent.iterdir()):
            skill_file().parent.rmdir()
