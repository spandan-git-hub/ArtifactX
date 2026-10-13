"""Integration tests for legacy unverifiable row handling and zero-disk verify-hashes (A5.2, A5.3)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.models.models import Case, Evidence, EvidenceFile
from backend.utils.hashing import compute_multi_hashes_bytes


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
def test_legacy_row_returns_legacy_unverifiable(client_and_db):
    """Verify that legacy rows with NULL content_bytes return LEGACY_UNVERIFIABLE, never VERIFIED_INTACT (A5.3)."""
    client, db = client_and_db

    # Create case
    case = Case(name="Legacy Case", investigator="Investigator 1")
    db.add(case)
    db.commit()
    db.refresh(case)

    # Insert legacy evidence row (storage_path set, content_bytes NULL, integrity_state='LEGACY_UNVERIFIABLE')
    legacy_ev = Evidence(
        case_id=case.id,
        original_filename="legacy_msgstore.db",
        storage_path="uploads/legacy_msgstore.db",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        content_type="application/octet-stream",
        evidence_type="file",
        content_bytes=None,
        integrity_state="LEGACY_UNVERIFIABLE",
    )
    db.add(legacy_ev)
    db.commit()
    db.refresh(legacy_ev)

    # Post to verify-hashes
    resp = client.post(f"/api/evidence/{legacy_ev.id}/verify-hashes")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["verification_status"] == "LEGACY_UNVERIFIABLE"
    assert data["is_valid"] is False
    assert data["integrity_state"] == "LEGACY_UNVERIFIABLE"
    assert data["main_file"]["actual_sha256"] == "LEGACY_UNVERIFIABLE"
    assert data["main_file"]["is_intact"] is False


@pytest.mark.integration
def test_intact_evidence_returns_verified_intact(client_and_db):
    """Verify that evidence with intact in-memory bytes returns VERIFIED_INTACT."""
    client, db = client_and_db

    case = Case(name="Intact Case", investigator="Investigator 2")
    db.add(case)
    db.commit()
    db.refresh(case)

    sample_bytes = b"SQLite format 3\x00-valid-bytes-for-testing"
    hashes = compute_multi_hashes_bytes(sample_bytes)

    intact_ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db",
        storage_path=f"db://evidence/{intact_ev_name if 'intact_ev_name' in locals() else 'test_msgstore.db'}",
        sha256=hashes["sha256"],
        content_type="application/octet-stream",
        evidence_type="file",
        metadata_={"md5": hashes["md5"], "sha1": hashes["sha1"]},
        content_bytes=sample_bytes,
        integrity_state="OK",
    )
    db.add(intact_ev)
    db.commit()
    db.refresh(intact_ev)

    resp = client.post(f"/api/evidence/{intact_ev.id}/verify-hashes")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["verification_status"] == "VERIFIED_INTACT"
    assert data["is_valid"] is True
    assert data["integrity_state"] == "OK"
    assert data["main_file"]["actual_sha256"] == hashes["sha256"]
    assert data["main_file"]["is_intact"] is True


@pytest.mark.integration
def test_tampered_evidence_returns_hash_mismatch(client_and_db):
    """Verify that tampered in-memory bytes return HASH_MISMATCH."""
    client, db = client_and_db

    case = Case(name="Tampered Case", investigator="Investigator 3")
    db.add(case)
    db.commit()
    db.refresh(case)

    real_bytes = b"Original-Evidence-Content"
    hashes = compute_multi_hashes_bytes(real_bytes)

    # Store altered bytes
    altered_bytes = b"Altered-Evidence-Content"
    tampered_ev = Evidence(
        case_id=case.id,
        original_filename="tampered.db",
        storage_path="db://evidence/tampered.db",
        sha256=hashes["sha256"],
        content_type="application/octet-stream",
        evidence_type="file",
        metadata_={"md5": hashes["md5"], "sha1": hashes["sha1"]},
        content_bytes=altered_bytes,
        integrity_state="OK",
    )
    db.add(tampered_ev)
    db.commit()
    db.refresh(tampered_ev)

    resp = client.post(f"/api/evidence/{tampered_ev.id}/verify-hashes")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["verification_status"] == "HASH_MISMATCH"
    assert data["is_valid"] is False


@pytest.mark.integration
def test_case_workspace_exposes_legacy_unverifiable_count(client_and_db):
    """Verify that case workspace and evidence summaries expose legacy_unverifiable_count (A5.3)."""
    client, db = client_and_db

    case = Case(name="Summary Test Case", investigator="Investigator 4")
    db.add(case)
    db.commit()
    db.refresh(case)

    # 1 intact evidence + 2 legacy evidence rows
    sample_bytes = b"dummy content"
    hashes = compute_multi_hashes_bytes(sample_bytes)

    ev_ok = Evidence(
        case_id=case.id,
        original_filename="ok.db",
        storage_path="db://evidence/ok.db",
        sha256=hashes["sha256"],
        content_bytes=sample_bytes,
        integrity_state="OK",
    )
    ev_leg1 = Evidence(
        case_id=case.id,
        original_filename="legacy1.db",
        storage_path="uploads/legacy1.db",
        sha256="0" * 64,
        content_bytes=None,
        integrity_state="LEGACY_UNVERIFIABLE",
    )
    ev_leg2 = Evidence(
        case_id=case.id,
        original_filename="legacy2.db",
        storage_path="uploads/legacy2.db",
        sha256="1" * 64,
        content_bytes=None,
        integrity_state="LEGACY_UNVERIFIABLE",
    )
    db.add_all([ev_ok, ev_leg1, ev_leg2])
    db.commit()

    # Check case workspace
    resp = client.get(f"/api/cases/{case.id}/workspace")
    assert resp.status_code == 200, resp.text
    workspace = resp.json()

    assert workspace["summary_counts"]["evidence_count"] == 3
    assert workspace["summary_counts"]["legacy_unverifiable_count"] == 2

    # Check active_evidence items contain integrity_state
    states = {e["original_filename"]: e["integrity_state"] for e in workspace["active_evidence"]}
    assert states["ok.db"] == "OK"
    assert states["legacy1.db"] == "LEGACY_UNVERIFIABLE"
    assert states["legacy2.db"] == "LEGACY_UNVERIFIABLE"

    # Check evidence summary report endpoint
    rep_resp = client.get(f"/api/cases/{case.id}/reports/summary")
    assert rep_resp.status_code == 200, rep_resp.text
    rep_summary = rep_resp.json()
    assert rep_summary["legacy_unverifiable_count"] == 2


@pytest.mark.integration
def test_get_evidence_file_legacy_row_returns_404(client_and_db):
    """Verify that get_evidence_file returns 404 for legacy rows lacking in-memory bytes."""
    client, db = client_and_db

    case = Case(name="File Download Case", investigator="Investigator 5")
    db.add(case)
    db.commit()
    db.refresh(case)

    ev = Evidence(
        case_id=case.id,
        original_filename="archive.zip",
        storage_path="uploads/archive.zip",
        sha256="a" * 64,
        evidence_type="zip",
        content_bytes=None,
        integrity_state="LEGACY_UNVERIFIABLE",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    ef = EvidenceFile(
        evidence_id=ev.id,
        relative_path="inside/file.txt",
        sha256="b" * 64,
        file_size=10,
        content_bytes=None,
    )
    db.add(ef)
    db.commit()
    db.refresh(ef)

    resp = client.get(f"/api/evidence/{ev.id}/files/{ef.id}")
    assert resp.status_code == 404
    assert "legacy unverifiable" in resp.json()["detail"].lower()
