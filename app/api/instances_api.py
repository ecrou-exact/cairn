"""Instances API (D-053): a project's commands, started, stopped and restarted from Cairn."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.instances import InstanceCreate, InstanceStart
from app.features.claude import claude_core, terminal_core
from app.features.instances import instances_core

instances_api = api_blueprint("instances_api")


def _guard(action, *args):
    try:
        return action(*args)
    except (instances_core.InstanceError, terminal_core.TerminalError) as exc:
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
    """`project`: the project's instances, each running or not, with its listening ports."""
    try:
        project_id = uuid.UUID(request.args.get("project", ""))
    except ValueError as exc:
        raise ApiError("'project' must be an id.", 422) from exc
    return jsonify(instances=[_row(item) for item in instances_core.for_project(project_id)])


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
