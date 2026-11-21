"""Change batches and undo (PROJECT_BRIEF.md §2.10).

Every activity row written inside `with batch():` shares one `batch_id`: one owner
action (an edit, a delete with its subtasks, a quick add) is one batch. Undo replays the
inverse of a batch, newest change first, through the same core functions, so undo is
validated and logged like any other change.

Each entity type registers how to invert its own actions with `register_undo`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.extensions import db

_current: ContextVar[uuid.UUID | None] = ContextVar("cairn_batch", default=None)
_undo: dict[str, Callable[[Activity], None]] = {}
UNDO_ACTION = "history.undo"


class UndoError(ValueError):
    pass


def current_batch() -> uuid.UUID | None:
    return _current.get()


@contextmanager
def batch() -> Iterator[uuid.UUID]:
    """Join the batch in progress, or start one.

    The outermost batch owns the transaction: it commits when its block ends and rolls
    everything back on an error, so one owner action (or one undo) is all or nothing.
    Code inside a batch never commits by itself.
    """
    existing = _current.get()
    if existing is not None:
        yield existing
        return
    token = _current.set(uuid.uuid4())
    try:
        yield _current.get()
        db.session.commit()
    except BaseException:
        db.session.rollback()
        raise
    finally:
        _current.reset(token)


def register_undo(action: str, inverse: Callable[[Activity], None]) -> None:
    """`inverse(activity)` undoes one activity row of `action` (e.g. `task.update`)."""
    if action in _undo:
        raise RuntimeError(f"Undo for '{action}' is registered twice.")
    _undo[action] = inverse


def _undone(batch_id: uuid.UUID) -> bool:
    return (
        db.session.scalar(
            select(Activity.id)
            .where(Activity.action == UNDO_ACTION, Activity.target_id == str(batch_id))
            .limit(1)
        )
        is not None
    )


def is_undoable(batch_id: uuid.UUID) -> bool:
    rows = _rows(batch_id)
    return bool(rows) and all(row.action in _undo for row in rows) and not _undone(batch_id)


def _rows(batch_id: uuid.UUID) -> list[Activity]:
    return list(
        db.session.scalars(
            select(Activity).where(Activity.batch_id == batch_id).order_by(Activity.created_at, Activity.id)
        )
    )


def undo(batch_id: uuid.UUID) -> uuid.UUID:
    """Undo a batch; returns the id of the batch made by the undo (itself undoable)."""
    from app.core.utils.logger import log_action  # logger imports this module

    rows = _rows(batch_id)
    if not rows:
        raise UndoError("Nothing to undo.")
    if _undone(batch_id):
        raise UndoError("This change was already undone.")
    if any(row.action not in _undo for row in rows):
        raise UndoError("This change cannot be undone.")
    with batch() as undo_batch:  # all or nothing: a half-undone change is worse than none
        for row in reversed(rows):
            _undo[row.action](row)
        log_action(UNDO_ACTION, target_type="batch", target_id=batch_id, meta={"changes": len(rows)})
    return undo_batch
