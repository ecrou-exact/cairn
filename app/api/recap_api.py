"""The day summary, its time entries and the rules (D-078)."""

from __future__ import annotations

import uuid
from datetime import date

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.recap import (
    EntryInput,
    EntryUpdate,
    PeriodSendInput,
    RulesInput,
    SendInput,
    SummaryInput,
    TargetInput,
)
from app.features.recap import kimai, period_core, recap_core

recap_api = api_blueprint("recap_api")


def _guard(action, *args):
    try:
        return action(*args)
    except (recap_core.RecapError, kimai.KimaiError) as exc:
        raise ApiError(str(exc), 409) from exc


def _day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ApiError("Write the day as YYYY-MM-DD.", 422) from exc


@recap_api.get("/period/<first>/<last>")
def get_period(first: str, last: str):
    """A period: each day's facts, drafts and entries, the time by rule and the summary."""
    return jsonify(_guard(period_core.describe_period, _day(first), _day(last)))


@recap_api.post("/period/<first>/<last>/read")
def read_period(first: str, last: str):
    _guard(period_core.read_period, _day(first), _day(last))
    return jsonify(period_core.describe_period(_day(first), _day(last)))


@recap_api.post("/period/<first>/<last>/propose")
def propose_period(first: str, last: str):
    """Drafts for each working day with work and no entry; weekends and days off are left."""
    return jsonify(_guard(period_core.propose_period, _day(first), _day(last))), 201


@recap_api.post("/period/<first>/<last>/send")
def send_period(first: str, last: str):
    """Create in Kimai the period's drafts of the named rules."""
    sent = _guard(period_core.send_period, _day(first), _day(last), body(PeriodSendInput).rules)
    return jsonify(sent=sent)


@recap_api.get("/day/<raw>")
def get_day(raw: str):
    return jsonify(recap_core.describe_day(_day(raw)))


@recap_api.post("/day/<raw>/read")
def read_day(raw: str):
    """Read git, GitHub, the tasks and the Claude conversations of the day again."""
    _guard(recap_core.read_day, _day(raw))
    return jsonify(recap_core.describe_day(_day(raw)))


@recap_api.put("/day/<raw>/summary")
def save_summary(raw: str):
    _guard(recap_core.save_summary, _day(raw), body(SummaryInput).summary)
    return jsonify(recap_core.describe_day(_day(raw)))


@recap_api.post("/day/<raw>/propose")
def propose(raw: str):
    made = _guard(recap_core.propose, _day(raw))
    return jsonify(entries=[recap_core.describe_entry(e) for e in made]), 201


@recap_api.post("/day/<raw>/entries")
def add_entry(raw: str):
    made = _guard(recap_core.add_entry, _day(raw), body(EntryInput))
    return jsonify(entry=recap_core.describe_entry(made)), 201


@recap_api.patch("/day-entries/<uuid:entry_id>")
def update_entry(entry_id: uuid.UUID):
    return jsonify(
        entry=recap_core.describe_entry(_guard(recap_core.update_entry, entry_id, body(EntryUpdate)))
    )


@recap_api.delete("/day-entries/<uuid:entry_id>")
def delete_entry(entry_id: uuid.UUID):
    _guard(recap_core.delete_entry, entry_id)
    return "", 204


@recap_api.post("/day/<raw>/send")
def send(raw: str):
    """Create the named drafts in Kimai."""
    sent = _guard(recap_core.send, _day(raw), body(SendInput).entries)
    return jsonify(entries=[recap_core.describe_entry(e) for e in sent])


@recap_api.get("/time-rules")
def list_rules():
    return jsonify(
        rules=[recap_core.describe_target(t) for t in recap_core.targets(request.args.get("q", "")[:100])]
    )


@recap_api.post("/time-rules")
def add_rule():
    return jsonify(rule=recap_core.describe_target(_guard(recap_core.save_target, body(TargetInput)))), 201


@recap_api.put("/time-rules/<uuid:target_id>")
def update_rule(target_id: uuid.UUID):
    saved = _guard(recap_core.save_target, body(TargetInput), target_id)
    return jsonify(rule=recap_core.describe_target(saved))


@recap_api.delete("/time-rules/<uuid:target_id>")
def delete_rule(target_id: uuid.UUID):
    _guard(recap_core.delete_target, target_id)
    return "", 204


@recap_api.get("/time-rules/export")
def export_rules():
    return jsonify(recap_core.export_rules())


@recap_api.post("/time-rules/import")
def import_rules():
    saved = _guard(recap_core.import_rules, body(RulesInput))
    return jsonify(rules=[recap_core.describe_target(t) for t in saved]), 201


@recap_api.get("/time-catalog")
def catalog():
    """Kimai's projects and their activities."""
    return jsonify(projects=_guard(kimai.catalog))
