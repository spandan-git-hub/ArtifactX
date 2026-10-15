"""Configuration for timeline reconstruction and time normalization (Rule R10, R11)."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TimelineConfig:
    """Configurable thresholds for time quality assessment and clock anomaly detection."""
    # Jan 1, 2009 00:00:00 UTC in milliseconds (before WhatsApp / Telegram existed)
    pre_2009_floor_ms: int = 1_230_768_000_000

    # Tolerance past evidence ingest/acquisition timestamp before flagging FUTURE (5 minutes)
    future_tolerance_ms: int = 300_000

    # Within-chat backward timestamp jump threshold for NON_MONOTONIC_WITH_ROWID & CLOCK_ANOMALY (1 minute)
    backward_jump_threshold_ms: int = 60_000

    # Tolerance between EXIF camera clock and GPS UTC satellite clock before flagging CLOCK_ANOMALY (2 minutes)
    gps_exif_tolerance_ms: int = 120_000

    # Analyst-configured assumed timezone offset in minutes for naive EXIF timestamps
    # Default is None: strictly no assumption, utc_ms remains None, tz_basis="naive_unknown_tz"
    assumed_naive_offset_minutes: Optional[int] = None

    # Magnitude thresholds for UNIT_SUSPECT detection
    # If a source with declared unit 's' has value > 1e11, it looks like ms
    unit_suspect_s_ceiling: int = 100_000_000_000
    # If a source with declared unit 'ms' has value < 1e11 and > 1e8, it looks like seconds
    unit_suspect_ms_floor: int = 100_000_000
