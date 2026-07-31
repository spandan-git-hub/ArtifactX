"""Timestamp normalization for timeline events."""

from datetime import datetime, timezone


def normalize_timestamp(timestamp: int) -> datetime:
    """
    Normalize a Unix timestamp to a timezone-aware datetime object in UTC.

    Args:
        timestamp: Unix timestamp (seconds or milliseconds since epoch)

    Returns:
        Timezone-aware datetime object in UTC
    """
    if not timestamp:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    ts = float(timestamp)
    if ts > 1e11:  # Milliseconds timestamp (e.g. 13-digit WA timestamp)
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return datetime.fromtimestamp(0, tz=timezone.utc)