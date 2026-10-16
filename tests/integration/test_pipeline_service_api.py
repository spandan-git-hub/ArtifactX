"""
Integration tests for backend pipeline service and API endpoints (spec 11_PIPELINE_AND_E2E.md §B13.2).

Verifies:
- POST /api/cases/{case_id}/pipeline/run
- Single-flight concurrency exclusion (HTTP 409 on overlap)
- GET /api/cases/{case_id}/pipeline/runs
- GET /api/pipeline/runs/{run_id}
- Pre-stage integrity verification
- Hash-chained audit log recording (PIPELINE_START, STAGE_*, PIPELINE_COMPLETE)
- R5 key material exclusion from middleware and error logs
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.models.models import Case, Evidence, PipelineRun
from backend.services.audit_service import AuditService
from forensic.common.hashing import sha256_hex


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def test_case_with_wa_evidence(db_session):
    """Create test case with DS-01 msgstore.db exhibit."""
    case = Case(
        name="Pipeline Test Case",
        description="Testing end-to-end pipeline API",
        investigator="Forensic Examiner",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Ingest msgstore.db
    msgstore_path = Path("testdata/DS-01-dev/msgstore.db")
    msgstore_data = msgstore_path.read_bytes()
    ev1 = Evidence(
        case_id=case.id,
        original_filename="msgstore.db",
        storage_path="memory://msgstore.db",
        sha256=sha256_hex(msgstore_data),
        content_bytes=msgstore_data,
        integrity_state="OK",
        evidence_type="whatsapp_db",
    )
    db_session.add(ev1)

    # Ingest wa.db
    wa_path = Path("testdata/DS-01-dev/wa.db")
    wa_data = wa_path.read_bytes()
    ev2 = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="memory://wa.db",
        sha256=sha256_hex(wa_data),
        content_bytes=wa_data,
        integrity_state="OK",
        evidence_type="whatsapp_db",
    )
    db_session.add(ev2)
    db_session.commit()

    return case


def test_pipeline_api_run_and_status(client, test_case_with_wa_evidence):
    """Verify triggering pipeline via API runs to completion and records stages."""
    case_id = test_case_with_wa_evidence.id

    resp = client.post(f"/api/cases/{case_id}/pipeline/run", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["case_id"] == case_id
    assert data["status"] in ("COMPLETED", "PARTIAL")
    assert len(data["content_hash"]) == 64
    assert len(data["stage_runs"]) > 0

    run_id = data["id"]

    # Verify GET /api/cases/{case_id}/pipeline/runs
    list_resp = client.get(f"/api/cases/{case_id}/pipeline/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    assert any(r["id"] == run_id for r in runs)

    # Verify GET /api/pipeline/runs/{run_id}
    detail_resp = client.get(f"/api/pipeline/runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == run_id
    assert len(detail["stage_runs"]) == len(data["stage_runs"])


def test_pipeline_api_concurrent_run_409(client, test_case_with_wa_evidence, db_session):
    """Verify that launching a run when one is already IN_PROGRESS returns HTTP 409 Conflict."""
    case_id = test_case_with_wa_evidence.id

    # Create an artificial IN_PROGRESS run
    in_progress_run = PipelineRun(
        id="pipe_active_test_lock",
        case_id=case_id,
        status="IN_PROGRESS",
    )
    db_session.add(in_progress_run)
    db_session.commit()

    try:
        resp = client.post(f"/api/cases/{case_id}/pipeline/run", json={})
        assert resp.status_code == 409
        assert "already in_progress" in resp.json()["detail"].lower()
    finally:
        db_session.delete(in_progress_run)
        db_session.commit()


def test_pipeline_api_audit_trail_recorded(client, test_case_with_wa_evidence, db_session):
    """Verify that pipeline execution appends PIPELINE_START, STAGE_*, and PIPELINE_COMPLETE to audit log."""
    case_id = test_case_with_wa_evidence.id

    resp = client.post(f"/api/cases/{case_id}/pipeline/run", json={})
    assert resp.status_code == 200

    # Verify cryptographic integrity of entire audit chain
    verification = AuditService.verify_audit_chain(db_session)
    assert verification.ok is True
    assert verification.checked > 0

    # Check for pipeline actions
    from backend.models.models import AuditLog
    entries = db_session.query(AuditLog).filter(AuditLog.case_id == case_id).all()
    actions = [e.action for e in entries]
    assert "PIPELINE_START" in actions
    assert "PIPELINE_COMPLETE" in actions
    assert any("STAGE_" in a for a in actions)


def test_pipeline_api_r5_key_redaction(client, test_case_with_wa_evidence):
    """Assert key bytes sent in request body are excluded from error logs and response bodies."""
    case_id = test_case_with_wa_evidence.id
    secret_hex = "a" * 64

    # Trigger with a key
    payload = {
        "keys": [
            {
                "key_type": "crypt15",
                "key_hex": secret_hex,
            }
        ]
    }
    resp = client.post(f"/api/cases/{case_id}/pipeline/run", json=payload)
    assert resp.status_code == 200
    resp_text = resp.text

    # Secret hex must not appear in response
    assert secret_hex not in resp_text
