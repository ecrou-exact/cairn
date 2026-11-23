"""Cairn command line — the one entry point, identical on Linux, macOS and Windows.

python manage.py setup         first run: .env with a secret key, master key, database
python manage.py start         development server (auto-reload) on 127.0.0.1:7010
python manage.py serve         production server (gunicorn on Linux/macOS, waitress on Windows)
python manage.py worker        background job worker (run it next to start or serve)
python manage.py roadmap [file] import a plan (default: Cairn's own roadmap, docs/roadmap.json)
python manage.py upgrade       apply database migrations
python manage.py migrate "msg" create a migration after a model change
python manage.py test [args]   run the test suite (pytest arguments pass through)
python manage.py check         lint, security scan and tests — run before declaring a change done
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess  # nosec B404 (fixed argument lists only, never a shell)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SERVE_THREADS = 16


def _run(*args: str, env: dict[str, str] | None = None) -> int:
    return subprocess.call(list(args), cwd=ROOT, env={**os.environ, **(env or {})})  # noqa: S603  # nosec B603


def _flask(*args: str, env: dict[str, str] | None = None) -> int:
    return _run(sys.executable, "-m", "flask", "--app", "wsgi:app", *args, env=env)


def cmd_setup(_: argparse.Namespace) -> int:
    from dotenv import load_dotenv

    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            "# Cairn local configuration. Never commit this file.\n"
            f"CAIRN_SECRET_KEY={secrets.token_urlsafe(48)}\n"
            "CAIRN_ENV=development\n"
            "CAIRN_HOST=127.0.0.1\n"
            "CAIRN_PORT=7010\n"
            "# CAIRN_DATABASE_URL=postgresql+psycopg://cairn:password@localhost/cairn\n"
            "# CAIRN_DATA_DIR=/var/lib/cairn\n",
            encoding="utf-8",
        )
        if os.name == "posix":
            ENV_FILE.chmod(0o600)
        print(f"Created {ENV_FILE.name} with a new secret key.")
    load_dotenv(ENV_FILE)

    from app.config import get_config
    from app.core.security.vault import load_master_key

    master = load_master_key(get_config().data_dir(), create=True)
    print(f"Master key ready (stored in: {master.source}). Data directory: {get_config().data_dir()}")
    code = cmd_upgrade(_)
    if code == 0:
        print("Setup done. Start Cairn with `python manage.py start` and open http://127.0.0.1:7010")
    return code


def cmd_mcp(_: argparse.Namespace) -> int:
    """Cairn's MCP server over stdio, started by Claude Code for a session opened in Cairn
    (D-052). Nothing but the protocol may be written to stdout: logs go to stderr."""
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    from app.features.claude.mcp_server import serve

    serve()
    return 0


def cmd_start(_: argparse.Namespace) -> int:
    host = os.environ.get("CAIRN_HOST", "127.0.0.1")
    port = os.environ.get("CAIRN_PORT", "7010")
    env = {"CAIRN_WEB": "1", "CAIRN_RELOAD": "1"}
    return _flask("run", "--debug", "--host", host, "--port", port, env=env)


def cmd_serve(_: argparse.Namespace) -> int:
    host = os.environ.get("CAIRN_HOST", "127.0.0.1")
    port = os.environ.get("CAIRN_PORT", "7010")
    env = {"CAIRN_ENV": os.environ.get("CAIRN_ENV", "production"), "CAIRN_WEB": "1"}
    # Threads, not processes alone: every open tab keeps one live-events stream (SSE) open.
    if os.name == "nt":
        return _run(
            sys.executable,
            "-m",
            "waitress",
            f"--listen={host}:{port}",
            f"--threads={SERVE_THREADS}",
            "wsgi:app",
            env=env,
        )
    return _run(
        sys.executable,
        "-m",
        "gunicorn",
        "--bind",
        f"{host}:{port}",
        "--workers",
        "1",  # one process: Claude terminals live in it (D-050); threads serve the pages
        "--worker-class",
        "gthread",
        "--threads",
        str(SERVE_THREADS),
        "wsgi:app",
        env=env,
    )


def cmd_worker(_: argparse.Namespace) -> int:
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    from app import create_app
    from app.core.jobs.worker import Worker, WorkerLockError

    try:
        Worker(create_app()).run_forever()
    except WorkerLockError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def cmd_upgrade(_: argparse.Namespace) -> int:
    return _flask("db", "upgrade")


def cmd_migrate(args: argparse.Namespace) -> int:
    return _flask("db", "migrate", "-m", args.message)


def cmd_test(args: argparse.Namespace) -> int:
    return _run(sys.executable, "-m", "pytest", *args.pytest_args, env={"CAIRN_ENV": "testing"})


def cmd_check(_: argparse.Namespace) -> int:
    steps = [
        (sys.executable, "-m", "ruff", "check", "."),
        (sys.executable, "-m", "ruff", "format", "--check", "."),
        (sys.executable, "-m", "bandit", "-q", "-c", "pyproject.toml", "-r", "app", "manage.py"),
    ]
    for step in steps:
        if (code := _run(*step)) != 0:
            return code
    return cmd_test(argparse.Namespace(pytest_args=["-q"]))


def cmd_roadmap(args: argparse.Namespace) -> int:
    import json

    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    from app import create_app
    from app.features.projects.plan_import_core import PlanError, import_plan

    path = Path(args.file)
    with create_app().app_context():
        try:
            counts = import_plan(json.loads(path.read_text(encoding="utf-8")))
        except (PlanError, ValueError) as exc:
            print(f"Could not import {path.name}: {exc}", file=sys.stderr)
            return 1
    print(
        f"{path.name}: {counts['created']} tasks created, {counts['existing']} already there, "
        f"{counts['dependencies']} dependencies added."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="manage.py", description="Cairn command line.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="first run").set_defaults(func=cmd_setup)
    sub.add_parser("start", help="development server").set_defaults(func=cmd_start)
    sub.add_parser("serve", help="production server").set_defaults(func=cmd_serve)
    sub.add_parser("worker", help="background job worker").set_defaults(func=cmd_worker)
    sub.add_parser("mcp", help="Cairn's MCP server over stdio (started by Claude Code)").set_defaults(
        func=cmd_mcp
    )
    roadmap = sub.add_parser("roadmap", help="import a plan (default: Cairn's own roadmap)")
    roadmap.add_argument("file", nargs="?", default=str(ROOT / "docs" / "roadmap.json"))
    roadmap.set_defaults(func=cmd_roadmap)
    sub.add_parser("upgrade", help="apply migrations").set_defaults(func=cmd_upgrade)
    migrate = sub.add_parser("migrate", help="create a migration")
    migrate.add_argument("message")
    migrate.set_defaults(func=cmd_migrate)
    sub.add_parser("test", help="run tests (extra arguments go to pytest)").set_defaults(func=cmd_test)
    sub.add_parser("check", help="lint + security scan + tests").set_defaults(func=cmd_check)
    args, extra = parser.parse_known_args()
    if args.command == "test":
        args.pytest_args = extra
    elif extra:
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
