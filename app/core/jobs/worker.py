"""The worker process: one thread pool per lane, heartbeats, crash recovery, daily schedules.

Runs in its own process (`python manage.py worker`), never inside the web server: a web
server recycles or times out its workers, which would kill long jobs (same reasoning as
Rulezet's worker.py). On SQLite only one worker may run (`WorkerLock`).
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path

import psutil
from flask import Flask

from app.core.db_class.base import utcnow
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.utils.settings import get_setting

_log = logging.getLogger("cairn.worker")
POLL_SECONDS = 1.0
HEARTBEAT_SECONDS = 30
DAILY = {"system.prune": timedelta(days=1)}
LOCK_NAME = "worker.lock"


class WorkerLockError(RuntimeError):
    pass


class WorkerLock:
    """One worker per SQLite database: SQLite has a single writer, two workers would only
    fight over it. The lock file holds the PID and start time of the running worker, so a
    stale file left by a crash is detected with psutil on every OS (no fcntl/msvcrt)."""

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / LOCK_NAME

    def _holder_alive(self) -> int | None:
        try:
            pid_text, started_text = self.path.read_text(encoding="utf-8").split()
            pid, started = int(pid_text), float(started_text)
        except (FileNotFoundError, ValueError):
            return None
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - started) < 1:
                return pid
        except psutil.Error:
            pass
        return None

    def acquire(self) -> None:
        holder = self._holder_alive()
        if holder is not None and holder != os.getpid():
            raise WorkerLockError(f"Another worker is already running (PID {holder}).")
        me = psutil.Process()
        self.path.write_text(f"{me.pid} {me.create_time()}", encoding="utf-8")

    def release(self) -> None:
        if self._holder_alive() == os.getpid():
            self.path.unlink(missing_ok=True)


class Worker:
    def __init__(self, app: Flask) -> None:
        self.app = app
        self.id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self.stop_event = threading.Event()
        self._running: dict[uuid.UUID, str] = {}
        self._lock = threading.Lock()

    # -- lanes ---------------------------------------------------------------------------------
    def _lane_loop(self, lane: str) -> None:
        with self.app.app_context():
            while not self.stop_event.is_set():
                try:
                    job = jobs_core.claim_next(lane, self.id)
                except Exception:
                    _log.exception("Could not claim a job on lane %s", lane)
                    db.session.rollback()
                    job = None
                if job is None:
                    self.stop_event.wait(POLL_SECONDS)
                    continue
                with self._lock:
                    self._running[job.id] = lane
                try:
                    _log.info("Running %s (%s) on lane %s", job.id, job.type, lane)
                    jobs_core.run(job)
                except Exception:
                    # Recording the outcome failed (database gone…): the job stays running and
                    # is requeued by recover_stale() once its heartbeats stop.
                    _log.exception("Could not record the outcome of job %s", job.id)
                    db.session.rollback()
                finally:
                    with self._lock:
                        self._running.pop(job.id, None)
                    db.session.remove()

    # -- housekeeping --------------------------------------------------------------------------
    def _housekeeping_loop(self) -> None:
        with self.app.app_context():
            last_beat = 0.0
            while not self.stop_event.is_set():
                try:
                    if time.monotonic() - last_beat >= HEARTBEAT_SECONDS:
                        with self._lock:
                            running = list(self._running)
                        jobs_core.heartbeat(running)
                        jobs_core.recover_stale()
                        self._schedule_daily()
                        last_beat = time.monotonic()
                except Exception:
                    _log.exception("Housekeeping failed")
                    db.session.rollback()
                self.stop_event.wait(5)

    def _schedule_daily(self) -> None:
        for job_type, every in DAILY.items():
            last = jobs_core.last_created(job_type)
            if last is None or utcnow() - last >= every:
                jobs_core.enqueue(job_type)

    # -- lifecycle -----------------------------------------------------------------------------
    def run_forever(self) -> None:
        lock = None
        if self.app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            lock = WorkerLock(self.app.config["CAIRN_DATA_DIR"])
            lock.acquire()
        try:
            self._run()
        finally:
            if lock is not None:
                lock.release()

    def _run(self) -> None:
        with self.app.app_context():
            lanes: dict[str, int] = get_setting("jobs.lanes")
            requeued = jobs_core.recover_stale()
        if requeued:
            _log.warning("Requeued %d jobs left running by a previous worker", requeued)
        threads = [threading.Thread(target=self._housekeeping_loop, name="housekeeping", daemon=True)]
        for lane, size in lanes.items():
            for index in range(max(1, int(size))):
                threads.append(
                    threading.Thread(
                        target=self._lane_loop, args=(lane,), name=f"{lane}-{index}", daemon=True
                    )
                )
        for thread in threads:
            thread.start()
        _log.info("Worker %s started: %s", self.id, ", ".join(f"{k} x{v}" for k, v in lanes.items()))
        try:
            while not self.stop_event.is_set():
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()
            for thread in threads:
                thread.join(timeout=10)
            _log.info("Worker %s stopped", self.id)
