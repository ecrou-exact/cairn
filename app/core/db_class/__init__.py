"""Import every model module so SQLAlchemy and Alembic see all tables."""

from app.core.db_class import activity, comment, job, owner, planning, resource, secret, setting  # noqa: F401
