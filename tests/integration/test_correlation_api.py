"""Integration tests for Correlation API endpoints, idempotency, pre-stage integrity, and audit logging (B12.7).

Follows master.md R3, R5, R8, R10, R11 and 10_CORRELATION.md §B12.7:
- POST /api/cases/{case_id}/correlation/deep/run executes cross-platform correlation.
- Pre-stage ensure_integrity() verification blocks execution on tampered evidence.
- Idempotent re-run produces identical findings and cleans up prior run.
- Audit chain records CORRELATE log entry with hash chain and zero secret leaks.
- GET /api/cases/{case_id}/correlation/findings verifies schema, dual scores, and filtering.
"""

from datetime import datetime, timezone
import hashlib
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.main import app
from backend.models.models import (
    AuditLog,
    Case,
    CorrelationFinding,
    CorrelationEdge,
    Evidence,
    PersonEntity,
    TelegramContact,
    TelegramMessage,
    WhatsAppContact,
    WhatsAppMessage,
)
from backend.services.integrity_service import EvidenceIntegrityError


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def populated_case(db_session: Session) -> Tuple[Case, Evidence]:
    """Create test case with Evidence, WhatsApp, and Telegram exhibits."""
    test_case = Case(
        name="Correlation Integration Case",
        case_number="CASE-CORR-001",
        investigator="Forensic Examiner",
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    # Evidence item
    content = b"Simulated Evidence Buffer for Correlation"
    sha = hashlib.sha256(content).hexdigest()
    ev = Evidence(
        case_id=test_case.id,
        original_filename="sample_evidence.db",
        storage_path="in_memory_sample_evidence.db",
        sha256=sha,
        content_bytes=content,
        integrity_state="OK",
        uploaded_at=datetime(2026, 10, 15, 12, 0, 0),
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    # WhatsApp contact and message with valid BTC address
    wa_cnt = WhatsAppContact(
        evidence_id=ev.id,
        jid="919876543210@s.whatsapp.net",
        display_name="Vikramaditya Rao",
        phone_number="+91 98765 43210",
        status="Available",
    )
    db_session.add(wa_cnt)

    wa_msg = WhatsAppMessage(
        evidence_id=ev.id,
        message_id="wa_msg_101",
        key_id="3EB0_KEY_101",
        key_remote_jid="919876543210@s.whatsapp.net",
        sender_jid="919876543210@s.whatsapp.net",
        body="Deposit funds to 13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf2 or visit https://www.example.test/case-files/archive-2026?utm_source=chat",
        timestamp=1789826400000,
        message_type="0",
        message_type_name="text",
        source_table="message",
        source_row_id=101,
    )
    db_session.add(wa_msg)

    # Telegram contact and message with identical BTC address and URL
    tg_cnt = TelegramContact(
        evidence_id=ev.id,
        user_id=5050,
        first_name="Vikramaditya",
        last_name="Rao",
        username="vikram_rao",
        phone="098765-43210",
    )
    db_session.add(tg_cnt)

    tg_msg = TelegramMessage(
        evidence_id=ev.id,
        mid=2020,
        message_id=2020,
        dialog_id="tg_dialog_1",
        sender_id=5050,
        body="Confirming BTC address 13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf2 and https://example.test/case-files/archive-2026?utm_source=tg",
        date_raw=1789826410,
        date_utc_ms=1789826410000,
        timestamp=1789826410000,
        source_table="messages_v2",
        source_row_id=2020,
        finding_id="tg_mid_2020",
    )
    db_session.add(tg_msg)

    db_session.commit()
    return test_case, ev


def test_deep_correlation_run_and_findings_api(client: TestClient, populated_case: Tuple[Case, Evidence], db_session: Session):
    """Verify POST /cases/{case_id}/correlation/deep/run and GET findings endpoint."""
    test_case, ev = populated_case

    response = client.post(
        f"/api/cases/{test_case.id}/correlation/deep/run",
        json={
            "phone_default_region": "IN",
            "media_hamming_distance": 4,
            "rendezvous_distance_meters": 250.0,
            "rendezvous_time_seconds": 7200,
        }
    )
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    data = response.json()
    assert data["status"] == "SUCCEEDED"
    assert data["case_id"] == test_case.id
    assert data["thresholds_version"] == "1.0.0"
    assert data["total_findings"] >= 3  # Phone identity + BTC address + Canonical URL
    assert data["above_threshold_count"] >= 3

    # Check findings from GET endpoint
    get_res = client.get(f"/api/cases/{test_case.id}/correlation/findings")
    assert get_res.status_code == 200
    findings = get_res.json()
    assert len(findings) >= 3

    # Verify each finding has required B12 attributes
    for f in findings:
        assert "finding_id" in f
        assert "kind" in f
        assert "strength" in f
        assert "match_certainty" in f
        assert 0.0 <= f["match_certainty"] <= 1.0
        assert "confidence_score" in f
        assert f["confidence_score"] < 1.0  # Rule R8
        assert "normalized_value" in f
        assert "left_ref" in f
        assert "right_ref" in f
        assert "limitations" in f
        assert "provenance" in f

    # Filter by kind
    btc_res = client.get(f"/api/cases/{test_case.id}/correlation/findings?kind=crypto_btc")
    assert btc_res.status_code == 200
    btc_findings = btc_res.json()
    assert len(btc_findings) == 1
    assert "13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf2" in btc_findings[0]["normalized_value"]
    assert btc_findings[0]["strength"] == "strong"


def test_deep_correlation_idempotent_rerun(client: TestClient, populated_case: Tuple[Case, Evidence], db_session: Session):
    """Verify re-running correlation produces identical counts without duplicate records."""
    test_case, ev = populated_case

    res1 = client.post(f"/api/cases/{test_case.id}/correlation/deep/run", json={})
    assert res1.status_code == 200
    data1 = res1.json()

    # Second run
    res2 = client.post(f"/api/cases/{test_case.id}/correlation/deep/run", json={})
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["total_findings"] == data2["total_findings"]
    assert data1["persons_count"] == data2["persons_count"]
    assert data1["edges_count"] == data2["edges_count"]

    # Verify DB record count is not doubled
    db_findings_count = db_session.query(CorrelationFinding).filter(CorrelationFinding.case_id == test_case.id).count()
    assert db_findings_count == data1["total_findings"]


def test_correlation_pre_stage_integrity_tamper_detection(populated_case: Tuple[Case, Evidence], db_session: Session):
    """Rule R3: Correlation must abort if evidence has been tampered with."""
    test_case, ev = populated_case

    # Tamper with evidence sha256 to simulate undetected bit flip or corruption
    db_session.execute(
        text("UPDATE evidence SET sha256 = '0000000000000000000000000000000000000000000000000000000000000000' WHERE id = :id"),
        {"id": ev.id}
    )
    db_session.commit()

    from backend.services.correlation_service import correlation_service

    with pytest.raises(EvidenceIntegrityError):
        correlation_service.run_deep_correlation(db_session, test_case.id)


def test_correlation_audit_chain_recording(client: TestClient, populated_case: Tuple[Case, Evidence], db_session: Session):
    """Rule R5, B12.7: CORRELATE action recorded in append-only audit log with zero secrets."""
    test_case, ev = populated_case

    res = client.post(f"/api/cases/{test_case.id}/correlation/deep/run", json={})
    assert res.status_code == 200

    # Query latest audit log entry
    audit_entry = db_session.query(AuditLog).filter(
        AuditLog.case_id == test_case.id,
        AuditLog.action == "CORRELATE",
    ).order_by(AuditLog.seq.desc()).first()

    assert audit_entry is not None, "Expected CORRELATE audit log entry to be recorded"
    assert audit_entry.entry_hash is not None
    assert audit_entry.prev_hash is not None
    assert len(audit_entry.entry_hash) == 64

    details = audit_entry.details_json or {}
    assert details.get("thresholds_version") == "1.0.0"
    assert "total_findings" in details
    assert "above_threshold_count" in details

    # Rule R5 assert zero key material in details
    details_str = str(details).lower()
    for sensitive in ("private_key", "secret", "passphrase", "root_key"):
        assert sensitive not in details_str
