import os
import uuid
from datetime import timedelta

import pytest

from app.core.db_class.activity import Activity
from app.core.db_class.base import utcnow
from app.core.db_class.job import Event, Job
from app.core.extensions import db
from app.core.jobs import jobs_core
from app.core.jobs.registry import register_handler
from app.core.jobs.worker import WorkerLock, WorkerLockError

CALLS: list[str] = []


@register_handler("test.ok", lane="io", title="Test ok")
def _ok(context, payload):
    context.log("working")
    context.progress(40)
    return {"echo": payload.get("x")}


@register_handler("test.boom", lane="io", title="Test boom", max_attempts=2)
def _boom(context, payload):
    raise RuntimeError("kaput")


@register_handler("test.cancellable", lane="io", title="Test cancel")
def _cancellable(context, payload):
    job = db.session.get(Job, context.job_id)
    job.cancel_requested = True  # what the owner's cancel does while the job runs
    db.session.commit()
    context.check_cancelled()
    CALLS.append("not reached")


@register_handler("test.manual", lane="system", title="Test manual", manual=True)
def _manual(context, payload):
    return None


def _run_next(lane="io"):
    job = jobs_core.claim_next(lane, "test-worker")
    assert job is not None
    jobs_core.run(job)
    db.session.refresh(job)
    return job


def test_job_runs_and_records_everything(ctx):
    queued = jobs_core.enqueue("test.ok", {"x": 7})
    assert queued.status == "queued"
    job = _run_next()
    assert (job.status, job.result, job.progress, job.attempts) == ("succeeded", {"echo": 7}, 100, 1)
    assert job.worker_id is None and job.finished_at is not None
    assert " INFO working" in job.log
    actions = [a.action for a in db.session.query(Activity).order_by(Activity.created_at)]
    assert actions == ["job.enqueue", "job.succeeded"]
    types = [e.type for e in db.session.query(Event).order_by(Event.id)]
    assert types[0] == "job.changed" and "job.log" in types and "job.progress" in types


def test_failure_retries_with_backoff_then_fails(ctx):
    jobs_core.enqueue("test.boom")
    job = _run_next()
    assert job.status == "queued" and job.error == "RuntimeError: kaput"
    assert job.run_after > utcnow() + timedelta(seconds=10)
    assert "ERROR RuntimeError: kaput" in job.log and "Traceback" in job.log
    assert jobs_core.claim_next("io", "w") is None  # not before its backoff
    job.run_after = utcnow()
    db.session.commit()
    job = _run_next()
    assert (job.status, job.attempts) == ("failed", 2)


def test_cancel_queued_and_running(ctx):
    queued = jobs_core.enqueue("test.ok")
    jobs_core.cancel(queued.id)
    assert queued.status == "cancelled"
    with pytest.raises(jobs_core.JobError):
        jobs_core.cancel(queued.id)

    jobs_core.enqueue("test.cancellable")
    job = _run_next()
    assert job.status == "cancelled" and "not reached" not in CALLS


def test_retry_resets_a_failed_job(ctx):
    job = jobs_core.enqueue("test.ok")
    jobs_core.cancel(job.id)
    jobs_core.retry(job.id)
    assert (job.status, job.attempts, job.error) == ("queued", 0, None)
    with pytest.raises(jobs_core.JobError):
        jobs_core.retry(job.id)
    with pytest.raises(jobs_core.JobNotFound):
        jobs_core.retry(uuid.uuid4())


def test_only_one_worker_wins_a_job(ctx):
    jobs_core.enqueue("test.ok")
    first = jobs_core.claim_next("io", "a")
    assert first is not None
    assert jobs_core.claim_next("io", "b") is None


def test_stale_running_job_is_requeued(ctx):
    jobs_core.enqueue("test.ok")
    job = jobs_core.claim_next("io", "dead-worker")
    job.heartbeat_at = utcnow() - timedelta(minutes=5)
    db.session.commit()
    assert jobs_core.recover_stale() == 1
    assert job.status == "queued" and "Worker lost" in job.log


