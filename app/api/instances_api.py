"""Instances API (D-053): a project's commands, started, stopped and restarted from Cairn."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.instances import FoundStop, InstanceCreate, InstanceStart, LogOpen
from app.features.claude import claude_core, terminal_core
from app.features.instances import found_core, instances_core
from app.features.projects import projects_core

instances_api = api_blueprint("instances_api")


def _guard(action, *args):
    try:
        return action(*args)
    except (instances_core.InstanceError, projects_core.ProjectError, terminal_core.TerminalError) as exc:
        raise ApiError(str(exc), 409) from exc


def _row(item: dict) -> dict:
    instance, live, last = item["instance"], item["running"], item["last"]
    return {
        "id": str(instance.id),
        "name": instance.name,
        "command": instance.command,
        "subfolder": instance.subfolder,
        "port": instance.port,
        "running": claude_core.describe(live) if live else None,
        "ports": item["ports"],
        "last_exit_code": last.exit_code if last and not live else None,
    }


@instances_api.get("/instances")
def list_instances():
    """`project`: the project's instances, each running or not, with its listening ports; and
    what runs for it outside Cairn (`outside`): other copies of its repository, containers."""
    try:
        project_id = uuid.UUID(request.args.get("project", ""))
    except ValueError as exc:
        raise ApiError("'project' must be an id.", 422) from exc
    project = _guard(projects_core.get_project, project_id)
    return jsonify(
        instances=[_row(item) for item in instances_core.for_project(project_id)],
        outside=found_core.for_project(project),
    )


@instances_api.post("/instances/outside/stop")
def stop_outside():
    """Stop an instance running outside Cairn."""
    data = body(FoundStop)
    _guard(found_core.stop, _guard(projects_core.get_project, data.project_id), data.id)
    return jsonify(ok=True)


@instances_api.post("/instances/log")
def open_log():
    """Follow the log of an instance running outside Cairn, in a terminal."""
    data = body(LogOpen)
    project = _guard(projects_core.get_project, data.project_id)
    session = _guard(found_core.open_log, project, data.key)
    return jsonify(session=claude_core.describe(session)), 201


@instances_api.post("/instances")
def create_instance():
    instance = _guard(instances_core.create, body(InstanceCreate))
    return jsonify(instance={"id": str(instance.id), "name": instance.name}), 201


@instances_api.delete("/instances/<uuid:instance_id>")
def delete_instance(instance_id: uuid.UUID):
    _guard(instances_core.delete, instance_id)
    return jsonify(ok=True)


@instances_api.post("/instances/<uuid:instance_id>/start")
def start_instance(instance_id: uuid.UUID):
    size = InstanceStart.model_validate(request.get_json(silent=True) or {})
    session = _guard(instances_core.start, instance_id, size.cols, size.rows)
    return jsonify(session=claude_core.describe(session)), 201


@instances_api.post("/instances/<uuid:instance_id>/stop")
def stop_instance(instance_id: uuid.UUID):
    _guard(instances_core.stop, instance_id)
    return jsonify(ok=True)


@instances_api.post("/instances/<uuid:instance_id>/restart")
def restart_instance(instance_id: uuid.UUID):
    session = _guard(instances_core.restart, instance_id)
    return jsonify(session=claude_core.describe(session)), 201
