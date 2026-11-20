"""Data for the Today page."""

from __future__ import annotations

from sqlalchemy import select

from app.core.db_class.activity import Activity
from app.core.extensions import db


def recent_activity(limit: int = 15) -> list[Activity]:
    return list(db.session.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(limit)))
