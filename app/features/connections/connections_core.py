"""Connected accounts (PROJECT_BRIEF.md §2.7 accounts, §9 GitHub, §6 Claude).

Claude can be reached two ways: **Claude Code on this machine** (default for runs: it uses
its own sign-in, so the owner's subscription works, nothing stored here) or an Anthropic
**API key** (fallback, kept in the vault).

The owner pastes a token once; it goes straight to the vault and is never shown again
(only its last characters). A job checks it with the service and records who it belongs
to. Other features ask `token_for(provider)` for the default account's token:

- GitHub: titles of private issues and pull requests in link previews (now), the GitHub
  inbox and sync (Phase 7);
- Anthropic: the key Claude runs use (Phase 5).

Credential changes are not undoable (they cannot be replayed without the secret), so they
are logged but do not go through history batches; removing an account erases its token.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 (argv lists only, see _claude_code_identity)
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.connection import CONNECTION_PROVIDERS, Connection
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.security.secret_core import delete_secret, get_secret, put_secret
from app.core.security.vault import masked
from app.core.utils.events import publish
from app.core.utils.logger import log_action

TIMEOUT = 15


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    icon: str  # Font Awesome classes
    token_label: str
    help: str
    uses: str


PROVIDERS = {
    "claude_code": Provider(
        "claude_code",
        "Claude Code (this machine)",
        "fa-solid fa-claude",
        "",
        "Uses the Claude Code installed on this machine, signed in with your own account (subscription or "
        "console). Nothing to paste: Cairn finds the `claude` command, or uses the path you give, and checks "
        "its version. Sign in once in a terminal with `claude` if you have not yet.",
        "Claude runs on your tasks go through it by default (Phase 5); an API key is only a fallback.",
    ),
    "github": Provider(
        "github",
        "GitHub",
        "fa-brands fa-github",
        "Personal access token",
        "Create a fine-grained token at github.com → Settings → Developer settings, with read access to the "
        "repositories Cairn should see (Contents, Issues, Pull requests, Metadata).",
        "Titles of private issues and pull requests in link previews; the GitHub inbox and sync later.",
    ),
    "anthropic": Provider(
        "anthropic",
        "Claude (Anthropic API)",
        "fa-solid fa-claude",
        "API key",
        "Create a key in the Claude Console (platform.claude.com → API keys). "
        "Each run will use the default key; usage is billed to its workspace.",
        "Claude runs on your tasks (Phase 5): the key is passed to each run, never written to disk.",
    ),
    "other": Provider(
        "other",
        "Other service",
        "fa-solid fa-key",
        "Token or key",
        "Any token you want Cairn to keep in its encrypted vault for modules and runs "
        "(GitLab, a CI, a cloud API…).",
        "Kept encrypted; modules and runs can be given access to it explicitly.",
    ),
}


class ConnectionError_(ValueError):
    pass


def _get(connection_id: uuid.UUID) -> Connection:
    found = db.session.get(Connection, connection_id)
    if found is None or found.is_deleted:
        raise ConnectionError_("This account does not exist.")
    return found


def _changed(connection: Connection) -> None:
    publish(
        "connection.changed",
        {"id": str(connection.id), "state": connection.state, "targets": ["connections"]},
    )


def connections() -> list[Connection]:
    return list(
        db.session.scalars(
            select(Connection)
            .where(Connection.deleted_at.is_(None))
            .order_by(Connection.provider, Connection.is_default.desc(), Connection.label)
        )
    )


def _check_token(token: str) -> str:
    token = token.strip()
    if len(token) < 8 or any(c.isspace() for c in token):
        raise ConnectionError_("Paste the whole token, without spaces.")
    return token


def add(provider: str, label: str, token: str, path: str = "") -> Connection:
    if provider not in CONNECTION_PROVIDERS:
        raise ConnectionError_("Unknown service.")
    label = " ".join(label.split())[:80] or PROVIDERS[provider].label
    if provider == "claude_code":
        return _add_claude_code(label, path)
    token = _check_token(token)
    has_default = db.session.scalar(
        select(Connection.id).where(
            Connection.provider == provider, Connection.is_default.is_(True), Connection.deleted_at.is_(None)
        )
    )
    connection = Connection(
        provider=provider, label=label, hint=masked(token), is_default=has_default is None
    )
    db.session.add(connection)
    db.session.flush()
    put_secret(connection.secret_name, token)
    log_action(
        "connection.create",
        target_type="connection",
        target_id=connection.id,
        meta={"provider": provider, "label": label},
    )
    _queue_check(connection)
    db.session.commit()
    return connection


def _add_claude_code(label: str, path: str) -> Connection:
    """No secret: Claude Code signs in on its own. `path` overrides finding `claude` on PATH."""
    path = path.strip()
    if path and not Path(path).is_file():
        raise ConnectionError_("No file at this path. Leave it empty to find `claude` automatically.")
    exists = db.session.scalar(
        select(Connection.id).where(Connection.provider == "claude_code", Connection.deleted_at.is_(None))
    )
    connection = Connection(
        provider="claude_code",
        label=label,
        hint="",
        is_default=exists is None,
        facts={"path": path} if path else {},
    )
    db.session.add(connection)
    db.session.flush()
    log_action(
        "connection.create",
        target_type="connection",
        target_id=connection.id,
        meta={"provider": "claude_code", "label": label},
    )
    _queue_check(connection)
    db.session.commit()
    return connection


def claude_code_path() -> str | None:
    """The `claude` executable Claude runs use: the default connection's path, else PATH."""
    connection = db.session.scalar(
        select(Connection).where(
            Connection.provider == "claude_code",
            Connection.is_default.is_(True),
            Connection.deleted_at.is_(None),
        )
    )
    configured = (connection.facts or {}).get("path") if connection is not None else None
    return configured or shutil.which("claude")


