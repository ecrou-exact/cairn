"""The day summary, its time entries and the rules that place the work (D-078)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for

from app.core.schema.recap import EntryInput, EntryUpdate, RulesInput, SendInput, SummaryInput, TargetInput
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, split_list, validate
from app.features.recap import kimai, recap_core

recap = Blueprint("recap", __name__)
PROBLEMS = (FormErrors, recap_core.RecapError, kimai.KimaiError)


def _day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        abort(404)


def _back(day: str):
    return redirect(url_for("recap.day", raw=day))


@recap.get("/day")
def index():
    chosen = request.args.get("on", "")
    return _back(_day(chosen).isoformat() if chosen else date.today().isoformat())


@recap.get("/day/<raw>")
def day(raw: str):
    chosen = _day(raw)
    there, problem = [], ""
    if kimai.configured():
        try:
            there = kimai.entries(chosen)
        except kimai.KimaiError as exc:
            problem = str(exc)
    found = recap_core.describe_day(chosen)
    sent = {e["kimai_id"] for e in found["entries"] if e["sent"]}
    today = date.today()
    return render_template(
        "recap/day.html",
        day=chosen,
        today=today,
        before=chosen - timedelta(days=1),
        after=chosen + timedelta(days=1) if chosen < today else None,
        found=found,
        read_at=datetime.fromisoformat(found["read_at"]).astimezone() if found["read_at"] else None,
        there=[row for row in there if row["id"] not in sent],
        problem=problem,
        kimai_ready=kimai.configured(),
        kimai_url=kimai.address() if kimai.configured() else "",
        targets=recap_core.targets(),
        kinds=recap_core.KINDS,
    )


def _act(raw: str, action, message: str):
    try:
        action()
    except PROBLEMS as exc:
        flash(str(exc), "danger")
    else:
        flash(message, "success")
    return _back(raw)


@recap.post("/day/<raw>/read")
def read(raw: str):
    chosen = _day(raw)
    return _act(raw, lambda: recap_core.read_day(chosen), "The day was read.")


@recap.post("/day/<raw>/summary")
def summary(raw: str):
    chosen = _day(raw)
    return _act(
        raw,
        lambda: recap_core.save_summary(
            chosen, validate(SummaryInput, {"summary": request.form.get("summary", "")}).summary
        ),
        "Summary saved.",
    )


@recap.post("/day/<raw>/propose")
def propose(raw: str):
    chosen = _day(raw)
    return _act(raw, lambda: recap_core.propose(chosen), "Time entries proposed: check them before you send.")


def _entry_form() -> dict[str, str]:
    hours, _, minutes = request.form.get("duration", "").partition(":")
    try:
        total = int(hours) * 60 + int(minutes or 0)
    except ValueError as exc:
        raise FormErrors({"duration": "Write the duration as hours:minutes."}) from exc
    values = {name: request.form.get(name, "") for name in ("target_id", "begin", "description")}
    return {**values, "minutes": total}


@recap.post("/day/<raw>/entries")
def add_entry(raw: str):
    chosen = _day(raw)
    return _act(
        raw, lambda: recap_core.add_entry(chosen, validate(EntryInput, _entry_form())), "Entry added."
    )


@recap.post("/day/<raw>/entries/<uuid:entry_id>")
def update_entry(raw: str, entry_id: uuid.UUID):
    return _act(
        raw, lambda: recap_core.update_entry(entry_id, validate(EntryUpdate, _entry_form())), "Entry saved."
    )


@recap.post("/day/<raw>/entries/<uuid:entry_id>/delete")
def delete_entry(raw: str, entry_id: uuid.UUID):
    try:
        with batch() as batch_id:
            recap_core.delete_entry(entry_id)
    except recap_core.RecapError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Entry removed.", batch_id)
    return _back(raw)


@recap.post("/day/<raw>/send")
def send(raw: str):
    chosen = _day(raw)
    return _act(
        raw,
        lambda: recap_core.send(
            chosen, validate(SendInput, {"entries": request.form.getlist("entries")}).entries
        ),
        "Sent to Kimai.",
    )


# -- the rules -------------------------------------------------------------------------------------


def _rule_form() -> TargetInput:
    form = request.form
    project, _, activity = form.get("place", "").partition(":")
    return validate(
        TargetInput,
        {
            "label": form.get("label", ""),
            "repos": split_list(form.get("repos")),
            "keywords": split_list(form.get("keywords")),
            "tags": split_list(form.get("tags")),
            "guidance": form.get("guidance", ""),
            "about": form.get("about", ""),
            "is_default": form.get("is_default") == "1",
            "kimai_project": project or 0,
            "kimai_activity": activity or 0,
        },
    )


@recap.get("/day/rules")
def rules():
    q = request.args.get("q", "")[:100]
    edited, problem, places = None, "", []
    try:
        places = kimai.catalog()
    except kimai.KimaiError as exc:
        problem = str(exc)
    if raw := request.args.get("edit"):
        try:
            edited = recap_core.get_target(uuid.UUID(raw))
        except ValueError:
            abort(404)
    return render_template(
        "recap/rules.html",
        rules=recap_core.targets(q),
        q=q,
        edited=edited,
        places=places,
        problem=problem,
        repo=request.args.get("repo", "")[:100],
    )


def _rule(action, message: str):
    try:
        action()
    except PROBLEMS as exc:
        flash(str(exc), "danger")
    else:
        flash(message, "success")
    return redirect(url_for("recap.rules"))


@recap.post("/day/rules")
def add_rule():
    return _rule(lambda: recap_core.save_target(_rule_form()), "Rule added.")


@recap.post("/day/rules/<uuid:target_id>")
def update_rule(target_id: uuid.UUID):
    return _rule(lambda: recap_core.save_target(_rule_form(), target_id), "Rule saved.")


@recap.post("/day/rules/<uuid:target_id>/delete")
def delete_rule(target_id: uuid.UUID):
    try:
        with batch() as batch_id:
            recap_core.delete_target(target_id)
    except recap_core.RecapError as exc:
        flash(str(exc), "danger")
    else:
        flash_undo("Rule removed.", batch_id)
    return redirect(url_for("recap.rules"))


@recap.get("/day/rules/export")
def export_rules():
    return Response(
        json.dumps(recap_core.export_rules(), indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=cairn-time-rules.json"},
    )


@recap.post("/day/rules/import")
def import_rules():
    def work():
        sent = request.files.get("file")
        try:
            data = json.loads(sent.read(1_000_000)) if sent else None
        except ValueError as exc:
            raise FormErrors({"file": "This file is not a rules file."}) from exc
        if not isinstance(data, dict):
            raise FormErrors({"file": "Choose a rules file."})
        recap_core.import_rules(validate(RulesInput, data))

    return _rule(work, "Rules imported.")
