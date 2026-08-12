"""Common utility functions for the application."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime.

    Use this for all application-level time handling.
    """
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """Return current UTC time as a naive datetime.

    Use this for SQLAlchemy ``Column`` defaults when the database column
    is ``TIMESTAMP WITHOUT TIME ZONE`` (the legacy default).  This avoids
    ``can't subtract offset-naive and offset-aware datetimes`` errors
    from asyncpg.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
