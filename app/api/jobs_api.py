"""Jobs API: list (same filters, search, sort and pages as the Jobs page), read, start, cancel, retry."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.jobs import jobs_core
from app.core.jobs.registry import manual_types
from app.core.schema.common import page_dict
from app.core.schema.jobs import JobDetail, JobStart, JobSummary

jobs_api = api_blueprint("jobs_api")


def _call(action, job_id: uuid.UUID):
    try:
        return action(job_id)
    except jobs_core.JobNotFound as exc:
        raise ApiError(str(exc), 404) from exc
    except jobs_core.JobError as exc:
        raise ApiError(str(exc), 409) from exc


@jobs_api.get("/jobs")
def list_jobs():
    page = jobs_core.list_jobs(request.args)
    items = [JobSummary.model_validate(job).model_dump(mode="json") for job in page.items]
    return jsonify(page_dict(page, items))


@jobs_api.get("/jobs/types")
def job_types():
    return jsonify([{"type": s.type, "title": s.title, "lane": s.lane} for s in manual_types()])


@jobs_api.get("/jobs/<uuid:job_id>")
def get_job(job_id: uuid.UUID):
    job = jobs_core.get_job(job_id)
    if job is None:
        raise ApiError("This job does not exist.", 404)
    return jsonify(JobDetail.model_validate(job).model_dump(mode="json"))


@jobs_api.post("/jobs")
def start_job():
    data = body(JobStart)
    try:
        job = jobs_core.enqueue_manual(data.type)
    except jobs_core.JobError as exc:
        raise ApiError(str(exc), 422) from exc
    return jsonify(JobDetail.model_validate(job).model_dump(mode="json")), 201


@jobs_api.post("/jobs/<uuid:job_id>/cancel")
def cancel_job(job_id: uuid.UUID):
    job = _call(jobs_core.cancel, job_id)
    return jsonify(JobDetail.model_validate(job).model_dump(mode="json"))


@jobs_api.post("/jobs/<uuid:job_id>/retry")
def retry_job(job_id: uuid.UUID):
    job = _call(jobs_core.retry, job_id)
    return jsonify(JobDetail.model_validate(job).model_dump(mode="json"))
