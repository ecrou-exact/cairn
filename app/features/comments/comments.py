"""Comment and correction actions, posted from the task and project pages."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.db_class.comment import COMMENT_TARGETS
from app.core.schema.comments import CommentCreate, CommentUpdate
from app.core.utils.history import batch
from app.core.utils.web import FormErrors, back_to, flash_undo, parse_target, validate
from app.features.comments import comments_core

comments = Blueprint("comments", __name__)


def _page_of(target_type: str, target) -> str:
    if target is None:
        return url_for("home.index")
    if target_type == "project":
        return url_for("projects.detail", slug=target.slug, _anchor="comments")
    return url_for("tasks.detail", task_id=target.id, _anchor="comments")


def _comment_or_404(comment_id: uuid.UUID):
    try:
        return comments_core.get_comment(comment_id)
    except comments_core.CommentNotFound:
        abort(404)


def _back_to_thread(comment) -> str:
    return back_to(_page_of(comment.target_type, comments_core.target_of(comment)))


@comments.post("/comments")
def create():
    target = parse_target(request.form.get("target"), COMMENT_TARGETS)
    if target is None:
        abort(400)
    kind = "correction" if request.form.get("kind") == "correction" else "comment"
    values = {
        "target_type": target[0],
        "target_id": target[1],
        "kind": kind,
        "body_md": request.form.get("body_md", ""),
    }
    try:
        with batch() as batch_id:
            comment = comments_core.create(validate(CommentCreate, values))
    except FormErrors:
        flash("Write something first.", "warning")
        return redirect(back_to(url_for("home.index")))
    except comments_core.CommentError as exc:
        flash(str(exc), "danger")
        return redirect(back_to(url_for("home.index")))
    flash_undo(
        "Correction kept: Claude gets it on every later run." if kind == "correction" else "Comment added.",
        batch_id,
    )
    return redirect(_back_to_thread(comment))


@comments.get("/comments/<uuid:comment_id>/edit")
def edit(comment_id: uuid.UUID):
    comment = _comment_or_404(comment_id)
    target = comments_core.target_of(comment)
    return render_template(
        "comments/edit.html",
        comment=comment,
        target=target,
        back=_page_of(comment.target_type, target),
        values={"body_md": comment.body_md, "kind": comment.kind},
        errors={},
    )


@comments.post("/comments/<uuid:comment_id>/edit")
def save(comment_id: uuid.UUID):
    comment = _comment_or_404(comment_id)
    target = comments_core.target_of(comment)
    kind = "correction" if request.form.get("kind") in ("correction", "on") else "comment"
    try:
        with batch() as batch_id:
            comments_core.update(
                comment.id,
                validate(CommentUpdate, {"body_md": request.form.get("body_md", ""), "kind": kind}),
            )
    except FormErrors as exc:
        return (
            render_template(
                "comments/edit.html",
                comment=comment,
                target=target,
                back=_page_of(comment.target_type, target),
                values={"body_md": request.form.get("body_md", ""), "kind": kind},
                errors=exc.errors,
            ),
            422,
        )
    flash_undo("Saved.", batch_id)
    return redirect(_page_of(comment.target_type, target))


@comments.post("/comments/<uuid:comment_id>/active")
def set_active(comment_id: uuid.UUID):
    comment = _comment_or_404(comment_id)
    active = request.form.get("active") == "1"
    with batch() as batch_id:
        comments_core.update(comment.id, CommentUpdate(active=active))
    flash_undo(
        "Claude gets this correction again." if active else "Retired: Claude no longer gets it.", batch_id
    )
    return redirect(_back_to_thread(comment))


@comments.post("/comments/<uuid:comment_id>/delete")
def delete(comment_id: uuid.UUID):
    comment = _comment_or_404(comment_id)
    with batch() as batch_id:
        comments_core.delete(comment.id)
    flash_undo("Moved to the trash.", batch_id)
    return redirect(_back_to_thread(comment))
