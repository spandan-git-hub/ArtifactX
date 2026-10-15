"""Unit tests for time value normalization and quality flags (spec B11.1, Rules R10, R11)."""

import pytest
from datetime import datetime, timezone
from forensic.timeline import (
    TimelineConfig,
    TimeValue,
    normalize_time_value,
    parse_exif_datetime_str,
    parse_gps_timestamp_to_utc_ms,
    parse_offset_minutes,
)


def test_seconds_to_ms_conversion():
    """Verify seconds unit converts to ms with utc_source basis."""
    # 2024-09-11 00:00:00 UTC = 1726012800 s
    tv = normalize_time_value(1726012800, unit="s")
    assert tv.utc_ms == 1726012800000
    assert tv.tz_basis == "utc_source"
    assert tv.unit == "s"
    assert "ZERO" not in tv.flags
    assert "PRE_2009" not in tv.flags
    assert "UNIT_SUSPECT" not in tv.flags


def test_milliseconds_normalization():
    """Verify milliseconds unit preserves value with utc_source basis."""
    tv = normalize_time_value(1726012800000, unit="ms")
    assert tv.utc_ms == 1726012800000
    assert tv.tz_basis == "utc_source"
    assert tv.unit == "ms"
    assert tv.flags == ()


def test_microseconds_normalization():
    """Verify microseconds unit divides by 1000."""
    tv = normalize_time_value(1726012800000000, unit="us")
    assert tv.utc_ms == 1726012800000
    assert tv.tz_basis == "utc_source"


def test_exif_naive_without_assumed_offset():
    """Verify naive EXIF DateTimeOriginal yields utc_ms=None and naive_unknown_tz basis."""
    tv = normalize_time_value("2026:09:15 14:30:00", unit="exif_naive")
    assert tv.utc_ms is None
    assert tv.tz_basis == "naive_unknown_tz"
    assert "NAIVE_LOCAL" not in tv.flags


def test_exif_naive_with_analyst_assumed_offset():
    """Verify naive EXIF with explicit analyst offset calculates UTC and flags NAIVE_LOCAL."""
    # Assume IST: +05:30 (+330 minutes)
    cfg = TimelineConfig(assumed_naive_offset_minutes=330)
    tv = normalize_time_value("2026:09:15 14:30:00", unit="exif_naive", config=cfg)
    assert tv.utc_ms is not None
    assert "NAIVE_LOCAL" in tv.flags
    assert tv.tz_basis == "naive_unknown_tz"

    # 14:30:00 in +05:30 is 09:00:00 UTC
    dt = datetime.fromtimestamp(tv.utc_ms / 1000.0, tz=timezone.utc)
    assert dt.hour == 9
    assert dt.minute == 0


def test_exif_with_offset_time_original():
    """Verify EXIF with explicit OffsetTimeOriginal calculates correct UTC."""
    # 10:15:00 at +05:30 is 04:45:00 UTC
    tv = normalize_time_value(
        "2026:09:16 10:15:00",
        unit="exif_offset",
        offset_str="+05:30",
    )
    assert tv.utc_ms is not None
    assert tv.tz_basis == "offset_given"
    dt = datetime.fromtimestamp(tv.utc_ms / 1000.0, tz=timezone.utc)
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 16
    assert dt.hour == 4
    assert dt.minute == 45


def test_gps_timestamp_utc():
    """Verify GPSDateStamp and GPSTimeStamp calculate exact UTC timestamp."""
    # GPS time: 2026:09:16 at 04:45:00 UTC
    tv = normalize_time_value(
        "2026:09:16",
        unit="gps_utc",
        gps_time_tuple=(4, 45, 0),
    )
    assert tv.utc_ms is not None
    assert tv.tz_basis == "utc_source"
    dt = datetime.fromtimestamp(tv.utc_ms / 1000.0, tz=timezone.utc)
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 16
    assert dt.hour == 4
    assert dt.minute == 45


def test_quality_flags_zero_and_negative():
    """Verify ZERO and NEGATIVE flags."""
    tv_zero = normalize_time_value(0, unit="ms")
    assert "ZERO" in tv_zero.flags
    assert "PRE_2009" in tv_zero.flags  # 1970 is before 2009

    tv_neg = normalize_time_value(-5000, unit="s")
    assert "NEGATIVE" in tv_neg.flags
    assert "PRE_2009" in tv_neg.flags


def test_quality_flag_pre_2009():
    """Verify PRE_2009 flag for timestamps before Jan 1, 2009."""
    # 2005-01-01 in ms
    tv = normalize_time_value(1104537600000, unit="ms")
    assert "PRE_2009" in tv.flags

    # 2024-01-01 in ms is after 2009
    tv_modern = normalize_time_value(1704067200000, unit="ms")
    assert "PRE_2009" not in tv_modern.flags


def test_quality_flag_future_deterministic():
    """Verify FUTURE flag uses evidence ingest time, ensuring determinism across runs."""
    ingest_time_ms = 1726000000000
    cfg = TimelineConfig(future_tolerance_ms=300000)  # 5 min

    # Normal timestamp within ingest window: no FUTURE flag
    tv_past = normalize_time_value(
        1726000000000 - 10000,
        unit="ms",
        evidence_ingest_time_ms=ingest_time_ms,
        config=cfg,
    )
    assert "FUTURE" not in tv_past.flags

    # Future timestamp exceeding ingest_time_ms + 5 min: FUTURE flag set
    tv_future = normalize_time_value(
        ingest_time_ms + 400000,
        unit="ms",
        evidence_ingest_time_ms=ingest_time_ms,
        config=cfg,
    )
    assert "FUTURE" in tv_future.flags


def test_quality_flag_unit_suspect_no_silent_conversion():
    """Verify UNIT_SUSPECT flags magnitude mismatch without silently mutating value (R10)."""
    # Seconds unit with magnitude > 1e11 (looks like ms): flag, don't divide!
    val_huge = 1726000000000
    tv_sec = normalize_time_value(val_huge, unit="s")
    assert "UNIT_SUSPECT" in tv_sec.flags
    # Crucial test: value was NOT silently divided by 1000
    assert tv_sec.utc_ms == val_huge * 1000

    # Milliseconds unit with magnitude < 1e11 and > 1e8 (looks like seconds): flag, don't multiply!
    val_sec_sized = 1726000000
    tv_ms = normalize_time_value(val_sec_sized, unit="ms")
    assert "UNIT_SUSPECT" in tv_ms.flags
    # Crucial test: value was NOT silently multiplied by 1000
    assert tv_ms.utc_ms == val_sec_sized


def test_flags_sorted_tuple():
    """Verify flags are returned as a sorted tuple."""
    # A negative timestamp before 2009
    tv = normalize_time_value(-1000, unit="ms")
    assert isinstance(tv.flags, tuple)
    assert tv.flags == tuple(sorted(tv.flags))
