"""Resources API: library list, create, upload, update, delete, attach / detach, per target."""

from __future__ import annotations

import uuid

from flask import jsonify, request, url_for

from app.api import ApiError, api_blueprint, body
from app.core.schema.common import page_dict
from app.core.schema.resources import LinkCreate, LinkOut, ResourceCreate, ResourceOut, ResourceUpdate
from app.core.utils.history import batch
from app.features.resources import resources_core, storage_core
from app.features.resources.resources_forms import parse_link

resources_api = api_blueprint("resources_api")


def _resource(resource) -> dict:
    data = ResourceOut.model_validate(resource).model_dump(mode="json")
    data["url_page"] = url_for("resources.detail", resource_id=resource.id)
    if resource.has_file:
        data["url_file"] = url_for("resources.file", resource_id=resource.id)
    return data


def _guard(action, *args):
    try:
        with batch() as batch_id:
            result = action(*args)
    except resources_core.ResourceNotFound as exc:
        raise ApiError(str(exc), 404) from exc
    except (resources_core.ResourceError, storage_core.StorageError) as exc:
        raise ApiError(str(exc), 422) from exc
    return result, batch_id


@resources_api.get("/resources")
def list_resources():
    page = resources_core.list_resources(request.args)
    return jsonify(page_dict(page, [_resource(r) for r in page.items]))


@resources_api.post("/resources")
def create_resource():
    resource, batch_id = _guard(resources_core.create, body(ResourceCreate))
    return jsonify(resource=_resource(resource), batch=str(batch_id)), 201


@resources_api.post("/resources/upload")
def upload_resource():
    """multipart/form-data: `file`, and optionally `attach` (`task:<id>` or `project:<id>`)."""
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ApiError("Send the file in a multipart field named 'file'.", 400)
    raw_target = request.form.get("attach")
    target = parse_link(raw_target)
    if raw_target and target is None:
        raise ApiError("'attach' must be task:<id> or project:<id>.", 422)
    (resource, new), batch_id = _guard(resources_core.upload, file.stream, file.filename, target)
    return jsonify(resource=_resource(resource), new=new, batch=str(batch_id)), 201 if new else 200


@resources_api.get("/resources/<uuid:resource_id>")
def get_resource(resource_id: uuid.UUID):
    resource, _ = _guard(resources_core.get_resource, resource_id)
    data = _resource(resource)
    data["attached_to"] = [
        {"link_id": str(link.id), "target_type": link.target_type, "target_id": str(link.target_id)}
        for link, _target in resources_core.usages(resource.id)
    ]
    return jsonify(data)


@resources_api.patch("/resources/<uuid:resource_id>")
def update_resource(resource_id: uuid.UUID):
    resource, batch_id = _guard(resources_core.update, resource_id, body(ResourceUpdate))
    return jsonify(resource=_resource(resource), batch=str(batch_id))


@resources_api.delete("/resources/<uuid:resource_id>")
def delete_resource(resource_id: uuid.UUID):
    _, batch_id = _guard(resources_core.delete, resource_id)
    return jsonify(batch=str(batch_id))


@resources_api.post("/resources/<uuid:resource_id>/links")
def attach_resource(resource_id: uuid.UUID):
    link, batch_id = _guard(resources_core.attach, resource_id, body(LinkCreate))
    return jsonify(link=LinkOut.model_validate(link).model_dump(mode="json"), batch=str(batch_id)), 201


@resources_api.delete("/resource-links/<uuid:link_id>")
def detach_resource(link_id: uuid.UUID):
    _, batch_id = _guard(resources_core.detach, link_id)
    return jsonify(batch=str(batch_id))


@resources_api.get("/tasks/<uuid:target_id>/resources", defaults={"target_type": "task"})
@resources_api.get("/projects/<uuid:target_id>/resources", defaults={"target_type": "project"})
def resources_of(target_type: str, target_id: uuid.UUID):
    return jsonify(
        items=[
            {"link_id": str(link.id), "note": link.note, "resource": _resource(resource)}
            for link, resource in resources_core.for_target(target_type, target_id)
        ]
    )
