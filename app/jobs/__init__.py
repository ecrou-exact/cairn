"""Job handlers. Importing this package registers every handler."""

from app.jobs import connections, discover, planning, resources, system  # noqa: F401
