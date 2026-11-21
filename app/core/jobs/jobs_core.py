"""Job lifecycle: enqueue, claim, run, retry with backoff, cancel, recover after a crash.

Claiming is a conditional UPDATE (`... WHERE id = ? AND status = 'queued'`): only one
worker can win a job, on SQLite and PostgreSQL alike.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, select, update

from app.core.db_class.base import utcnow
from app.core.db_class.job import FINISHED_STATUSES, JOB_STATUSES, Job
from app.core.extensions import db
from app.core.jobs.context import JobCancelled, JobContext, append_log
from app.core.jobs.registry import get_handler, handler_types
from app.core.utils.actor import acting_as
from app.core.utils.events import publish
from app.core.utils.listing import FilterSpec, ListPage, ListSpec, run_list
from app.core.utils.logger import log_action

_log = logging.getLogger("cairn.jobs")
BACKOFF_BASE_SECONDS = 15
STALE_AFTER = timedelta(minutes=2)


class JobError(ValueError):
    pass


class JobNotFound(JobError):
    pass


def _announce(job: Job) -> None:
    publish(
        "job.changed",
        {
            "id": str(job.id),
            "status": job.status,
            "progress": job.progress,
            "attempts": job.attempts,
            "error": job.error,
        },
    )


# -- reading ---------------------------------------------------------------------------------


def list_spec() -> ListSpec:
    lanes = sorted({spec.lane for spec in handler_types()})
    return ListSpec(
        sortable={
            "created": Job.created_at,
            "status": Job.status,
            "type": Job.type,
            "lane": Job.lane,
            "finished": Job.finished_at,
        },
        default_sort="created",
        tiebreak=Job.id,
        searchable=(Job.title, Job.type, Job.error),
        filters=(
            FilterSpec("status", "Status", Job.status, tuple((s, s.capitalize()) for s in JOB_STATUSES)),
            FilterSpec("lane", "Lane", Job.lane, tuple((lane, lane.capitalize()) for lane in lanes)),
        ),
    )


def list_jobs(args: Mapping[str, Any]) -> ListPage:
    return run_list(list_spec(), select(Job), args)


def get_job(job_id: uuid.UUID) -> Job | None:
    return db.session.get(Job, job_id)


def _require(job_id: uuid.UUID) -> Job:
    job = get_job(job_id)
    if job is None:
        raise JobNotFound("This job does not exist.")
    return job


# -- writing ---------------------------------------------------------------------------------


def enqueue(job_type: str, payload: dict[str, Any] | None = None, *, title: str | None = None) -> Job:
    spec = get_handler(job_type)
    job = Job(
        type=job_type,
        lane=spec.lane,
        title=title or spec.title,
        payload=payload or {},
        max_attempts=spec.max_attempts,
        timeout_seconds=spec.timeout_seconds,
    )
    db.session.add(job)
    db.session.flush()
    log_action("job.enqueue", target_type="job", target_id=job.id, meta={"type": job_type})
    _announce(job)
    db.session.commit()
    return job


def enqueue_manual(job_type: str) -> Job:
    """What the owner may start by hand (Jobs page, API): only handlers marked `manual`."""
    try:
        spec = get_handler(job_type)
    except KeyError as exc:
        raise JobError("This job type does not exist.") from exc
    if not spec.manual:
        raise JobError("This job type cannot be started by hand.")
    return enqueue(job_type)


def claim_next(lane: str, worker_id: str) -> Job | None:
    now = utcnow()
    candidates = db.session.scalars(
        select(Job.id)
        .where(Job.lane == lane, Job.status == "queued", Job.run_after <= now)
        .order_by(Job.run_after, Job.created_at)
        .limit(5)
    ).all()
    for job_id in candidates:
        won = db.session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "queued")
            .values(
                status="running",
                started_at=now,
                heartbeat_at=now,
                worker_id=worker_id,
                attempts=Job.attempts + 1,
            )
        ).rowcount
        if won:
            job = db.session.get(Job, job_id)
            db.session.refresh(job)
            _announce(job)
            db.session.commit()
            return job
        db.session.rollback()
    return None


def run(job: Job) -> None:
    """Execute a claimed job and record its outcome."""
    spec = get_handler(job.type)
    context = JobContext(job.id, job.timeout_seconds)
    try:
        with acting_as("system"):
            result = spec.func(context, dict(job.payload))
    except JobCancelled as stop:
        db.session.rollback()
        _finish(job, "cancelled", error=str(stop))
    except Exception as exc:
        db.session.rollback()
        _log.exception("Job %s (%s) failed", job.id, job.type)
        _fail(job, f"{type(exc).__name__}: {exc}", traceback.format_exc(limit=8))
    else:
        _finish(job, "succeeded", result=result or {})


def _finish(job: Job, status: str, *, result: dict | None = None, error: str | None = None) -> None:
    db.session.refresh(job)
    job.status, job.result, job.error = status, result, error
    job.finished_at, job.worker_id = utcnow(), None
    if status == "succeeded":
        job.progress = 100
    log_action(
        f"job.{status}",
        target_type="job",
        target_id=job.id,
        meta={"type": job.type},
        level="info" if status == "succeeded" else "warning",
    )
    _announce(job)
    db.session.commit()


def _fail(job: Job, message: str, trace: str) -> None:
    db.session.refresh(job)
    append_log(job, f"{message}\n{trace}", "ERROR")
    if job.attempts < job.max_attempts and not job.cancel_requested:
        delay = BACKOFF_BASE_SECONDS * 2 ** (job.attempts - 1)
        job.status, job.error, job.worker_id = "queued", message, None
        job.run_after = utcnow() + timedelta(seconds=delay)
        append_log(job, f"Retrying in {delay} s (attempt {job.attempts + 1} of {job.max_attempts}).", "WARN")
        _announce(job)
        db.session.commit()
        return
    _finish(job, "failed", error=message)


def cancel(job_id: uuid.UUID) -> Job:
    job = _require(job_id)
    if job.is_finished:
        raise JobError("This job has already finished.")
    if job.cancel_requested:
        raise JobError("Cancellation was already requested.")
    if job.status == "queued":
        job.status, job.finished_at, job.error = "cancelled", utcnow(), "cancelled by the owner"
        append_log(job, "Cancelled by the owner before it started.", "WARN")
    else:
        job.cancel_requested = True  # the handler stops at its next check_cancelled()
        append_log(job, "Cancellation requested.", "WARN")
    log_action("job.cancel", target_type="job", target_id=job.id, meta={"type": job.type})
    _announce(job)
    db.session.commit()
    return job


def retry(job_id: uuid.UUID) -> Job:
    job = _require(job_id)
    if job.status not in ("failed", "cancelled"):
        raise JobError("Only failed or cancelled jobs can be retried.")
    job.status, job.error, job.result, job.progress = "queued", None, None, 0
    job.attempts, job.cancel_requested, job.finished_at = 0, False, None
    job.run_after = utcnow()
    append_log(job, "Retried by the owner.")
    log_action("job.retry", target_type="job", target_id=job.id, meta={"type": job.type})
    _announce(job)
    db.session.commit()
    return job


# -- worker housekeeping ---------------------------------------------------------------------


def recover_stale() -> int:
    """Requeue running jobs whose worker stopped sending heartbeats (crash, kill, reboot)."""
    limit = utcnow() - STALE_AFTER
    stale = db.session.scalars(select(Job).where(Job.status == "running", Job.heartbeat_at < limit)).all()
    for job in stale:
        job.status, job.worker_id = "queued", None
        append_log(job, "Worker lost; job requeued.", "WARN")
        _announce(job)
    db.session.commit()
    return len(stale)


def heartbeat(job_ids: list[uuid.UUID]) -> None:
    if job_ids:
        db.session.execute(
            update(Job).where(Job.id.in_(job_ids), Job.status == "running").values(heartbeat_at=utcnow())
        )
        db.session.commit()


def last_created(job_type: str):
    return db.session.scalar(
        select(Job.created_at).where(Job.type == job_type).order_by(Job.created_at.desc()).limit(1)
    )


def prune_finished(older_than_days: int) -> int:
    limit = utcnow() - timedelta(days=older_than_days)
    result = db.session.execute(delete(Job).where(Job.status.in_(FINISHED_STATUSES), Job.finished_at < limit))
    return result.rowcount or 0
