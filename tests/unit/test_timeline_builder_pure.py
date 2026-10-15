"""Unit tests for PureTimelineBuilder handling heterogeneous evidence sources (spec B11.2, B11.3, B11.4)."""

import pytest
from forensic.timeline import (
    PureTimelineBuilder,
    TimelineConfig,
)


def test_builder_whatsapp_and_telegram_messages():
    """Verify builder processes both WhatsApp (ms) and Telegram (s) messages into a unified timeline."""
    builder = PureTimelineBuilder()

    wa_msgs = [
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "message_id": 101,
            "key_id": "3EB0_WA_01",
            "chat_jid": "user1@s.whatsapp.net",
            "sender_jid": "user1@s.whatsapp.net",
            "timestamp": 1726000000000,  # ms
            "body": "Hello from WhatsApp",
            "message_type": 0,
        }
    ]

    tg_msgs = [
        {
            "evidence_id": 2,
            "evidence_sha256": "sha_tg",
            "message_id": 201,
            "dialog_id": 999,
            "sender_id": 888,
            "date": 1726000010,  # 10s later in seconds
            "body": "Hello from Telegram",
            "view": "main_view",
        }
    ]

    result = builder.build_timeline(
        whatsapp_messages=wa_msgs,
        telegram_messages=tg_msgs,
    )

    assert len(result.events) == 2
    # Verify WA came first, then TG (10s later)
    assert result.events[0].app == "whatsapp"
    assert result.events[0].time.utc_ms == 1726000000000
    assert result.events[1].app == "telegram"
    assert result.events[1].time.utc_ms == 1726000010000
    assert len(result.timeline_hash) == 64


def test_builder_revocations_and_edits():
    """Verify revocations and edits inherit provenance from both base message and change table."""
    builder = PureTimelineBuilder()

    revs = [
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "revocation_id": 1,
            "message_id": 50,
            "key_id": "3EB0_REV",
            "chat_jid": "group@g.us",
            "revoked_timestamp_ms": 1726000050000,
            "original_timestamp_ms": 1726000000000,
        }
    ]

    edits = [
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "edit_id": 1,
            "message_id": 51,
            "key_id": "3EB0_EDIT",
            "chat_jid": "group@g.us",
            "edit_timestamp_ms": 1726000060000,
            "old_text": "Before edit",
            "new_text": "After edit",
        }
    ]

    result = builder.build_timeline(
        whatsapp_revocations=revs,
        whatsapp_edits=edits,
    )

    assert len(result.events) == 2
    rev_ev = result.events[0]
    assert rev_ev.kind == "revocation"
    # Provenance links to message table and message_revoked table
    assert len(rev_ev.source_refs) == 2
    assert rev_ev.source_refs[0].source_table == "message"
    assert rev_ev.source_refs[1].source_table == "message_revoked"

    edit_ev = result.events[1]
    assert edit_ev.kind == "edit"
    assert len(edit_ev.source_refs) == 2
    assert edit_ev.source_refs[0].source_table == "message"
    assert edit_ev.source_refs[1].source_table == "message_edit_info"


def test_recovered_records_and_tier4_exclusion():
    """Verify Tier 1-3 recovered records are placed, while Tier 4 ID gaps and live duplicates are excluded."""
    builder = PureTimelineBuilder()

    recs = [
        # Tier 2 WAL recovery: valid, placed on timeline with own timestamp
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "finding_id": "find_wal_01",
            "tier": 2,
            "kind": "wal_resident",
            "table_name": "message",
            "recovered_fields": {"timestamp": 1726000020000, "text_data": "Carved WAL message"},
            "validation_status": "FULL_RECORD_VALID",
            "strength": "strong",
            "confidence_score": 0.95,
        },
        # Duplicate of live: must be excluded from timeline (B11.3)
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "finding_id": "find_dup_02",
            "tier": 2,
            "kind": "wal_resident",
            "table_name": "message",
            "recovered_fields": {"timestamp": 1726000020000, "text_data": "Duplicate"},
            "validation_status": "DUPLICATE_OF_LIVE",
            "strength": "strong",
            "confidence_score": 0.95,
        },
        # Tier 4 primary key ID gap: must NOT be placed on timeline (B11.3, DEC-014)
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_wa",
            "finding_id": "find_gap_03",
            "tier": 4,
            "kind": "id_gap",
            "table_name": "message",
            "recovered_fields": {"gap_start": 10, "gap_end": 15},
            "validation_status": "CANDIDATE",
            "strength": "weak_hint",
            "confidence_score": 0.25,
        },
    ]

    result = builder.build_timeline(recovered_records=recs)

    # Only Tier 2 WAL finding placed on timeline
    assert len(result.events) == 1
    assert result.events[0].kind == "recovered_record"
    assert result.events[0].time.utc_ms == 1726000020000
    assert result.events[0].summary == "Carved WAL message"

    # Tier 4 gap recorded in unplaced_indicators
    assert len(result.unplaced_indicators) == 1
    assert result.unplaced_indicators[0]["kind"] == "id_gap"
    assert result.unplaced_indicators[0]["finding_id"] == "find_gap_03"