def test_only_manual_types_can_be_started_by_hand(ctx):
    assert jobs_core.enqueue_manual("test.manual").type == "test.manual"
    with pytest.raises(jobs_core.JobError):
        jobs_core.enqueue_manual("test.ok")
    with pytest.raises(jobs_core.JobError):
        jobs_core.enqueue_manual("does.not_exist")


def test_prune_deletes_old_finished_jobs_only(ctx):
    old = jobs_core.enqueue("test.ok")
    jobs_core.cancel(old.id)
    old.finished_at = utcnow() - timedelta(days=40)
    running = jobs_core.enqueue("test.ok")
    db.session.commit()
    assert jobs_core.prune_finished(30) == 1
    db.session.commit()
    assert db.session.get(Job, running.id) is not None


def test_self_check_job(ctx):
    jobs_core.enqueue("system.self_check")
    job = _run_next("system")
    assert job.status == "succeeded"
    assert job.result["checks"]["database"] == "ok" and job.result["checks"]["vault"] == "ok"


def test_worker_lock_refuses_a_second_worker(tmp_path):
    lock = WorkerLock(tmp_path)
    lock.acquire()
    lock.acquire()  # the same process may take it again
    # A lock file naming a live process that is not us: refused.
    lock.path.write_text(f"{os.getppid()} 0", encoding="utf-8")  # wrong start time: stale
    lock.acquire()
    import psutil

    parent = psutil.Process(os.getppid())
    lock.path.write_text(f"{parent.pid} {parent.create_time()}", encoding="utf-8")
    with pytest.raises(WorkerLockError):
        lock.acquire()
    lock.path.unlink()
    lock.acquire()
    lock.release()
    assert not lock.path.exists()


# -- pages and API -------------------------------------------------------------------------


def test_jobs_pages(app, signed_in):
    with app.app_context():
        job_id = jobs_core.enqueue("test.ok", {"x": 1}).id
    page = signed_in.get("/jobs?q=Test&status=queued&sort=type&dir=asc&view=cards")
    assert page.status_code == 200 and b"Test ok" in page.data
    assert b'name="cn-events-after"' in page.data
    detail = signed_in.get(f"/jobs/{job_id}")
    assert detail.status_code == 200 and b"<cn-vitrine" in detail.data
    assert signed_in.get(f"/jobs/{uuid.uuid4()}").status_code == 404
    response = signed_in.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 302
    with app.app_context():
        assert jobs_core.get_job(job_id).status == "cancelled"


def test_start_from_the_page(app, signed_in):
    response = signed_in.post("/jobs/start", data={"type": "test.manual"})
    assert response.status_code == 302 and "/jobs/" in response.location
    refused = signed_in.post("/jobs/start", data={"type": "test.ok"}, follow_redirects=True)
    assert b"cannot be started by hand" in refused.data


def test_jobs_api(app, signed_in):
    created = signed_in.post("/api/jobs", json={"type": "test.manual"})
    assert created.status_code == 201
    job_id = created.json["id"]
    assert signed_in.post("/api/jobs", json={"type": "test.ok"}).status_code == 422
    assert signed_in.post("/api/jobs", json={"type": "x", "extra": 1}).status_code == 422
    listing = signed_in.get("/api/jobs?status=queued")
    assert listing.json["total"] == 1 and listing.json["items"][0]["id"] == job_id
    assert signed_in.get(f"/api/jobs/{job_id}").json["log"] == ""
    assert signed_in.post(f"/api/jobs/{job_id}/cancel").json["status"] == "cancelled"
    assert signed_in.post(f"/api/jobs/{job_id}/cancel").status_code == 409
    assert signed_in.post(f"/api/jobs/{uuid.uuid4()}/retry").status_code == 404
    assert [t["type"] for t in signed_in.get("/api/jobs/types").json] == [
        "system.prune",
        "system.self_check",
        "test.manual",
    ]


def test_api_requires_the_owner(client, owner):
    assert client.get("/api/jobs").status_code == 401
