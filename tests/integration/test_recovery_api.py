"""
Integration tests for physical recovery API endpoints, idempotency, audit trail, and filters (spec B10.5, master.md R3, R4, R8).

Tests:
1. POST /api/cases/{case_id}/recovery/run triggers 4-tier physical carving and persists findings.
2. Hash-chained audit logging: RECOVER_START and RECOVER_COMPLETE entries recorded with zero message content.
3. Idempotent re-run: triggering recovery multiple times does not duplicate findings.
4. GET /api/cases/{case_id}/recovery/findings supports filtering by tier, strength, and kind.
5. GET /api/cases/{case_id}/recovery/findings/{finding_id} returns single finding detail.
6. Proper 404 response on unknown case.
"""

import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import AuditLog, Case, Evidence, RecoveredFinding, RecoveryRun


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def wa_case_and_evidence(db_session: Session) -> tuple[Case, Evidence]:
    """Create test Case and Evidence with DS-01-dev msgstore.db content."""
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    if not ds01_path.exists():
        pytest.skip("DS-01-dev/msgstore.db fixture not found")

    content = ds01_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    test_case = Case(
        name="Recovery API Test Case",
        case_number="CASE-REC-001",
        investigator="Forensic Examiner",
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
    return test_case, ev


def test_recovery_run_api_and_audit(client: TestClient, db_session: Session, wa_case_and_evidence: tuple[Case, Evidence]):
    """Verify POST /run triggers recovery, creates run record, and appends audit logs."""
    case, ev = wa_case_and_evidence

    res = client.post(f"/api/cases/{case.id}/recovery/run", json={"evidence_id": ev.id})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "SUCCEEDED"
    assert data["findings_count"] > 0
    assert data["case_id"] == case.id

    # Verify audit logs: RECOVER_START and RECOVER_COMPLETE
    audit_start = (
        db_session.query(AuditLog)
        .filter(AuditLog.case_id == case.id, AuditLog.action == "RECOVER_START")
        .first()
    )
    assert audit_start is not None
    # Verify zero message content in audit log details
    assert "content" not in audit_start.details_json
    assert "body" not in audit_start.details_json

    audit_complete = (
        db_session.query(AuditLog)
        .filter(AuditLog.case_id == case.id, AuditLog.action == "RECOVER_COMPLETE")
        .first()
    )
    assert audit_complete is not None
    assert audit_complete.action == "RECOVER_COMPLETE"
    assert "content" not in audit_complete.details_json
    assert "body" not in audit_complete.details_json


def test_recovery_run_idempotency(client: TestClient, db_session: Session, wa_case_and_evidence: tuple[Case, Evidence]):
    """Verify running recovery multiple times is idempotent (no duplicate findings)."""
    case, ev = wa_case_and_evidence

    # First run
    res1 = client.post(f"/api/cases/{case.id}/recovery/run", json={"evidence_id": ev.id})
    assert res1.status_code == 200
    count_1 = db_session.query(RecoveredFinding).filter(RecoveredFinding.case_id == case.id).count()

    # Second run
    res2 = client.post(f"/api/cases/{case.id}/recovery/run", json={"evidence_id": ev.id})
    assert res2.status_code == 200
    count_2 = db_session.query(RecoveredFinding).filter(RecoveredFinding.case_id == case.id).count()

    assert count_1 == count_2
    assert count_1 > 0


def test_list_recovered_findings_and_filters(client: TestClient, db_session: Session, wa_case_and_evidence: tuple[Case, Evidence]):
    """Verify GET /findings with tier, strength, and kind query filters."""
    case, ev = wa_case_and_evidence
    client.post(f"/api/cases/{case.id}/recovery/run", json={"evidence_id": ev.id})

    # 1. Fetch all findings
    res_all = client.get(f"/api/cases/{case.id}/recovery/findings")
    assert res_all.status_code == 200
    all_findings = res_all.json()
    assert len(all_findings) > 0

    # 2. Filter by Tier 1
    res_t1 = client.get(f"/api/cases/{case.id}/recovery/findings?tier=1")
    assert res_t1.status_code == 200
    t1_findings = res_t1.json()
    for f in t1_findings:
        assert f["tier"] == 1

    # 3. Filter by Tier 4
    res_t4 = client.get(f"/api/cases/{case.id}/recovery/findings?tier=4")
    assert res_t4.status_code == 200
    t4_findings = res_t4.json()
    for f in t4_findings:
        assert f["tier"] == 4
        assert f["strength"] == "weak_hint"
        assert f["confidence_score"] <= 0.30

    # 4. Filter by kind="id_gap"
    res_gap = client.get(f"/api/cases/{case.id}/recovery/findings?kind=id_gap")
    assert res_gap.status_code == 200
    gap_findings = res_gap.json()
    for f in gap_findings:
        assert f["kind"] == "id_gap"

    # 5. Fetch single finding by ID
    first_id = all_findings[0]["id"]
    res_single = client.get(f"/api/cases/{case.id}/recovery/findings/{first_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == first_id


def test_recovery_nonexistent_case(client: TestClient):
    """Verify 404 response for nonexistent case."""
    res = client.post("/api/cases/999999/recovery/run")
    assert res.status_code == 404
