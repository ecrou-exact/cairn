"""Jobs page: every background job, live, with cancel and retry."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.jobs import jobs_core
from app.core.jobs.registry import manual_types
from app.core.utils.events import latest_event_id

jobs = Blueprint("jobs", __name__)


# Live pages read the last event id *before* their data: the stream starts there, so a
# change made while the page renders is replayed rather than missed.


@jobs.get("/jobs")
def index():
    after = latest_event_id()
    page = jobs_core.list_jobs(request.args)
    return render_template("jobs/index.html", page=page, startable=manual_types(), events_after=after)


@jobs.get("/jobs/<uuid:job_id>")
def detail(job_id: uuid.UUID):
    after = latest_event_id()
    job = jobs_core.get_job(job_id)
    if job is None:
        abort(404)
    return render_template("jobs/detail.html", job=job, events_after=after)


@jobs.post("/jobs/start")
def start():
    try:
        job = jobs_core.enqueue_manual(request.form.get("type", ""))
    except jobs_core.JobError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("jobs.index"))
    flash(f"“{job.title}” is queued.", "success")
    return redirect(url_for("jobs.detail", job_id=job.id))


def _act(action, job_id: uuid.UUID, done):
    """Run a job action; `done(job)` gives the success message."""
    try:
        job = action(job_id)
    except jobs_core.JobNotFound:
        abort(404)
    except jobs_core.JobError as exc:
        flash(str(exc), "danger")
    else:
        flash(done(job), "success")
    return redirect(url_for("jobs.detail", job_id=job_id))


@jobs.post("/jobs/<uuid:job_id>/cancel")
def cancel(job_id: uuid.UUID):
    return _act(
        jobs_core.cancel,
        job_id,
        lambda job: (
            "Job cancelled." if job.is_finished else "Cancellation requested: the job stops at its next step."
        ),
    )


@jobs.post("/jobs/<uuid:job_id>/retry")
def retry(job_id: uuid.UUID):
    return _act(jobs_core.retry, job_id, lambda job: "The job is queued again.")
