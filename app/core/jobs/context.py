"""What a running handler can do: report progress, write its log, check for cancellation."""

from __future__ import annotations

import time
import uuid

from app.core.db_class.base import utcnow
from app.core.db_class.job import Job
from app.core.extensions import db
from app.core.utils.events import publish

MAX_LOG_CHARS = 200_000
LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")


class JobCancelled(Exception):
    """Raised by `check_cancelled()` when the owner cancelled the job: it ends as cancelled."""


class JobTimedOut(Exception):
    """Raised by `check_cancelled()` past the job's timeout: it fails (and may be retried)."""


def append_log(job: Job, text: str, level: str = "INFO") -> None:
    """Add a line (and any continuation lines, such as a traceback) to the job log.

    Lines read `HH:MM:SS LEVEL message`, a format the log viewer (vt-log) splits into
    time, level and message. Not committed: the caller commits with its own change.
    """
    if level not in LOG_LEVELS:
        raise ValueError(f"Unknown log level '{level}'.")
    entry = f"{utcnow():%H:%M:%S} {level} {text.rstrip()}\n"
    job.log = (job.log + entry)[-MAX_LOG_CHARS:]
    publish("job.log", {"id": str(job.id), "text": entry})


class JobContext:
    def __init__(self, job_id: uuid.UUID, timeout_seconds: int) -> None:
        self.job_id = job_id
        self._deadline = time.monotonic() + timeout_seconds

    def _job(self) -> Job:
        job = db.session.get(Job, self.job_id)
        db.session.refresh(job)
        return job

    def log(self, line: str, level: str = "INFO") -> None:
        job = self._job()
        append_log(job, line, level)
        job.heartbeat_at = utcnow()
        db.session.commit()

    def progress(self, percent: int) -> None:
        job = self._job()
        job.progress = max(0, min(100, int(percent)))
        job.heartbeat_at = utcnow()
        publish("job.progress", {"id": str(job.id), "progress": job.progress})
        db.session.commit()

    def check_cancelled(self) -> None:
        """Call between steps: stops the handler cleanly when asked to."""
        if time.monotonic() > self._deadline:
            raise JobTimedOut("the job ran past its time limit")
        if self._job().cancel_requested:
            raise JobCancelled("cancelled by the owner")
