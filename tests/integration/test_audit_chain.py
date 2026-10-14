"""
Integration tests for hash-chained audit service and verification (B5.5, R5, R11).
"""

import concurrent.futures
from typing import Generator
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.models import AuditLog, Case
from backend.services.audit_service import AuditService, redact_sensitive_keys, GENESIS_HASH


@pytest.fixture
def test_case(db_session: Session) -> Case:
    case = Case(name="Audit Chain Test Case", description="Testing B5.5 audit chain")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def test_audit_chain_append_and_verify(db_session: Session, test_case: Case):
    """Assert audit chain appends entries with monotonic seq and passes unbroken verification."""
    # Ensure fresh chain in test session
    entries = []
    actions = ["INGEST", "DETECT", "PARSE_WHATSAPP", "TIMELINE_BUILD", "REPORT_GENERATED"]
    for act in actions:
        entry = AuditService.append(
            db=db_session,
            action=act,
            actor="analyst_alice",
            case_id=test_case.id,
            details={"step": act, "item_count": 42},
        )
        entries.append(entry)

    assert len(entries) == 5
    # Verify monotonic seq
    for idx, e in enumerate(entries):
        assert e.seq == idx + 1

    # Verify genesis prev_hash
    assert entries[0].prev_hash == GENESIS_HASH

    # Verify chaining
    for i in range(1, len(entries)):
        assert entries[i].prev_hash == entries[i - 1].entry_hash

    # Verify entire chain
    res = AuditService.verify_audit_chain(db_session)
    assert res.ok is True
    assert res.checked >= 5
    assert res.first_bad_seq is None
    assert res.head_hash == entries[-1].entry_hash


def test_audit_chain_detects_content_tampering(db_session: Session, test_case: Case):
    """Assert modifying details_json of an existing audit entry breaks the chain."""
    entry1 = AuditService.append(db=db_session, action="STEP_1", case_id=test_case.id, details={"val": 1})
    entry2 = AuditService.append(db=db_session, action="STEP_2", case_id=test_case.id, details={"val": 2})
    entry3 = AuditService.append(db=db_session, action="STEP_3", case_id=test_case.id, details={"val": 3})

    # Tamper with row 2 using raw SQL to bypass ORM event hooks
    db_session.execute(
        text("UPDATE audit_log SET details_json = '{\"val\": 999}' WHERE seq = :seq"),
        {"seq": entry2.seq},
    )
    db_session.commit()

    # Chain verification walk must fail and flag row 2
    res = AuditService.verify_audit_chain(db_session)
    assert res.ok is False
    assert res.first_bad_seq == entry2.seq
    assert "Entry hash mismatch" in (res.error_detail or "")


def test_audit_chain_detects_row_deletion(db_session: Session, test_case: Case):
    """Assert deleting a middle entry breaks sequence and hash pointer."""
    entry1 = AuditService.append(db=db_session, action="STEP_A", case_id=test_case.id)
    entry2 = AuditService.append(db=db_session, action="STEP_B", case_id=test_case.id)
    entry3 = AuditService.append(db=db_session, action="STEP_C", case_id=test_case.id)

    # Delete entry2 via raw SQL
    db_session.execute(
        text("DELETE FROM audit_log WHERE seq = :seq"),
        {"seq": entry2.seq},
    )
    db_session.commit()

    res = AuditService.verify_audit_chain(db_session)
    assert res.ok is False
    assert res.first_bad_seq == entry3.seq
    assert "discontinuity" in (res.error_detail or "").lower() or "broken" in (res.error_detail or "").lower()


def test_audit_chain_r5_key_redaction(db_session: Session, test_case: Case):
    """Assert R5: keys, passphrases, and key-derived secrets are never stored in audit details."""
    sensitive_dict = {
        "action_info": "decrypt",
        "key": "64_hex_secret_key_material_0123456789abcdef",
        "root_key": "another_secret",
        "passphrase": "super_secret_password",
        "nested": {
            "auth_key": b"secret_binary_tokens",
            "normal_field": "public_data",
        },
    }

    entry = AuditService.append(
        db=db_session,
        action="DECRYPT_ATTEMPT",
        case_id=test_case.id,
        details=sensitive_dict,
    )

    stored_details = entry.details_json
    # Confirm raw secrets are not present
    details_str = str(stored_details)
    assert "64_hex_secret_key_material" not in details_str
    assert "super_secret_password" not in details_str
    assert "another_secret" not in details_str
    assert "REDACTED" in stored_details["key"]
    assert "REDACTED" in stored_details["passphrase"]
    assert stored_details["nested"]["normal_field"] == "public_data"


def test_audit_chain_thread_concurrency(db_session: Session, test_case: Case):
    """Assert concurrent appends maintain strictly monotonic sequences and unbroken hash chain."""
    def worker(worker_id: int):
        # Use separate connection session per thread
        from backend.app.database import SessionLocal
        local_db = SessionLocal()
        try:
            for i in range(5):
                AuditService.append(
                    db=local_db,
                    action=f"WORKER_{worker_id}_ACTION_{i}",
                    actor=f"worker_{worker_id}",
                    case_id=test_case.id,
                    details={"worker": worker_id, "step": i},
                )
        finally:
            local_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, w) for w in range(4)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Verify complete chain
    res = AuditService.verify_audit_chain(db_session)
    assert res.ok is True
    assert res.checked >= 20
    assert res.first_bad_seq is None


def test_audit_chain_api_verify(db_session: Session, test_case: Case):
    """Test GET /api/audit/verify HTTP endpoint."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    AuditService.append(db=db_session, action="API_TEST_ACTION", case_id=test_case.id, details={"test": True})

    client = TestClient(app)
    response = client.get("/api/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["checked"] >= 1
    assert data["head_hash"] is not None

