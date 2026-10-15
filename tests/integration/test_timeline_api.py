"""
Integration tests for Timeline build, deterministic idempotency, API endpoints, and audit trail (spec B11.2, master.md R3, R10, R11).

Tests:
1. POST /api/cases/{case_id}/timeline/build produces total deterministic ordering and timeline_hash.
2. Idempotent rebuild: re-running timeline build produces identical events_created and timeline_hash.
3. Pre-stage ensure_integrity() verification blocks execution if evidence has been tampered with.
4. Cryptographic audit trail: TIMELINE_BUILD log entry recorded with hash chain and zero message content (R5).
5. GET /api/cases/{case_id}/timeline and filter endpoints return additive forensic schema fields.
6. Histogram endpoint aggregates events by app and date intervals.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.main import app
from backend.models.models import (
    AuditLog,
    Case,
    Evidence,
    MediaItem,
    RecoveredFinding,
    TelegramMessage,
    TimelineEvent,
    WhatsAppEdit,
    WhatsAppMessage,
    WhatsAppRevocation,
)
from backend.services.timeline_service import timeline_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def populated_case(db_session: Session) -> tuple[Case, Evidence]:
    """Create test case with Evidence, WhatsApp, Telegram, Recovery, and Media items."""
    test_case = Case(
        name="Timeline Integration Case",
        case_number="CASE-TL-001",
        investigator="Forensic Examiner",
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    # 1. Evidence item
    content = b"Simulated Evidence File Buffer"
    sha = hashlib.sha256(content).hexdigest()
    ev = Evidence(
        case_id=test_case.id,
        original_filename="sample_evidence.db",
        storage_path="in_memory_sample_evidence.db",
        sha256=sha,
        content_bytes=content,
        integrity_state="OK",
        uploaded_at=datetime(2026, 9, 15, 12, 0, 0),
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    # 2. WhatsApp Message
    wa_msg = WhatsAppMessage(
        evidence_id=ev.id,
        message_id="wa_msg_001",
        key_id="3EB0_KEY_001",
        key_remote_jid="alice@s.whatsapp.net",
        sender_jid="alice@s.whatsapp.net",
        body="Secret meeting tomorrow",
        timestamp=1726000000000,
        message_type="0",
        message_type_name="text",
        source_table="message",
        source_row_id=1,
    )
    db_session.add(wa_msg)

    # 3. WhatsApp Revocation
    wa_rev = WhatsAppRevocation(
        evidence_id=ev.id,
        revoked_key_id="3EB0_KEY_REV",
        revoke_ts=1726000050000,
        original_sender="alice@s.whatsapp.net",
        original_ts=1726000000000,
        message_row_id=2,
        finding_id="rev_find_001",
    )
    db_session.add(wa_rev)

    # 4. Telegram Message (date in seconds: 1726000020 s -> 1726000020000 ms)
    tg_msg = TelegramMessage(
        evidence_id=ev.id,
        mid=201,
        message_id=201,
        dialog_id="tg_group_999",
        sender_id=888,
        body="Telegram message arrived",
        date_raw=1726000020,
        date_unit="seconds",
        date_utc_ms=1726000020000,
        timestamp=1726000020000,
        source_table="messages_v2",
        source_row_id=201,
        finding_id="tg_find_001",
    )
    db_session.add(tg_msg)

    # 5. Recovered finding (Tier 2 WAL resident)
    rec = RecoveredFinding(
        case_id=test_case.id,
        evidence_id=ev.id,
        finding_id="carved_001",
        tier=2,
        kind="wal_resident",
        source_app="whatsapp",
        method="wal",
        raw_payload_hash="payload_sha256_mock_001",
        body="Carved uncheckpointed row",
        timestamp=1726000030000,
        validation_status="FULL_RECORD_VALID",
        strength="strong",
        confidence_score=0.92,
        recovered_fields={"timestamp": 1726000030000, "text_data": "Carved uncheckpointed row"},
    )
    db_session.add(rec)

    # 6. Media Item with EXIF offset
    media = MediaItem(
        case_id=test_case.id,
        evidence_id=ev.id,
        file_path="evidence_photo.jpg",
        sha256="media_sha256_001",
        mime_type="image/jpeg",
        media_type="image",
        exif_data={
            "DateTimeOriginal": "2026:09:16 10:15:00",
            "OffsetTimeOriginal": "+05:30",
            "exif_type": "offset_dt",
        },
    )
    db_session.add(media)

    db_session.commit()
    return test_case, ev


def test_direct_build(populated_case, db_session):
    test_case, ev = populated_case
    result = timeline_service.build_timeline_for_case(db_session, test_case.id)
    assert result["events_created"] >= 5


def test_timeline_build_and_idempotent_rebuild(client, populated_case, db_session):
    """Verify build_timeline runs and re-running yields identical events_created and timeline_hash."""
    test_case, ev = populated_case

    # First build
    res1 = client.post(f"/api/cases/{test_case.id}/timeline/build")
    assert res1.status_code == 202
    data1 = res1.json()
    assert data1["events_created"] >= 5
    assert "timeline_hash" in data1
    hash1 = data1["timeline_hash"]
    assert len(hash1) == 64

    # Second build (Idempotent rebuild proof per Rule R11)
    res2 = client.post(f"/api/cases/{test_case.id}/timeline/build")
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["events_created"] == data1["events_created"]
    assert data2["timeline_hash"] == hash1

    # Verify rows in DB match
    db_count = db_session.query(TimelineEvent).filter(TimelineEvent.case_id == test_case.id).count()
    assert db_count == data1["events_created"]


def test_timeline_pre_stage_integrity_tamper_detection(client, db_session):
    """Verify pre-stage ensure_integrity() detects tampering and prevents timeline rebuild."""
    tamper_case = Case(
        name="Tamper Test Case",
        case_number="CASE-TL-TAMPER",
        investigator="Forensic Examiner",
    )
    db_session.add(tamper_case)
    db_session.commit()
    db_session.refresh(tamper_case)

    # Insert evidence with mismatched hash on purpose (simulating corrupted exhibit)
    data = b"Tampered Content Bytes Corrupted!"
    wrong_sha = hashlib.sha256(b"DIFFERENT_ORIGINAL_DATA").hexdigest()
    ev = Evidence(
        case_id=tamper_case.id,
        original_filename="corrupted_evidence.db",
        storage_path="in_memory_corrupted.db",
        content_bytes=data,
        sha256=wrong_sha,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()

    # Attempting to rebuild timeline must fail with EvidenceIntegrityError
    with pytest.raises(Exception) as exc_info:
        timeline_service.build_timeline_for_case(db_session, tamper_case.id)
    err_msg = str(exc_info.value).lower()
    assert "integrity" in err_msg or "failed" in err_msg or "mismatch" in err_msg


def test_timeline_hash_chained_audit_trail(client, populated_case, db_session):
    """Verify TIMELINE_BUILD action is logged to append-only audit chain with zero content leak (R5)."""
    test_case, ev = populated_case

    res = client.post(f"/api/cases/{test_case.id}/timeline/build")
    assert res.status_code == 202
    tl_hash = res.json()["timeline_hash"]

    # Verify AuditLog
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.case_id == test_case.id, AuditLog.action == "TIMELINE_BUILD")
        .order_by(AuditLog.seq.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.details_json.get("timeline_hash") == tl_hash
    assert audit_entry.entry_hash is not None
    assert len(audit_entry.entry_hash) == 64

    # R5 verification: Ensure no message body text is leaked in audit details
    details_str = str(audit_entry.details_json)
    assert "Secret meeting" not in details_str
    assert "Telegram message arrived" not in details_str


def test_timeline_get_and_filter_endpoints(client, populated_case):
    """Verify GET and filter endpoints return additive forensic fields."""
    test_case, ev = populated_case

    # Trigger build
    client.post(f"/api/cases/{test_case.id}/timeline/build")

    # 1. GET /api/cases/{case_id}/timeline
    res = client.get(f"/api/cases/{test_case.id}/timeline")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 5

    # Check additive forensic fields on events
    first_ev = events[0]
    assert "event_id" in first_ev
    assert "utc_ms" in first_ev
    assert "time_unit" in first_ev
    assert "tz_basis" in first_ev
    assert "time_flags" in first_ev
    assert "source_refs" in first_ev
    assert "strength" in first_ev

    # 2. POST /api/cases/{case_id}/timeline/filter for WhatsApp only
    res_filter = client.post(
        f"/api/cases/{test_case.id}/timeline/filter",
        json={"source_app": "whatsapp"},
    )
    assert res_filter.status_code == 200
    wa_filtered = res_filter.json()
    assert all(e["source_app"] == "whatsapp" for e in wa_filtered)
    assert len(wa_filtered) >= 2


def test_timeline_histogram_endpoint(client, populated_case):
    """Verify timeline histogram endpoint returns binned density metrics."""
    test_case, ev = populated_case

    # Trigger build
    client.post(f"/api/cases/{test_case.id}/timeline/build")

    res = client.get(f"/api/cases/{test_case.id}/timeline/histogram?interval=day")
    assert res.status_code == 200
    hist = res.json()
    assert hist["case_id"] == test_case.id
    assert hist["total_events"] >= 5
    assert "bins" in hist
    assert len(hist["bins"]) >= 1
    assert "apps_breakdown" in hist
    assert hist["apps_breakdown"]["whatsapp"] >= 1