def replace_token(connection_id: uuid.UUID, token: str) -> Connection:
    connection = _get(connection_id)
    if connection.provider == "claude_code":
        raise ConnectionError_("Claude Code has no token: it uses its own sign-in.")
    token = _check_token(token)
    put_secret(connection.secret_name, token)
    connection.hint = masked(token)
    connection.identity, connection.error, connection.facts = "", "", {}
    log_action("connection.token", target_type="connection", target_id=connection.id)
    _queue_check(connection)
    db.session.commit()
    return connection


def rename(connection_id: uuid.UUID, label: str) -> Connection:
    connection = _get(connection_id)
    label = " ".join(label.split())[:80]
    if not label:
        raise ConnectionError_("Give it a name.")
    log_action(
        "connection.rename",
        target_type="connection",
        target_id=connection.id,
        diff={"label": [connection.label, label]},
    )
    connection.label = label
    db.session.commit()
    return connection


def make_default(connection_id: uuid.UUID) -> Connection:
    connection = _get(connection_id)
    for other in db.session.scalars(
        select(Connection).where(Connection.provider == connection.provider, Connection.deleted_at.is_(None))
    ):
        other.is_default = other.id == connection.id
    log_action("connection.default", target_type="connection", target_id=connection.id)
    db.session.commit()
    return connection


def remove(connection_id: uuid.UUID) -> None:
    """Removes the account and erases its token from the vault (not kept in the trash)."""
    connection = _get(connection_id)
    if connection.provider != "claude_code":
        delete_secret(connection.secret_name)
    log_action(
        "connection.delete",
        target_type="connection",
        target_id=connection.id,
        meta={"provider": connection.provider, "label": connection.label},
        level="warning",
    )
    was_default, provider = connection.is_default, connection.provider
    db.session.delete(connection)
    db.session.flush()
    if was_default:
        following = db.session.scalar(
            select(Connection)
            .where(Connection.provider == provider, Connection.deleted_at.is_(None))
            .limit(1)
        )
        if following is not None:
            following.is_default = True
    db.session.commit()


def token_for(provider: str) -> str | None:
    """The default account's token for `provider`, or None. Only for server-side use."""
    connection = db.session.scalar(
        select(Connection).where(
            Connection.provider == provider, Connection.is_default.is_(True), Connection.deleted_at.is_(None)
        )
    )
    return get_secret(connection.secret_name) if connection is not None else None


