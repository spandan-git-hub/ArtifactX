"""
Integration tests for WhatsApp parsing API, audit logging, idempotency, and repository storage (spec B7.5).
"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import AuditLog, Case, DerivedArtifact, Evidence, WhatsAppChat, WhatsAppEdit, WhatsAppMessage, WhatsAppRevocation


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def wa_evidence(db_session: Session) -> Evidence:
    """Create a test Case and Evidence with DS-01-dev msgstore.db content."""
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    if not ds01_path.exists():
        pytest.skip("DS-01-dev/msgstore.db fixture not found")

    content = ds01_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    test_case = Case(
        name="WA Forensic Test Case",
        case_number="CASE-WA-001",
        investigator="Agent Forensic",
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    ev = Evidence(
        case_id=test_case.id,
        original_filename="msgstore.db",
        storage_path="testdata/DS-01-dev/msgstore.db",
        sha256=sha256,
        content_bytes=content,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    return ev


def test_whatsapp_parse_api_and_audit(client: TestClient, db_session: Session, wa_evidence: Evidence):
    """Verify POST /api/whatsapp/parse/{id} triggers parsing and writes hash-chained audit log."""
    res = client.post(f"/api/whatsapp/parse/{wa_evidence.id}")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["evidence_id"] == wa_evidence.id
    assert data["schema_family"] == "modern"
    assert data["messages_count"] >= 380
    assert data["chats_count"] >= 4
    assert data["revocations_count"] >= 1
    assert data["edits_count"] >= 1

    # Verify audit log entry
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.evidence_id == wa_evidence.id, AuditLog.action == "whatsapp_parse")
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.details_json["schema_family"] == "modern"
    assert audit_entry.details_json["messages_count"] == data["messages_count"]


def test_whatsapp_parse_idempotency(client: TestClient, db_session: Session, wa_evidence: Evidence):
    """
    Assert parsing twice on the same evidence replaces existing rows atomically
    and does not duplicate messages, chats, revocations, or edits (B7.5).
    """
    res1 = client.post(f"/api/whatsapp/parse/{wa_evidence.id}")
    assert res1.status_code == 200
    count1 = res1.json()["messages_count"]

    db_msgs_1 = db_session.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == wa_evidence.id).count()
    db_chats_1 = db_session.query(WhatsAppChat).filter(WhatsAppChat.evidence_id == wa_evidence.id).count()
    db_revs_1 = db_session.query(WhatsAppRevocation).filter(WhatsAppRevocation.evidence_id == wa_evidence.id).count()

    # Second parse
    res2 = client.post(f"/api/whatsapp/parse/{wa_evidence.id}")
    assert res2.status_code == 200
    count2 = res2.json()["messages_count"]

    db_msgs_2 = db_session.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == wa_evidence.id).count()
    db_chats_2 = db_session.query(WhatsAppChat).filter(WhatsAppChat.evidence_id == wa_evidence.id).count()
    db_revs_2 = db_session.query(WhatsAppRevocation).filter(WhatsAppRevocation.evidence_id == wa_evidence.id).count()

    assert count1 == count2
    assert db_msgs_1 == db_msgs_2 == count1
    assert db_chats_1 == db_chats_2
    assert db_revs_1 == db_revs_2


def test_whatsapp_get_endpoints(client: TestClient, db_session: Session, wa_evidence: Evidence):
    """Verify all GET endpoints expose forensic data with additive fields and findings."""
    client.post(f"/api/whatsapp/parse/{wa_evidence.id}")

    # 1. Messages endpoint
    msgs_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-messages")
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) >= 380

    m0 = msgs[0]
    assert "key_id" in m0
    assert "chat_row_id" in m0
    assert "message_type_name" in m0
    assert "ts_utc_ms" in m0
    assert "source_table" in m0
    assert m0["source_table"] == "message"

    # 2. Chats endpoint
    chats_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-chats")
    assert chats_res.status_code == 200
    chats = chats_res.json()
    assert len(chats) >= 4
    assert any(c["is_group"] is True for c in chats)

    # 3. Revocations endpoint
    rev_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-revocations")
    assert rev_res.status_code == 200
    revs = rev_res.json()
    assert len(revs) >= 1
    assert revs[0]["strength"] == "deterministic"
    assert revs[0]["confidence_score"] == 1.0
    assert revs[0]["revoked_key_id"] != ""

    # 4. Edits endpoint
    edits_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-edits")
    assert edits_res.status_code == 200
    edits = edits_res.json()
    assert len(edits) >= 1
    assert edits[0]["strength"] == "deterministic"
    assert edits[0]["confidence_score"] == 1.0

    # 5. Contacts & Groups endpoint
    cnt_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-contacts")
    assert cnt_res.status_code == 200
    grp_res = client.get(f"/api/whatsapp/evidence/{wa_evidence.id}/wa-groups")
    assert grp_res.status_code == 200


def test_whatsapp_parse_derived_artifact(client: TestClient, db_session: Session, wa_evidence: Evidence):
    """Verify parsing a decrypted DerivedArtifact via ?derived_artifact_id query param."""
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    content = ds01_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    derived = DerivedArtifact(
        case_id=wa_evidence.case_id,
        parent_evidence_id=wa_evidence.id,
        original_filename="msgstore.db",
        artifact_type="decrypted_sqlite",
        sha256=sha256,
        content_bytes=content,
    )
    db_session.add(derived)
    db_session.commit()
    db_session.refresh(derived)

    res = client.post(f"/api/whatsapp/parse/{wa_evidence.id}?derived_artifact_id={derived.id}")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify messages have derived_artifact_id populated
    first_msg = (
        db_session.query(WhatsAppMessage)
        .filter(WhatsAppMessage.evidence_id == wa_evidence.id)
        .first()
    )
    assert first_msg is not None
    assert first_msg.derived_artifact_id == str(derived.id)
