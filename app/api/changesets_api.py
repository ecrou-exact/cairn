"""Proposals of changes (D-071)."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.api import ApiError, api_blueprint, body
from app.core.schema.changesets import ChangesetApply
from app.core.schema.common import page_dict
from app.features.changesets import changesets_core

changesets_api = api_blueprint("changesets_api")


def _guard(action, *args):
    try:
        return action(*args)
    except changesets_core.ChangesetError as exc:
        raise ApiError(str(exc), 409) from exc


@changesets_api.get("/changesets")
def list_changesets():
    """Proposals, the newest first; `status`: proposed, applied, dismissed."""
    page = changesets_core.list_changesets(request.args)
    return jsonify(page_dict(page, [changesets_core.describe(c) for c in page.items]))


@changesets_api.get("/changesets/<uuid:changeset_id>")
def get_changeset(changeset_id: uuid.UUID):
    return jsonify(changeset=changesets_core.describe(_guard(changesets_core.get, changeset_id)))


@changesets_api.post("/changesets/<uuid:changeset_id>/apply")
def apply_changeset(changeset_id: uuid.UUID):
    """Apply the items kept (`keep`: their places), in one batch."""
    data = body(ChangesetApply)
    return jsonify(changeset=changesets_core.describe(_guard(changesets_core.apply, changeset_id, data.keep)))


@changesets_api.post("/changesets/<uuid:changeset_id>/dismiss")
def dismiss_changeset(changeset_id: uuid.UUID):
    return jsonify(changeset=changesets_core.describe(_guard(changesets_core.dismiss, changeset_id)))
