"""Timestamp helpers shared by persistence, audit, and API layers."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC, matching how timestamps are stored in the database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
