"""Deterministic timestamp normalization and quality flag assessment (Rule R10, R11)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Set, Tuple

from forensic.timeline.config import TimelineConfig
from forensic.timeline.models import TimeUnit, TimeValue, TzBasis


def _parse_numeric(val: Any) -> Optional[int]:
    """Safely convert int, float, or numeric string to int."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return None


def parse_offset_minutes(offset_str: Optional[str]) -> Optional[int]:
    """Parse '[+-]HH:MM' or '[+-]HHMM' into signed total minutes."""
    if not offset_str:
        return None
    s = offset_str.strip()
    m = re.match(r"^([+-])(\d{1,2}):?(\d{2})$", s)
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    hours = int(m.group(2))
    mins = int(m.group(3))
    return sign * (hours * 60 + mins)


def parse_exif_datetime_str(dt_str: str) -> Optional[datetime]:
    """Parse standard EXIF 'YYYY:MM:DD HH:MM:SS' into a naive datetime."""
    s = dt_str.strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_gps_timestamp_to_utc_ms(date_stamp: str, time_stamp: Any) -> Optional[int]:
    """
    Parse GPSDateStamp ('YYYY:MM:DD') and GPSTimeStamp ((h, m, s) tuple of rationals/ints)
    into UTC milliseconds. GPS time is strictly UTC.
    """
    if not date_stamp or not time_stamp:
        return None
    d_str = str(date_stamp).strip().replace("-", ":").replace("/", ":")
    try:
        parts = d_str.split(":")
        if len(parts) != 3:
            return None
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        # time_stamp is typically a tuple of 3 (hours, minutes, seconds)
        if hasattr(time_stamp, "__len__") and len(time_stamp) == 3:
            h = float(time_stamp[0])
            m = float(time_stamp[1])
            s = float(time_stamp[2])
        else:
            return None

        # Build UTC datetime
        dt = datetime(year, month, day, int(h), int(m), int(s), tzinfo=timezone.utc)
        subsecond_ms = int(round((s - int(s)) * 1000))
        return int(dt.timestamp() * 1000) + subsecond_ms
    except Exception:
        return None


def normalize_time_value(
    raw: int | str | None,
    unit: TimeUnit,
    evidence_ingest_time_ms: Optional[int] = None,
    config: Optional[TimelineConfig] = None,
    offset_str: Optional[str] = None,
    gps_time_tuple: Optional[Any] = None,
) -> TimeValue:
    """
    Normalize raw timestamp to TimeValue per spec B11.1 (Rules R10, R11).
    
    Evaluates quality flags:
    - ZERO: raw == 0 or '0'
    - NEGATIVE: numeric raw < 0
    - PRE_2009: utc_ms < Jan 1, 2009
    - FUTURE: utc_ms > evidence_ingest_time_ms + tolerance (deterministic, never wall-clock)
    - UNIT_SUSPECT: value magnitude suggests different unit; flagged without silent conversion
    - NAIVE_LOCAL: naive EXIF where analyst-configured assumed offset was applied
    """
    if config is None:
        config = TimelineConfig()

    flags: Set[str] = set()
    raw_str = "" if raw is None else str(raw).strip()

    # Check for ZERO and NEGATIVE
    num_val = _parse_numeric(raw)
    if num_val is not None:
        if num_val == 0:
            flags.add("ZERO")
        elif num_val < 0:
            flags.add("NEGATIVE")
    elif raw_str == "0":
        flags.add("ZERO")

    utc_ms: Optional[int] = None
    tz_basis: TzBasis = "utc_source"

    # Evaluate per unit
    if unit == "s":
        tz_basis = "utc_source"
        if num_val is not None:
            if num_val > config.unit_suspect_s_ceiling:
                # Value > 1e11 in a seconds field looks like milliseconds; flag, don't silently convert (R10)
                flags.add("UNIT_SUSPECT")
            utc_ms = num_val * 1000
        else:
            tz_basis = "not_applicable"

    elif unit == "ms":
        tz_basis = "utc_source"
        if num_val is not None:
            if 0 < num_val < config.unit_suspect_s_ceiling and num_val > config.unit_suspect_ms_floor:
                # Value in range 1e8..1e11 in a ms field looks like seconds; flag, don't silently convert (R10)
                flags.add("UNIT_SUSPECT")
            utc_ms = num_val
        else:
            tz_basis = "not_applicable"

    elif unit == "us":
        tz_basis = "utc_source"
        if num_val is not None:
            utc_ms = num_val // 1000
        else:
            tz_basis = "not_applicable"

    elif unit == "exif_naive":
        parsed_dt = parse_exif_datetime_str(raw_str)
        if parsed_dt is None:
            tz_basis = "not_applicable"
            utc_ms = None
        elif config.assumed_naive_offset_minutes is not None:
            # Explicit analyst configuration applies assumed offset
            offset_td = timedelta(minutes=config.assumed_naive_offset_minutes)
            tz_obj = timezone(offset_td)
            utc_dt = parsed_dt.replace(tzinfo=tz_obj).astimezone(timezone.utc)
            utc_ms = int(utc_dt.timestamp() * 1000)
            tz_basis = "naive_unknown_tz"
            flags.add("NAIVE_LOCAL")
        else:
            # Default: strictly no assumption, utc_ms stays None (spec B11.4)
            utc_ms = None
            tz_basis = "naive_unknown_tz"

    elif unit == "exif_offset":
        parsed_dt = parse_exif_datetime_str(raw_str)
        offset_mins = parse_offset_minutes(offset_str)
        if parsed_dt is not None and offset_mins is not None:
            tz_obj = timezone(timedelta(minutes=offset_mins))
            utc_dt = parsed_dt.replace(tzinfo=tz_obj).astimezone(timezone.utc)
            utc_ms = int(utc_dt.timestamp() * 1000)
            tz_basis = "offset_given"
        elif parsed_dt is not None:
            # Offset was missing or unparseable; treat as naive
            utc_ms = None
            tz_basis = "naive_unknown_tz"
        else:
            tz_basis = "not_applicable"
            utc_ms = None

    elif unit == "gps_utc":
        gps_ms = parse_gps_timestamp_to_utc_ms(raw_str, gps_time_tuple)
        if gps_ms is not None:
            utc_ms = gps_ms
            tz_basis = "utc_source"
        else:
            tz_basis = "not_applicable"
            utc_ms = None

    elif unit == "unknown":
        tz_basis = "not_applicable"
        utc_ms = None

    # Check temporal threshold flags against utc_ms
    if utc_ms is not None:
        if utc_ms < config.pre_2009_floor_ms:
            flags.add("PRE_2009")

        if evidence_ingest_time_ms is not None:
            if utc_ms > evidence_ingest_time_ms + config.future_tolerance_ms:
                flags.add("FUTURE")

    sorted_flags = tuple(sorted(flags))
    return TimeValue(
        raw=raw if raw is not None else "",
        unit=unit,
        utc_ms=utc_ms,
        tz_basis=tz_basis,
        flags=sorted_flags,
    )