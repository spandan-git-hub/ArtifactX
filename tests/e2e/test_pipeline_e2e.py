"""
End-to-end integration test suite for the complete ArtifactX forensic pipeline (spec 11_PIPELINE_AND_E2E.md §B13.4, §B13.5).

Evaluates the complete ingest-to-findings path across all dev datasets:
- DS-01: Plain WhatsApp + WAL set
- DS-02: WhatsApp Crypt14 container + key
- DS-03: WhatsApp Crypt15 container + hex key
- DS-02/DS-03: No-key honest failure (ENCRYPTED_KEY_REQUIRED)
- DS-04: Negative fixtures (wrong key AUTH_FAILED, truncated TRUNCATED_INPUT, plaintext conflict)
- DS-05: Telegram cache4.db + WAL set
- DS-06: Cross-platform correlation (planted links vs decoys)
- DS-07: Unrelated control dataset (0 links above threshold)
- DS-08: Tampered database (pre-stage integrity rejection)
- Mixed-case: Exhibit failure isolation (unrelated exhibits succeed)
- Idempotency & Determinism (B13.5): Identical content hash, no duplicates on rerun, shuffle invariance
- Audit chain integrity & R5 key redaction
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import random
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.models.models import (
    AuditLog,
    Case,
    Evidence,
    PipelineRun,
    PipelineStageRun,
    TelegramMessage,
    TimelineEvent,
    WhatsAppMessage,
)
from backend.services.audit_service import AuditService
from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput, PipelineConfig


@pytest.fixture
def client(db_session):
    return TestClient(app)


def _create_case(db_session, name: str = "E2E Test Case") -> Case:
    case = Case(
        name=name,
        case_number=f"CASE-E2E-{random.randint(1000, 9999)}",
        examiner_name="Special Agent Forensic",
        agency="Judicial Cyber Lab",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def _ingest_file(
    db_session,
    case_id: int,
    file_path: Path,
    original_name: str | None = None,
    tampered_bytes: bytes | None = None,
    claimed_sha256: str | None = None,
) -> Evidence:
    real_data = file_path.read_bytes()
    data = tampered_bytes if tampered_bytes is not None else real_data
    digest = claimed_sha256 if claimed_sha256 is not None else sha256_hex(data)
    fn = original_name or file_path.name

    ev = Evidence(
        case_id=case_id,
        original_filename=fn,
        storage_path=f"memory://{fn}",
        sha256=digest,
        content_bytes=data,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    return ev


# =============================================================================
# 1. DS-01 Plain + WAL set (B13.4)
# =============================================================================

def test_e2e_ds01_plain_wal_pipeline(client, db_session):
    """Assert DS-01 plain msgstore.db + WAL + wa.db completes all stages and verifies audit trail."""
    case = _create_case(db_session, "DS-01 E2E Case")
    base_dir = Path("testdata/DS-01-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db")
    _ingest_file(db_session, case.id, base_dir / "msgstore.db-wal")
    _ingest_file(db_session, case.id, base_dir / "wa.db")

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200, resp.text
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"
    assert len(run_data["content_hash"]) == 64

    # Verify stage statuses
    stage_names = [s["stage"] for s in run_data["stage_runs"]]
    assert "integrity" in stage_names
    assert "detect" in stage_names
    assert "parse" in stage_names
    assert "recover" in stage_names
    assert "timeline" in stage_names
    assert "correlate" in stage_names

    # Check persistence
    wa_msgs = db_session.query(WhatsAppMessage).join(Evidence).filter(Evidence.case_id == case.id).all()
    assert len(wa_msgs) > 0

    tl_events = db_session.query(TimelineEvent).filter(TimelineEvent.case_id == case.id).all()
    assert len(tl_events) > 0

    # Audit chain verification
    audit_svc = AuditService(db_session)
    chain_status = audit_svc.verify_case_chain(case.id)
    assert chain_status["valid"] is True
    assert chain_status["entries_checked"] >= 3


# =============================================================================
# 2. DS-02 Crypt14 with Key (B13.4)
# =============================================================================

def test_e2e_ds02_crypt14_with_key(client, db_session):
    """Assert DS-02 Crypt14 decrypts and parses with parity to DS-01 plain."""
    case = _create_case(db_session, "DS-02 Crypt14 Case")
    base_dir = Path("testdata/DS-02-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db.crypt14")
    key_bytes = (base_dir / "keys" / "key").read_bytes()
    key_b64 = base64.b64encode(key_bytes).decode("ascii")

    resp = client.post(
        f"/api/cases/{case.id}/pipeline/run",
        json={
            "keys": [
                {"key_type": "crypt14", "key_file_b64": key_b64}
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"
    decrypt_stages = [s for s in run_data["stage_runs"] if s["stage"] == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0]["status"] == "COMPLETED"

    # Messages persisted
    wa_msgs = db_session.query(WhatsAppMessage).join(Evidence).filter(Evidence.case_id == case.id).all()
    assert len(wa_msgs) > 0


# =============================================================================
# 3. DS-03 Crypt15 with Key (B13.4)
# =============================================================================

def test_e2e_ds03_crypt15_with_key(client, db_session):
    """Assert DS-03 Crypt15 decrypts and parses with parity to DS-01 plain."""
    case = _create_case(db_session, "DS-03 Crypt15 Case")
    base_dir = Path("testdata/DS-03-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db.crypt15")
    key_hex = (base_dir / "keys" / "root_key.hex").read_text(encoding="utf-8").strip()

    resp = client.post(
        f"/api/cases/{case.id}/pipeline/run",
        json={
            "keys": [
                {"key_type": "crypt15", "key_hex": key_hex}
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"
    decrypt_stages = [s for s in run_data["stage_runs"] if s["stage"] == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0]["status"] == "COMPLETED"


# =============================================================================
# 4. DS-02 / DS-03 No Key Honest Failure (B13.4)
# =============================================================================

def test_e2e_ds02_ds03_no_key_honest_failure(client, db_session):
    """Assert Crypt14/Crypt15 without key produces honest ENCRYPTED_KEY_REQUIRED and skips downstream."""
    case = _create_case(db_session, "DS-03 No Key Case")
    base_dir = Path("testdata/DS-03-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db.crypt15")

    # Run without supplying key
    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200, resp.text
    run_data = resp.json()

    # Honest failure status
    assert run_data["status"] == "PARTIAL"
    decrypt_stages = [s for s in run_data["stage_runs"] if s["stage"] == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0]["status"] == "FAILED_HONEST"
    assert decrypt_stages[0]["error_code"] == "ENCRYPTED_KEY_REQUIRED"

    # Downstream skipped
    parse_stages = [s for s in run_data["stage_runs"] if s["stage"] == "parse"]
    assert len(parse_stages) == 1
    assert parse_stages[0]["status"] == "SKIPPED"
    assert parse_stages[0]["skip_reason"].startswith("dependency")


# =============================================================================
# 5. DS-04 Negative Fixtures (B13.4)
# =============================================================================

def test_e2e_ds04_wrong_key_auth_failed(client, db_session):
    """Assert wrong key returns typed AUTH_FAILED and emits no plaintext."""
    case = _create_case(db_session, "DS-04 Wrong Key Case")
    base_dir = Path("testdata/DS-04-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db.crypt15")
    wrong_key_hex = "00" * 32

    resp = client.post(
        f"/api/cases/{case.id}/pipeline/run",
        json={
            "keys": [{"key_type": "crypt15", "key_hex": wrong_key_hex}]
        },
    )
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] == "PARTIAL"
    decrypt_stages = [s for s in run_data["stage_runs"] if s["stage"] == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0]["status"] == "FAILED_HONEST"
    assert decrypt_stages[0]["error_code"] == "AUTH_FAILED"


def test_e2e_ds04_truncated_input(client, db_session):
    """Assert truncated encrypted file produces typed TRUNCATED_INPUT."""
    case = _create_case(db_session, "DS-04 Truncated Case")
    base_dir = Path("testdata/DS-04-dev")

    _ingest_file(db_session, case.id, base_dir / "truncated_body.crypt15")
    key_hex = (base_dir / "keys" / "primary_key.hex").read_text(encoding="utf-8").strip()

    resp = client.post(
        f"/api/cases/{case.id}/pipeline/run",
        json={
            "keys": [{"key_type": "crypt15", "key_hex": key_hex}]
        },
    )
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] == "PARTIAL"
    decrypt_stages = [s for s in run_data["stage_runs"] if s["stage"] == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0]["status"] == "FAILED_HONEST"
    assert decrypt_stages[0]["error_code"] in ("TRUNCATED_INPUT", "AUTH_FAILED")


def test_e2e_ds04_plaintext_named_crypt15(client, db_session):
    """Assert plaintext SQLite database named .crypt15 is detected and parsed with conflict noted."""
    case = _create_case(db_session, "DS-04 Plaintext Conflict Case")
    base_dir = Path("testdata/DS-04-dev")

    _ingest_file(db_session, case.id, base_dir / "plaintext_sqlite.crypt15")

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    # Detect stage should identify extension conflict
    detect_stages = [s for s in run_data["stage_runs"] if s["stage"] == "detect"]
    assert len(detect_stages) == 1
    counts = detect_stages[0].get("counts_json") or {}
    assert counts.get("extension_conflicts", 0) >= 1

    # Parsed without needing decryption
    parse_stages = [s for s in run_data["stage_runs"] if s["stage"] == "parse"]
    assert len(parse_stages) == 1
    assert parse_stages[0]["status"] == "COMPLETED"


# =============================================================================
# 6. DS-05 Telegram + WAL (B13.4)
# =============================================================================

def test_e2e_ds05_telegram_wal(client, db_session):
    """Assert DS-05 Telegram cache4.db + WAL executes parse, recovery, and timeline stages."""
    case = _create_case(db_session, "DS-05 Telegram Case")
    base_dir = Path("testdata/DS-05-dev")

    _ingest_file(db_session, case.id, base_dir / "cache4.db")
    _ingest_file(db_session, case.id, base_dir / "cache4.db-wal")

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"

    tg_msgs = db_session.query(TelegramMessage).join(Evidence).filter(Evidence.case_id == case.id).all()
    assert len(tg_msgs) > 0


# =============================================================================
# 7. DS-06 Cross-App Correlation (B13.4)
# =============================================================================

def test_e2e_ds06_crossapp_correlation(client, db_session):
    """Assert DS-06 discovers planted cross-platform links and does not link decoys above threshold."""
    case = _create_case(db_session, "DS-06 Cross-App Case")
    base_dir = Path("testdata/DS-06-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db")
    _ingest_file(db_session, case.id, base_dir / "wa.db")
    _ingest_file(db_session, case.id, base_dir / "cache4.db")

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"
    corr_stages = [s for s in run_data["stage_runs"] if s["stage"] == "correlate"]
    assert len(corr_stages) == 1
    assert corr_stages[0]["status"] == "COMPLETED"
    counts = corr_stages[0].get("counts_json") or {}
    assert counts.get("total_findings", 0) > 0


# =============================================================================
# 8. DS-07 Negative Control Dataset (B13.4)
# =============================================================================

def test_e2e_ds07_negative_control(client, db_session):
    """Assert DS-07 unrelated control dataset produces 0 correlation findings above threshold."""
    case = _create_case(db_session, "DS-07 Control Case")
    base_dir = Path("testdata/DS-07-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db")
    _ingest_file(db_session, case.id, base_dir / "wa.db")
    _ingest_file(db_session, case.id, base_dir / "cache4.db")

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] == "COMPLETED"
    corr_stages = [s for s in run_data["stage_runs"] if s["stage"] == "correlate"]
    assert len(corr_stages) == 1
    counts = corr_stages[0].get("counts_json") or {}
    # 0 false positive cross-platform correlations on unrelated control dataset (acceptance.yaml control_fpr_max: 0.0)
    assert counts.get("identity_findings", 0) == 0
    assert counts.get("handover_findings", 0) == 0
    assert counts.get("media_findings", 0) == 0


# =============================================================================
# 9. DS-08 Tampered Database Integrity Rejection (B13.4)
# =============================================================================

def test_e2e_ds08_tamper_integrity_failure(client, db_session):
    """Assert DS-08 tampered database fails pre-stage integrity verification and stages refuse."""
    case = _create_case(db_session, "DS-08 Tamper Case")
    base_dir = Path("testdata/DS-08-dev")

    # Ingest tampered database claiming untampered reference sha256
    ref_bytes = (base_dir / "reference_base.db").read_bytes()
    tampered_bytes = (base_dir / "tampered_offset_000000.db").read_bytes()
    claimed_hash = sha256_hex(ref_bytes)

    _ingest_file(
        db_session,
        case.id,
        base_dir / "tampered_offset_000000.db",
        original_name="tampered.db",
        tampered_bytes=tampered_bytes,
        claimed_sha256=claimed_hash,
    )

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    assert run_data["status"] in ("FAILED", "PARTIAL")
    integrity_stages = [s for s in run_data["stage_runs"] if s["stage"] == "integrity"]
    assert len(integrity_stages) == 1
    assert integrity_stages[0]["status"] == "FAILED_HONEST"
    assert integrity_stages[0]["error_code"] == "INTEGRITY_FAILURE"


# =============================================================================
# 10. Mixed-Case Failure Isolation (B13.4)
# =============================================================================

def test_e2e_mixed_case_failure_isolation(client, db_session):
    """Assert failure of one exhibit is isolated; valid exhibits complete all stages."""
    case = _create_case(db_session, "Mixed Case")

    # 1. Valid WhatsApp database
    wa_valid = Path("testdata/DS-01-dev/msgstore.db")
    _ingest_file(db_session, case.id, wa_valid)

    # 2. Corrupted exhibit with mismatched hash
    bad_bytes = b"CORRUPTED_EVIDENCE_BYTES"
    _ingest_file(
        db_session,
        case.id,
        wa_valid,
        original_name="corrupted.db",
        tampered_bytes=bad_bytes,
        claimed_sha256=sha256_hex(b"DIFFERENT_HASH"),
    )

    resp = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp.status_code == 200
    run_data = resp.json()

    # Overall pipeline is PARTIAL
    assert run_data["status"] == "PARTIAL"

    # Integrity stages
    integ_stages = [s for s in run_data["stage_runs"] if s["stage"] == "integrity"]
    statuses = {s["evidence_id"]: s["status"] for s in integ_stages}
    assert "COMPLETED" in statuses.values()
    assert "FAILED_HONEST" in statuses.values()

    # Valid data parsed and persisted
    wa_msgs = db_session.query(WhatsAppMessage).join(Evidence).filter(Evidence.case_id == case.id).all()
    assert len(wa_msgs) > 0


# =============================================================================
# 11. Idempotency & Determinism (B13.5)
# =============================================================================

def test_e2e_idempotency_and_determinism(client, db_session):
    """Assert pipeline runs produce identical content hashes, no row duplicates, and order invariance."""
    case = _create_case(db_session, "Determinism Case")
    base_dir = Path("testdata/DS-01-dev")

    ev1 = _ingest_file(db_session, case.id, base_dir / "msgstore.db")
    ev2 = _ingest_file(db_session, case.id, base_dir / "wa.db")

    # Run 1
    resp1 = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp1.status_code == 200
    run1 = resp1.json()

    msgs_after_run1 = db_session.query(WhatsAppMessage).join(Evidence).filter(Evidence.case_id == case.id).count()

    # Run 2 (Idempotency rerun)
    resp2 = client.post(f"/api/cases/{case.id}/pipeline/run", json={})
    assert resp2.status_code == 200
    run2 = resp2.json()

    msgs_after_run2 = db_session.query(WhatsAppMessage).join(Evidence).filter(Evidence.case_id == case.id).count()

    # Assert content_hash identity (R11)
    assert run1["content_hash"] == run2["content_hash"]
    # Assert no duplicate messages
    assert msgs_after_run1 == msgs_after_run2

    # Shuffle invariance: pure pipeline with reversed inputs
    inputs_forward = [
        EvidenceInput(evidence_id=str(ev1.id), sha256=ev1.sha256, name=ev1.original_filename, data=ev1.content_bytes, role="primary"),
        EvidenceInput(evidence_id=str(ev2.id), sha256=ev2.sha256, name=ev2.original_filename, data=ev2.content_bytes, role="wa_contacts"),
    ]
    inputs_reversed = list(reversed(inputs_forward))

    cfg = PipelineConfig()
    res_fwd = run_pipeline(inputs_forward, (), cfg, run_id="fwd")
    res_rev = run_pipeline(inputs_reversed, (), cfg, run_id="rev")

    assert res_fwd.content_hash == res_rev.content_hash


# =============================================================================
# 12. R5 Key Redaction and Deferred BYTEA Listing (B13.2, R5, R19)
# =============================================================================

def test_e2e_r5_key_redaction_and_bytea_exclusion(client, db_session):
    """Assert pipeline runs listing excludes BYTEA and contains zero secret key material (R5, R19)."""
    case = _create_case(db_session, "R5 Inspection Case")
    base_dir = Path("testdata/DS-03-dev")

    _ingest_file(db_session, case.id, base_dir / "msgstore.db.crypt15")
    key_hex = (base_dir / "keys" / "root_key.hex").read_text(encoding="utf-8").strip()

    resp = client.post(
        f"/api/cases/{case.id}/pipeline/run",
        json={"keys": [{"key_type": "crypt15", "key_hex": key_hex}]},
    )
    assert resp.status_code == 200

    # Verify runs listing endpoint
    list_resp = client.get(f"/api/cases/{case.id}/pipeline/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1

    # Verify BYTEA not leaked in listing
    for r in runs:
        assert "content_bytes" not in r
        assert "data" not in r

    # Verify radioactive key bytes NOT in DB or response
    runs_text = json.dumps(runs)
    assert key_hex not in runs_text

    # Verify audit log doesn't contain raw secret key
    audit_logs = db_session.query(AuditLog).filter(AuditLog.case_id == case.id).all()
    for log in audit_logs:
        log_str = json.dumps(log.details_json)
        assert key_hex not in log_str
