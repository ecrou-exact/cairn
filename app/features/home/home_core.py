"""Data for the Today page: next actions, what needs attention, the running timer, activity."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.features.tasks import tasks_core, timer_core


def recent_activity(limit: int = 15) -> list[Activity]:
    return list(db.session.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(limit)))


def today() -> dict[str, Any]:
    return {
        "next_actions": tasks_core.next_actions(),
        "attention": tasks_core.needs_attention(),
        "timer": timer_core.running(),
        "counts": tasks_core.counts_by_state(),
        "activity": recent_activity(),
    }
