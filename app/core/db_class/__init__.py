"""Import every model module so SQLAlchemy and Alembic see all tables."""

from app.core.db_class import activity, job, owner, planning, resource, secret, setting  # noqa: F401
