"""Comments API: thread per task or project, create, edit, retire a correction, delete; task brief."""

from __future__ import annotations

import uuid

from flask import jsonify

from app.api import ApiError, api_blueprint, body
from app.core.schema.comments import CommentCreate, CommentOut, CommentUpdate
from app.core.utils.history import batch
from app.features.comments import comments_core
from app.features.tasks import brief_core, tasks_core

comments_api = api_blueprint("comments_api")


def _comment(comment) -> dict:
    data = CommentOut.model_validate(comment).model_dump(mode="json")
    data["author"] = comments_core.author_label(comment.created_by)
    return data


def _guard(action, *args):
    try:
        with batch() as batch_id:
            result = action(*args)
    except comments_core.CommentNotFound as exc:
        raise ApiError(str(exc), 404) from exc
    except comments_core.CommentError as exc:
        raise ApiError(str(exc), 422) from exc
    return result, batch_id


@comments_api.get("/tasks/<uuid:target_id>/comments", defaults={"target_type": "task"})
@comments_api.get("/projects/<uuid:target_id>/comments", defaults={"target_type": "project"})
def thread(target_type: str, target_id: uuid.UUID):
    return jsonify(items=[_comment(c) for c in comments_core.for_target(target_type, target_id)])


@comments_api.post("/comments")
def create_comment():
    comment, batch_id = _guard(comments_core.create, body(CommentCreate))
    return jsonify(comment=_comment(comment), batch=str(batch_id)), 201


@comments_api.patch("/comments/<uuid:comment_id>")
def update_comment(comment_id: uuid.UUID):
    comment, batch_id = _guard(comments_core.update, comment_id, body(CommentUpdate))
    return jsonify(comment=_comment(comment), batch=str(batch_id))


@comments_api.delete("/comments/<uuid:comment_id>")
def delete_comment(comment_id: uuid.UUID):
    _, batch_id = _guard(comments_core.delete, comment_id)
    return jsonify(batch=str(batch_id))


@comments_api.get("/tasks/<uuid:task_id>/brief")
def task_brief(task_id: uuid.UUID):
    """The Markdown a Claude run on this task receives (instructions, corrections, resources…)."""
    try:
        task = tasks_core.get_task(task_id)
    except tasks_core.TaskNotFound as exc:
        raise ApiError(str(exc), 404) from exc
    return jsonify(task_id=str(task.id), markdown=brief_core.task_brief(task))
