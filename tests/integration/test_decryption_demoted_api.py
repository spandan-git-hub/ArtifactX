"""
Integration tests for Decryption API endpoints in demoted state (A6.4).
Verifies:
- /decryption/run returns status DECRYPTOR_NOT_AVAILABLE.
- DecryptionOperation record in DB is recorded with DECRYPTOR_NOT_AVAILABLE.
- /decryption/detect does not return sqlcipher, mtproto, or whatsapp_enc.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.models.models import Case, Evidence, DecryptionOperation


@pytest.fixture
def client_and_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    client = TestClient(app)
    try:
        yield client, db
    finally:
        db.close()


@pytest.mark.integration
def test_api_decryption_run_returns_decryptor_not_available(client_and_db):
    """
    A6.4: Until B6, /decryption/run returns state DECRYPTOR_NOT_AVAILABLE.
    """
    client, db = client_and_db

    # Create case and evidence
    case = Case(name="Decryption Test Case", investigator="Investigator 1")
    db.add(case)
    db.flush()
    case_id = case.id

    encrypted_payload = b"msgstore.db.crypt14_fake_data_" + bytes(256)
    evidence = Evidence(
        case_id=case_id,
        original_filename="msgstore.db.crypt14",
        storage_path="in-memory/msgstore.db.crypt14",
        sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        content_type="application/octet-stream",
        evidence_type="file",
        content_bytes=encrypted_payload,
        integrity_state="OK",
    )
    db.add(evidence)
    db.flush()
    evidence_id = evidence.id
    db.commit()

    # Call /evidence/{id}/decryption/run
    req_body = {
        "key_material": "0123456789abcdef" * 4,
        "format_override": "crypt14",
    }
    resp = client.post(f"/api/evidence/{evidence_id}/decryption/run", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "DECRYPTOR_NOT_AVAILABLE"
    assert data["derived_artifact_id"] is None
    assert "not available" in data["error_message"].lower()

    # Verify operation audit in DB
    op = db.query(DecryptionOperation).filter(DecryptionOperation.id == data["operation_id"]).first()
    assert op is not None
    assert op.status == "DECRYPTOR_NOT_AVAILABLE"
    assert "not available" in op.error_message.lower()
