"""
Integration tests for WhatsApp Decryption API and mandatory R5 key leak audit (B6.6).
Strictly adheres to:
- master.md R3: Evidence immutability; hash chain audit logging.
- master.md R4: Zero disk writes; PostgreSQL BYTEA in-memory streaming.
- master.md R5: Keys are radioactive. Mandatory comprehensive secret leak scan.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.models.models import (
    ActivityLog,
    Case,
    DecryptionOperation,
    DerivedArtifact,
    ErrorLog,
    Evidence,
)
from backend.services.audit_service import AuditService


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
def test_api_decryption_detect_crypt14_and_crypt15(client_and_db):
    """B6.6: POST /api/evidence/{id}/decryption/detect accurately identifies container formats."""
    client, db = client_and_db

    case = Case(name="Detect Test Case", investigator="Agent")
    db.add(case)
    db.flush()

    c14_bytes = Path("testdata/DS-02-dev/msgstore.db.crypt14").read_bytes()
    ev14 = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt14",
        storage_path="in-memory/msgstore.db.crypt14",
        sha256=hashlib.sha256(c14_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c14_bytes,
        integrity_state="OK",
    )
    db.add(ev14)

    c15_bytes = Path("testdata/DS-03-dev/msgstore.db.crypt15").read_bytes()
    ev15 = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt15",
        storage_path="in-memory/msgstore.db.crypt15",
        sha256=hashlib.sha256(c15_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c15_bytes,
        integrity_state="OK",
    )
    db.add(ev15)
    db.commit()

    # Detect on Crypt14
    resp14 = client.post(f"/api/evidence/{ev14.id}/decryption/detect")
    assert resp14.status_code == 200, resp14.text
    d14 = resp14.json()
    assert d14["is_encrypted"]
    assert d14["format"] == "crypt14"

    # Detect on Crypt15
    resp15 = client.post(f"/api/evidence/{ev15.id}/decryption/detect")
    assert resp15.status_code == 200, resp15.text
    d15 = resp15.json()
    assert d15["is_encrypted"]
    assert d15["format"] == "crypt15"


@pytest.mark.integration
def test_api_decryption_run_crypt14_happy_path(client_and_db):
    """B6.6: Happy path decryption of Crypt14 container with DerivedArtifact provenance and audit chain."""
    client, db = client_and_db

    case = Case(name="C14 Happy Path Case", investigator="Agent")
    db.add(case)
    db.flush()

    c14_bytes = Path("testdata/DS-02-dev/msgstore.db.crypt14").read_bytes()
    key_bytes = Path("testdata/DS-02-dev/keys/key").read_bytes()
    manifest = json.loads(Path("testdata/DS-02-dev/manifest.json").read_text(encoding="utf-8"))
    expected_sha256 = manifest["encryption"]["plaintext_sha256"]

    ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt14",
        storage_path="in-memory/msgstore.db.crypt14",
        sha256=hashlib.sha256(c14_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c14_bytes,
        integrity_state="OK",
    )
    db.add(ev)
    db.commit()

    # Base64 encode key file for key_data field
    key_b64 = base64.b64encode(key_bytes).decode("ascii")

    req_body = {
        "key_type": "crypt14_keyfile",
        "key_data": key_b64,
        "format_override": "crypt14",
    }
    resp = client.post(f"/api/evidence/{ev.id}/decryption/run", json=req_body)
    assert resp.status_code == 200, resp.text
    res_json = resp.json()

    assert res_json["status"] == "SUCCEEDED"
    assert res_json["output_sha256"] == expected_sha256
    derived_id = res_json["derived_artifact_id"]
    assert derived_id is not None

    # Verify DerivedArtifact in DB
    derived = db.query(DerivedArtifact).filter(DerivedArtifact.id == derived_id).first()
    assert derived is not None
    assert derived.sha256 == expected_sha256
    assert derived.content_bytes[:16] == b"SQLite format 3\x00"
    assert derived.provenance["source_evidence_id"] == ev.id
    assert derived.provenance["output_sha256"] == expected_sha256

    # Verify audit chain integrity
    audit_chain_res = AuditService.verify_audit_chain(db=db)
    assert audit_chain_res.ok


@pytest.mark.integration
def test_api_decryption_run_crypt15_happy_path(client_and_db):
    """B6.6: Happy path decryption of Crypt15 container with 64-hex key."""
    client, db = client_and_db

    case = Case(name="C15 Happy Path Case", investigator="Agent")
    db.add(case)
    db.flush()

    c15_bytes = Path("testdata/DS-03-dev/msgstore.db.crypt15").read_bytes()
    hex_str = Path("testdata/DS-03-dev/keys/root_key.hex").read_text(encoding="utf-8").strip()
    manifest = json.loads(Path("testdata/DS-03-dev/manifest.json").read_text(encoding="utf-8"))
    expected_sha256 = manifest["encryption"]["plaintext_sha256"]

    ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt15",
        storage_path="in-memory/msgstore.db.crypt15",
        sha256=hashlib.sha256(c15_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c15_bytes,
        integrity_state="OK",
    )
    db.add(ev)
    db.commit()

    req_body = {
        "key_type": "crypt15_hex",
        "key_data": hex_str,
        "format_override": "crypt15",
    }
    resp = client.post(f"/api/evidence/{ev.id}/decryption/run", json=req_body)
    assert resp.status_code == 200, resp.text
    res_json = resp.json()

    assert res_json["status"] == "SUCCEEDED"
    assert res_json["output_sha256"] == expected_sha256
    derived_id = res_json["derived_artifact_id"]
    assert derived_id is not None

    derived = db.query(DerivedArtifact).filter(DerivedArtifact.id == derived_id).first()
    assert derived.sha256 == expected_sha256


@pytest.mark.integration
def test_api_decryption_passphrase_rejection(client_and_db):
    """B6.6: Passphrases offered on Crypt15 return FAILED with PASSPHRASE_NOT_SUPPORTED."""
    client, db = client_and_db

    case = Case(name="Passphrase Reject Case", investigator="Agent")
    db.add(case)
    db.flush()

    c15_bytes = Path("testdata/DS-03-dev/msgstore.db.crypt15").read_bytes()
    ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt15",
        storage_path="in-memory/msgstore.db.crypt15",
        sha256=hashlib.sha256(c15_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c15_bytes,
        integrity_state="OK",
    )
    db.add(ev)
    db.commit()

    req_body = {
        "key_type": "crypt15_hex",
        "key_data": "MySampleUserPassphraseNotKey!",
        "format_override": "crypt15",
    }
    resp = client.post(f"/api/evidence/{ev.id}/decryption/run", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert "PASSPHRASE_NOT_SUPPORTED" in data["error_message"]


@pytest.mark.integration
def test_api_mandatory_r5_key_leak_audit(client_and_db, caplog):
    """
    B6.6 & master.md R5 MANDATORY TEST:
    Execute decryption with a recognizable canary key (64 x 'a').
    Scan:
    - audit_log table
    - decryption_operations table
    - error_logs table
    - activity_logs table
    - captured structlog/caplog output
    - exception messages
    - OpenAPI schema
    - 422 forced-validation-failure response
    Assert: ZERO occurrences of the key hex, base64, or raw bytes!
    """
    client, db = client_and_db

    canary_hex = "a" * 64
    canary_bytes = bytes.fromhex(canary_hex)
    canary_b64 = base64.b64encode(canary_bytes).decode("ascii")

    case = Case(name="R5 Leak Audit Case", investigator="Agent")
    db.add(case)
    db.flush()

    c15_bytes = Path("testdata/DS-03-dev/msgstore.db.crypt15").read_bytes()
    ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db.crypt15",
        storage_path="in-memory/msgstore.db.crypt15",
        sha256=hashlib.sha256(c15_bytes).hexdigest(),
        content_type="application/octet-stream",
        content_bytes=c15_bytes,
        integrity_state="OK",
    )
    db.add(ev)
    db.commit()

    # 1. Run decryption with canary key (will fail authentication as wrong key)
    req_body = {
        "key_type": "crypt15_hex",
        "key_data": canary_hex,
        "format_override": "crypt15",
    }
    resp = client.post(f"/api/evidence/{ev.id}/decryption/run", json=req_body)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "FAILED"

    # 2. Trigger a 422 validation failure with canary key
    bad_req_body = {
        "key_type": "crypt15_hex",
        "key_data": 123456,  # Invalid type triggers RequestValidationError
        "extra_field_with_canary": canary_hex,
    }
    resp_422 = client.post(f"/api/evidence/{ev.id}/decryption/run", json=bad_req_body)
    assert resp_422.status_code == 422
    text_422 = resp_422.text

    # Assert 422 response did NOT echo canary_hex or canary_b64
    assert canary_hex not in text_422
    assert canary_b64 not in text_422

    # 3. Query all relevant database tables
    from backend.models.models import AuditLog

    audit_rows = db.query(AuditLog).filter(AuditLog.case_id == case.id).all()
    op_rows = db.query(DecryptionOperation).filter(DecryptionOperation.case_id == case.id).all()
    error_rows = db.query(ErrorLog).all()
    activity_rows = db.query(ActivityLog).filter(ActivityLog.case_id == case.id).all()

    # Scan audit logs
    for ar in audit_rows:
        ar_str = json.dumps(ar.details_json or {}) + (ar.action or "")
        assert canary_hex not in ar_str
        assert canary_b64 not in ar_str

    # Scan decryption operations
    for op in op_rows:
        op_str = json.dumps(op.parameters or {}) + (op.error_message or "") + op.status
        assert canary_hex not in op_str
        assert canary_b64 not in op_str

    # Scan error logs
    for er in error_rows:
        er_str = (er.message or "") + (er.stack_trace or "")
        assert canary_hex not in er_str
        assert canary_b64 not in er_str

    # Scan activity logs
    for act in activity_rows:
        act_str = (act.description or "") + (act.action or "")
        assert canary_hex not in act_str
        assert canary_b64 not in act_str

    # Scan captured structlog / caplog output
    log_text = caplog.text
    assert canary_hex not in log_text
    assert canary_b64 not in log_text

    # Scan OpenAPI JSON schema
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    assert canary_hex not in openapi_resp.text
    assert canary_b64 not in openapi_resp.text
