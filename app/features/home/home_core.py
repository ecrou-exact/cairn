"""Data for the Today page: next actions, what needs attention, the running timer, activity."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.extensions import db
from app.features.tasks import tasks_core, timer_core


def recent_activity(limit: int = 15) -> list[Activity]:
    return list(db.session.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(limit)))


def greeting(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    return "Good morning" if 5 <= hour < 12 else "Good afternoon" if hour < 18 else "Good evening"


def today() -> dict[str, Any]:
    return {
        "next_actions": tasks_core.next_actions(),
        "attention": tasks_core.needs_attention(),
        "timer": timer_core.running(),
        "counts": tasks_core.counts_by_state(),
        "pulse": tasks_core.pulse(),
        "greeting": greeting(),
        "activity": recent_activity(),
    }
