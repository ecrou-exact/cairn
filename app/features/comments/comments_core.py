"""Comments and the corrections log on tasks and projects (PROJECT_BRIEF.md §2.2).

Soft delete like everything else; a deleted comment waits in the trash. A correction can
be retired (no longer given to Claude) without being deleted: the log keeps it.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from app.core.db_class.base import utcnow
from app.core.db_class.comment import Comment
from app.core.db_class.planning import Project, Task
from app.core.extensions import db
from app.core.schema.comments import CommentCreate, CommentUpdate
from app.core.utils.actor import current_actor
from app.core.utils.events import publish
from app.core.utils.history import batch, register_undo
from app.core.utils.logger import log_action

TARGETS = {"project": Project, "task": Task}


class CommentError(ValueError):
    pass


class CommentNotFound(CommentError):
    pass


def author_label(actor: str) -> str:
    """`user` → You, `claude:<run>` → Claude, `module:<id>` → Module <id>."""
    if actor == "user":
        return "You"
    kind, _, name = actor.partition(":")
    return {"claude": "Claude", "module": f"Module {name}"}.get(kind, actor)


def get_comment(comment_id: uuid.UUID, *, deleted: bool = False) -> Comment:
    comment = db.session.get(Comment, comment_id)
    if comment is None or comment.is_deleted != deleted:
        raise CommentNotFound(
            "This comment does not exist." if not deleted else "This comment is not in the trash."
        )
    return comment


def target_of(comment: Comment) -> Project | Task | None:
    return db.session.get(TARGETS[comment.target_type], comment.target_id)


def _changed(comment: Comment) -> None:
    publish(
        "comment.changed",
        {
            "id": str(comment.id),
            "kind": comment.kind,
            "targets": [f"{comment.target_type}:{comment.target_id}"],
        },
    )


def create(data: CommentCreate) -> Comment:
    target = db.session.get(TARGETS[data.target_type], data.target_id)
    if target is None or target.is_deleted:
        raise CommentError(f"This {data.target_type} does not exist.")
    with batch():
        comment = Comment(**data.model_dump(), created_by=current_actor())
        db.session.add(comment)
        db.session.flush()
        log_action(
            "comment.create",
            target_type="comment",
            target_id=comment.id,
            diff={"body_md": [None, comment.body_md], "kind": [None, comment.kind]},
            meta={"on": f"{comment.target_type}:{comment.target_id}"},
        )
        _changed(comment)
    return comment


def update(comment_id: uuid.UUID, data: CommentUpdate) -> Comment:
    comment = get_comment(comment_id)
    fields = data.model_dump(exclude_unset=True)
    fields = {key: value for key, value in fields.items() if value is not None}
    diff = {
        key: [getattr(comment, key), value] for key, value in fields.items() if getattr(comment, key) != value
    }
    if not diff:
        return comment
    with batch():
        for key in diff:
            setattr(comment, key, fields[key])
        if "body_md" in diff:
            comment.edited_at = utcnow()
        log_action("comment.update", target_type="comment", target_id=comment.id, diff=diff)
        _changed(comment)
    return comment


def delete(comment_id: uuid.UUID) -> Comment:
    comment = get_comment(comment_id)
    with batch():
        comment.deleted_at = utcnow()
        log_action(
            "comment.delete",
            target_type="comment",
            target_id=comment.id,
            diff={"deleted_at": [None, comment.deleted_at.isoformat()]},
        )
        _changed(comment)
    return comment


def restore(comment_id: uuid.UUID) -> Comment:
    comment = get_comment(comment_id, deleted=True)
    with batch():
        log_action(
            "comment.restore",
            target_type="comment",
            target_id=comment.id,
            diff={"deleted_at": [comment.deleted_at.isoformat(), None]},
        )
        comment.deleted_at = None
        _changed(comment)
    return comment


def purge(comment_id: uuid.UUID) -> None:
    comment = get_comment(comment_id, deleted=True)
    log_action(
        "comment.purge",
        target_type="comment",
        target_id=comment.id,
        meta={"kind": comment.kind, "on": f"{comment.target_type}:{comment.target_id}"},
        level="warning",
    )
    db.session.delete(comment)
    db.session.commit()


def forget_targets(target_type: str, target_ids: list[uuid.UUID]) -> None:
    """Comments on projects or tasks deleted for good go with them."""
    if target_ids:
        db.session.execute(
            sql_delete(Comment).where(Comment.target_type == target_type, Comment.target_id.in_(target_ids))
        )


# -- undo ------------------------------------------------------------------------------------


def _undo_create(row) -> None:
    comment = db.session.get(Comment, uuid.UUID(row.target_id))
    if comment is not None and not comment.is_deleted:
        delete(comment.id)


def _undo_update(row) -> None:
    update(uuid.UUID(row.target_id), CommentUpdate.model_validate({k: v[0] for k, v in row.diff.items()}))


def _undo_delete(row) -> None:
    comment = db.session.get(Comment, uuid.UUID(row.target_id))
    if comment is not None and comment.is_deleted:
        restore(comment.id)


def _undo_restore(row) -> None:
    comment = db.session.get(Comment, uuid.UUID(row.target_id))
    if comment is not None and not comment.is_deleted:
        delete(comment.id)


register_undo("comment.create", _undo_create)
register_undo("comment.update", _undo_update)
register_undo("comment.delete", _undo_delete)
register_undo("comment.restore", _undo_restore)


# -- reading ---------------------------------------------------------------------------------


def for_target(target_type: str, target_id: uuid.UUID, kind: str | None = None) -> list[Comment]:
    query = select(Comment).where(
        Comment.target_type == target_type, Comment.target_id == target_id, Comment.deleted_at.is_(None)
    )
    if kind:
        query = query.where(Comment.kind == kind)
    return list(db.session.scalars(query.order_by(Comment.created_at, Comment.id)))


def corrections_for_task(task: Task, chain: list[Task]) -> list[tuple[str, Comment]]:
    """Active corrections that apply to `task`: its project's, then its parent tasks' (outermost
    first, `chain` as from `tasks_core.ancestors`), then its own — as (where from, correction)."""
    sources: list[tuple[str, str, uuid.UUID]] = []
    if task.project is not None:
        sources.append((f"project {task.project.name}", "project", task.project.id))
    sources += [(f"parent task {parent.title}", "task", parent.id) for parent in chain]
    sources.append(("this task", "task", task.id))
    found = []
    for label, target_type, target_id in sources:
        found += [(label, c) for c in for_target(target_type, target_id, "correction") if c.active]
    return found


def deleted_comments() -> list[Comment]:
    return list(
        db.session.scalars(
            select(Comment).where(Comment.deleted_at.is_not(None)).order_by(Comment.deleted_at.desc())
        )
    )
