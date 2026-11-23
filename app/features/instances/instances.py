"""Instance actions from the project's Instances tab (forms; D-053)."""

from __future__ import annotations

import uuid

from flask import Blueprint, flash, redirect, request, url_for

from app.core.schema.instances import FoundStop, InstanceCreate, LogOpen
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, flash_undo, local_path, validate
from app.features.claude import terminal_core
from app.features.instances import found_core, instances_core
from app.features.projects import projects_core

instances = Blueprint("instances", __name__)


def _back() -> str:
    return local_path(request.form.get("next")) or url_for("projects.index")


@instances.post("/instances")
def create():
    values = {key: request.form.get(key, "") for key in ("project_id", "name", "command", "subfolder")}
    values["port"] = request.form.get("port") or None
    try:
        with batch() as batch_id:
            instance = instances_core.create(validate(InstanceCreate, values))
    except FormErrors as exc:
        flash(" ".join(exc.errors.values()), "danger")
        return redirect(_back())
    except instances_core.InstanceError as exc:
        flash(str(exc), "danger")
        return redirect(_back())
    flash_undo(f"Added the instance “{instance.name}”.", batch_id)
    return redirect(_back())


@instances.post("/instances/<uuid:instance_id>/<any(start, stop, restart, delete, autostart):action>")
def act(instance_id: uuid.UUID, action: str):
    try:
        if action == "delete":
            with batch() as batch_id:
                instances_core.delete(instance_id)
            flash_undo("Instance removed.", batch_id)
            return redirect(_back())
        if action == "autostart":
            with batch() as batch_id:
                found = instances_core.toggle_autostart(instance_id)
            flash_undo(
                f"“{found.name}” {'starts' if found.autostart else 'no longer starts'} with the machine.",
                batch_id,
            )
            return redirect(_back())
        if action == "stop":
            instances_core.stop(instance_id)
            return redirect(_back())
        session = (instances_core.restart if action == "restart" else instances_core.start)(instance_id)
    except (instances_core.InstanceError, terminal_core.TerminalError) as exc:
        flash(str(exc), "danger")
        return redirect(_back())
    return redirect(url_for("claude.session", session_id=session.id))


@instances.post("/instances/log")
def open_log():
    """Follow the log of an instance running outside Cairn, in a terminal (D-061)."""
    values = {key: request.form.get(key, "") for key in ("project_id", "key")}
    try:
        data = validate(LogOpen, values)
        session = found_core.open_log(projects_core.get_project(data.project_id), data.key)
    except FormErrors as exc:
        flash(" ".join(exc.errors.values()), "danger")
        return redirect(_back())
    except (instances_core.InstanceError, projects_core.ProjectError, terminal_core.TerminalError) as exc:
        flash(str(exc), "danger")
        return redirect(_back())
    return redirect(url_for("claude.session", session_id=session.id))


@instances.post("/instances/outside/stop")
def stop_outside():
    """Stop an instance running outside Cairn (D-070)."""
    values = {key: request.form.get(key, "") for key in ("project_id", "id")}
    try:
        data = validate(FoundStop, values)
        found_core.stop(projects_core.get_project(data.project_id), data.id)
    except FormErrors as exc:
        flash(" ".join(exc.errors.values()), "danger")
    except (instances_core.InstanceError, projects_core.ProjectError) as exc:
        flash(str(exc), "danger")
    return redirect(_back())
