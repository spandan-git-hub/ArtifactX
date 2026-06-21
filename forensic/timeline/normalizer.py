"""Timestamp normalization for timeline events."""

from datetime import datetime, timezone


def normalize_timestamp(timestamp: int) -> datetime:
    """
    Normalize a Unix timestamp to a timezone-aware datetime object in UTC.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        Timezone-aware datetime object in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)