def test_exif_variants_and_clock_anomaly():
    """Verify EXIF naive, offset, GPS handling and clock anomaly detection between GPS and camera clock."""
    # Tolerance is 120s (2 minutes)
    cfg = TimelineConfig(gps_exif_tolerance_ms=120000)
    builder = PureTimelineBuilder(config=cfg)

    media_items = [
        # Naive only
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_media",
            "filename": "img_naive.jpg",
            "date_time_original": "2026:09:15 14:30:00",
            "exif_type": "naive_dt",
        },
        # Offset given
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_media",
            "filename": "img_offset.jpg",
            "date_time_original": "2026:09:16 10:15:00",
            "offset_time_original": "+05:30",
            "exif_type": "offset_dt",
        },
        # GPS and EXIF in heavy disagreement (> 2 min)
        {
            "evidence_id": 1,
            "evidence_sha256": "sha_media",
            "filename": "img_gps_anomaly.jpg",
            "date_time_original": "2026:09:16 10:15:00",
            "offset_time_original": "+05:30",  # 04:45:00 UTC
            "gps_date_stamp": "2026:09:16",
            "gps_time_stamp": (5, 0, 0),  # 05:00:00 UTC (15 minutes ahead!)
            "exif_type": "gps_dt",
        },
    ]

    result = builder.build_timeline(media_exif_records=media_items)

    assert len(result.events) == 3
    # Check naive has utc_ms=None
    naive_ev = [e for e in result.events if "img_naive.jpg" in e.summary][0]
    assert naive_ev.time.utc_ms is None
    assert naive_ev.time.tz_basis == "naive_unknown_tz"

    # Check offset has valid utc_ms
    offset_ev = [e for e in result.events if "img_offset.jpg" in e.summary][0]
    assert offset_ev.time.utc_ms is not None
    assert offset_ev.time.tz_basis == "offset_given"

    # Check clock anomaly was flagged in unplaced_indicators
    anomalies = [ind for ind in result.unplaced_indicators if ind["kind"] == "clock_anomaly"]
    assert len(anomalies) == 1
    assert "GPS vs EXIF camera clock mismatch" in anomalies[0]["indicator"]
    assert anomalies[0]["delta_seconds"] == 900.0  # 15 minutes


def test_chat_level_duplicate_and_non_monotonic_flags():
    """Verify chat-level duplicate timestamps and backward jumps receive quality flags."""
    cfg = TimelineConfig(backward_jump_threshold_ms=60000)
    builder = PureTimelineBuilder(config=cfg)

    wa_msgs = [
        # Row 1 at t=1000
        {
            "evidence_id": 1,
            "evidence_sha256": "sha1",
            "message_id": 1,
            "chat_jid": "chatA@s.whatsapp.net",
            "sender_jid": "user1",
            "timestamp": 1726000000000,
            "body": "First",
        },
        # Row 2 at t=1000 (duplicate timestamp within chat)
        {
            "evidence_id": 1,
            "evidence_sha256": "sha1",
            "message_id": 2,
            "chat_jid": "chatA@s.whatsapp.net",
            "sender_jid": "user2",
            "timestamp": 1726000000000,
            "body": "Duplicate time",
        },
        # Row 3 at t=1000 - 120,000ms (row increased, but timestamp jumped backwards by 2 minutes!)
        {
            "evidence_id": 1,
            "evidence_sha256": "sha1",
            "message_id": 3,
            "chat_jid": "chatA@s.whatsapp.net",
            "sender_jid": "user1",
            "timestamp": 1726000000000 - 120000,
            "body": "Backward jump",
        },
    ]

    result = builder.build_timeline(whatsapp_messages=wa_msgs)

    events_by_row = {e.source_refs[0].source_row_id: e for e in result.events}
    # Rows 1 and 2 should have DUPLICATE_TS
    assert "DUPLICATE_TS" in events_by_row[1].time.flags
    assert "DUPLICATE_TS" in events_by_row[2].time.flags

    # Row 3 should have NON_MONOTONIC_WITH_ROWID and CLOCK_ANOMALY
    assert "NON_MONOTONIC_WITH_ROWID" in events_by_row[3].time.flags
    assert "CLOCK_ANOMALY" in events_by_row[3].time.flags

    # An indicator should be present in unplaced_indicators
    anomalies = [ind for ind in result.unplaced_indicators if ind.get("indicator") == "Non-monotonic timestamp jump backward"]
    assert len(anomalies) >= 1
    assert anomalies[0]["chat_ref"] == "chatA@s.whatsapp.net"