# -- checking a token ------------------------------------------------------------------------


def _queue_check(connection: Connection) -> None:
    if connection.provider == "other":
        connection.state = "unchecked"
        return
    connection.state = "checking"
    jobs_core.enqueue(
        "connections.check",
        {"connection_id": str(connection.id)},
        title=f"Check the {connection.label} account",
    )


def request_check(connection_id: uuid.UUID) -> Connection:
    connection = _get(connection_id)
    if connection.provider == "other":
        raise ConnectionError_("Cairn cannot check tokens of other services.")
    _queue_check(connection)
    db.session.commit()
    return connection


def _github_identity(token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Cairn",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310  # nosec B310
            data = json.loads(response.read(200_000))
            scopes = response.headers.get("X-OAuth-Scopes")
    except urllib.error.HTTPError as exc:
        reason = (
            "GitHub refused the token (revoked or mistyped)."
            if exc.code == 401
            else f"GitHub answered {exc.code}."
        )
        raise ConnectionError_(reason) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectionError_(f"Could not reach GitHub ({getattr(exc, 'reason', exc)}).") from exc
    facts = {"name": data.get("name") or "", "html_url": data.get("html_url") or ""}
    if scopes is not None:
        facts["scopes"] = [s.strip() for s in scopes.split(",") if s.strip()]
    return {"identity": data.get("login") or "", "facts": facts}


def _claude_code_identity(path: str | None) -> dict[str, Any]:
    """`claude --version`: read-only, no shell, short timeout."""
    if not path:
        raise ConnectionError_("Claude Code was not found on this machine (no `claude` command on PATH).")
    try:
        done = subprocess.run(  # noqa: S603  # nosec B603 (argv list, the owner's own executable)
            [path, "--version"], capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConnectionError_(f"Could not run Claude Code ({exc}).") from exc
    version = (done.stdout or done.stderr).strip().splitlines()[0] if (done.stdout or done.stderr) else ""
    if done.returncode != 0 or not version:
        raise ConnectionError_(f"Claude Code did not answer (exit code {done.returncode}).")
    return {"identity": version[:120], "facts": {"path": path}}


def _anthropic_identity(token: str) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=token, max_retries=0, timeout=TIMEOUT)
    try:
        page = client.models.list(limit=20)
    except anthropic.AuthenticationError as exc:
        raise ConnectionError_("Anthropic refused the key (revoked or mistyped).") from exc
    except anthropic.PermissionDeniedError as exc:
        raise ConnectionError_("This key may not list models; check its workspace permissions.") from exc
    except anthropic.APIConnectionError as exc:
        raise ConnectionError_("Could not reach the Anthropic API.") from exc
    except anthropic.APIStatusError as exc:
        raise ConnectionError_(f"The Anthropic API answered {exc.status_code}.") from exc
    models = [model.id for model in page.data]
    return {"identity": "API key", "facts": {"models": models[:20]}}


CHECKS = {"claude_code": _claude_code_identity, "github": _github_identity, "anthropic": _anthropic_identity}


def run_check(connection_id: uuid.UUID) -> Connection:
    """Called by the `connections.check` job: ask the service who the token belongs to."""
    connection = _get(connection_id)
    if connection.provider == "claude_code":
        argument = (connection.facts or {}).get("path") or shutil.which("claude")
    else:
        argument = get_secret(connection.secret_name)
        if argument is None:
            raise ConnectionError_("The token is missing from the vault.")
    try:
        found = CHECKS[connection.provider](argument)
    except ConnectionError_ as exc:
        connection.state, connection.error = "failed", str(exc)
    else:
        connection.state, connection.error = "ok", ""
        connection.identity, connection.facts = found["identity"][:120], found["facts"]
    connection.checked_at = utcnow()
    log_action(
        "connection.check",
        target_type="connection",
        target_id=connection.id,
        meta={"state": connection.state},
        level="info" if connection.state == "ok" else "warning",
    )
    _changed(connection)
    db.session.commit()
    return connection
