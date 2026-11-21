"""Built-in maintenance jobs."""

from __future__ import annotations

import shutil

from flask import current_app
from sqlalchemy import text

from app.core.extensions import db
from app.core.jobs.context import JobContext
from app.core.jobs.jobs_core import prune_finished
from app.core.jobs.registry import register_handler
from app.core.security.secret_core import delete_secret, get_secret, put_secret
from app.core.utils.events import prune_events
from app.core.utils.settings import get_setting

MIN_FREE_BYTES = 1024**3


@register_handler(
    "system.prune", lane="system", title="Clean up old jobs and events", max_attempts=2, manual=True
)
def prune(context: JobContext, payload: dict) -> dict:
    days = int(payload.get("older_than_days") or get_setting("jobs.retention_days"))
    context.log(f"Deleting finished jobs older than {days} days.")
    jobs = prune_finished(days)
    context.progress(50)
    events = prune_events()
    db.session.commit()
    context.log(f"Deleted {jobs} jobs and {events} realtime events.")
    return {"jobs_deleted": jobs, "events_deleted": events}


@register_handler(
    "system.self_check", lane="system", title="Self-check", max_attempts=1, timeout_seconds=120, manual=True
)
def self_check(context: JobContext, payload: dict) -> dict:
    checks: dict[str, str] = {}

    context.log("Database: running a query.")
    db.session.execute(text("SELECT 1"))
    checks["database"] = "ok"
    context.progress(30)
    context.check_cancelled()

    context.log("Vault: writing, reading and deleting a test secret.")
    probe = "system.self_check.probe"
    put_secret(probe, "probe-value")
    ok = get_secret(probe) == "probe-value"
    delete_secret(probe)
    db.session.commit()
    checks["vault"] = "ok" if ok else "failed"
    context.progress(60)
    context.check_cancelled()

    data_dir = current_app.config["CAIRN_DATA_DIR"]
    free = shutil.disk_usage(data_dir).free
    checks["disk"] = "ok" if free >= MIN_FREE_BYTES else "low"
    context.log(f"Disk: {free / 1024**3:.1f} GiB free in the data directory.")
    context.progress(90)

    if "failed" in checks.values():
        raise RuntimeError(f"Self-check failed: {checks}")
    context.log("All checks passed." if set(checks.values()) == {"ok"} else f"Warnings: {checks}")
    return {"checks": checks, "free_gib": round(free / 1024**3, 1)}
