"""Import every model module so SQLAlchemy and Alembic see all tables."""

from app.core.db_class import (  # noqa: F401
    activity,
    changeset,
    claude,
    comment,
    connection,
    job,
    owner,
    planning,
    resource,
    secret,
    setting,
)
