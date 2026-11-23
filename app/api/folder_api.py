"""A project's copies on the machine, and what Cairn can take from its folder (D-081)."""

from __future__ import annotations

import uuid

from flask import jsonify

from app.api import ApiError, api_blueprint, body
from app.core.schema.folder import BringInput, GitAction
from app.features.changesets.changesets_core import ChangesetError
from app.features.folder import copies_core, git_core, scan_core
from app.features.instances.instances_core import InstanceError
from app.features.projects import projects_core
from app.features.resources.resources_core import ResourceError

folder_api = api_blueprint("folder_api")


def _project(project_id: uuid.UUID):
    try:
        return projects_core.get_project(project_id)
    except projects_core.ProjectError as exc:
        raise ApiError(str(exc), 404) from exc


@folder_api.get("/projects/<uuid:project_id>/copies")
def copies(project_id: uuid.UUID):
    """Its folder, worktrees and clones: branch, changes, pull request, what runs in each."""
    return jsonify(copies_core.overview(_project(project_id)))


@folder_api.get("/projects/<uuid:project_id>/found")
def found(project_id: uuid.UUID):
    """To-do lists, issues, boards, skills and commands that are not in Cairn yet."""
    return jsonify(scan_core.scan(_project(project_id)))


@folder_api.post("/projects/<uuid:project_id>/bring")
def bring(project_id: uuid.UUID):
    """Take what is named by its keys; tasks come as a proposal."""
    try:
        taken = scan_core.bring(_project(project_id), body(BringInput).keys)
    except (scan_core.ScanError, ChangesetError, ResourceError, InstanceError) as exc:
        raise ApiError(str(exc), 409) from exc
    changeset = taken["changeset"]
    return jsonify({**taken, "changeset": str(changeset.id) if changeset else None}), 201


@folder_api.get("/projects/<uuid:project_id>/git")
def git_state(project_id: uuid.UUID):
    """Where each copy stands: branch, ahead and behind, changes, pull request."""
    return jsonify(git_core.state(_project(project_id)))


@folder_api.post("/projects/<uuid:project_id>/git/<any(fetch, pull):action>")
def git_action(project_id: uuid.UUID, action: str):
    """Fetch, or pull when it fast-forwards, one copy (`folder`) of the project."""
    data = body(GitAction)
    try:
        said = git_core.act(_project(project_id), data.folder, action)
    except git_core.GitError as exc:
        raise ApiError(str(exc), 409) from exc
    return jsonify(said=said)
