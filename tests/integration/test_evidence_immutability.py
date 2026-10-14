"""
Integration tests for Evidence and AuditLog immutability guarantees (B5.3, R3, DEC-010).
Tests both ORM event hooks and database-level SQL triggers.
"""

import hashlib
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError

from backend.models.models import (
    AuditLog,
    Case,
    Evidence,
    EvidenceFile,
    EvidenceImmutableError,
    AuditLogImmutableError,
)
from backend.services.integrity_service import (
    ensure_integrity,
    EvidenceIntegrityError,
    LegacyUnverifiableError,
)
from backend.services.audit_service import AuditService


@pytest.fixture
def test_case(db_session: Session) -> Case:
    case = Case(name="Immutability Test Case", description="Testing B5.3 immutability")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def test_evidence_orm_immutability(db_session: Session, test_case: Case):
    """Assert ORM blocks updating content_bytes or sha256 on Evidence once populated."""
    payload = b"ORIGINAL_EVIDENCE_BYTES_FOR_IMMUTABILITY_TEST"
    digest = hashlib.sha256(payload).hexdigest()

    evidence = Evidence(
        case_id=test_case.id,
        original_filename="evidence.bin",
        storage_path="db://evidence/evidence.bin",
        content_bytes=payload,
        sha256=digest,
        integrity_state="VERIFIED_INTACT",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # 1. Attempting to alter content_bytes via ORM must raise EvidenceImmutableError
    evidence.content_bytes = b"TAMPERED_EVIDENCE_BYTES"
    with pytest.raises(EvidenceImmutableError, match="strictly immutable"):
        db_session.commit()
    db_session.rollback()

    # 2. Attempting to alter sha256 via ORM must raise EvidenceImmutableError
    db_session.refresh(evidence)
    evidence.sha256 = "f" * 64
    with pytest.raises(EvidenceImmutableError, match="strictly immutable"):
        db_session.commit()
    db_session.rollback()

    # 3. Altering mutable metadata (e.g. integrity_state, status) must succeed
    db_session.refresh(evidence)
    evidence.integrity_state = "ANALYSIS_IN_PROGRESS"
    db_session.commit()
    db_session.refresh(evidence)
    assert evidence.integrity_state == "ANALYSIS_IN_PROGRESS"


def test_evidence_file_orm_immutability(db_session: Session, test_case: Case):
    """Assert ORM blocks updating content_bytes or sha256 on EvidenceFile once populated."""
    evidence = Evidence(
        case_id=test_case.id,
        original_filename="parent.zip",
        storage_path="db://evidence/parent.zip",
        content_bytes=b"parentdata",
        sha256=hashlib.sha256(b"parentdata").hexdigest(),
    )
    db_session.add(evidence)
    db_session.commit()

    child_bytes = b"CHILD_FILE_BYTES"
    child_sha = hashlib.sha256(child_bytes).hexdigest()
    ev_file = EvidenceFile(
        evidence_id=evidence.id,
        relative_path="msgstore.db",
        file_size=len(child_bytes),
        content_bytes=child_bytes,
        sha256=child_sha,
    )
    db_session.add(ev_file)
    db_session.commit()
    db_session.refresh(ev_file)

    ev_file.content_bytes = b"TAMPERED_CHILD_BYTES"
    with pytest.raises(EvidenceImmutableError, match="strictly immutable"):
        db_session.commit()
    db_session.rollback()


def test_audit_log_orm_immutability(db_session: Session, test_case: Case):
    """Assert ORM blocks updating or deleting AuditLog entries."""
    entry = AuditService.append(
        db=db_session,
        action="TEST_ACTION",
        case_id=test_case.id,
        details={"info": "immutability_test"},
    )

    # 1. Update blocked
    entry.action = "TAMPERED_ACTION"
    with pytest.raises(AuditLogImmutableError, match="append-only and strictly immutable"):
        db_session.commit()
    db_session.rollback()

    # 2. Delete blocked
    entry_refetched = db_session.query(AuditLog).filter(AuditLog.seq == entry.seq).first()
    assert entry_refetched is not None
    db_session.delete(entry_refetched)
    with pytest.raises(AuditLogImmutableError, match="cannot be deleted"):
        db_session.commit()
    db_session.rollback()


def test_database_triggers_immutability(db_session: Session, test_case: Case):
    """Assert DB triggers enforce immutability even on raw SQL statements."""
    dialect = db_session.bind.dialect.name
    if dialect != "sqlite":
        pytest.skip("Test specifically verifies SQLite trigger DDL behavior")

    # Install the SQLite triggers directly for the in-memory test DB
    db_session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS prevent_evidence_content_update
        BEFORE UPDATE OF content_bytes, sha256 ON evidence
        FOR EACH ROW
        WHEN OLD.content_bytes IS NOT NULL
        BEGIN
            SELECT RAISE(ABORT, 'Evidence content_bytes and sha256 are immutable');
        END;
    """))
    db_session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
        BEFORE UPDATE ON audit_log
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'audit_log is append-only and immutable');
        END;
    """))
    db_session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
        BEFORE DELETE ON audit_log
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'audit_log entries cannot be deleted');
        END;
    """))
    db_session.commit()

    # Create evidence row
    payload = b"TEST_PAYLOAD"
    ev = Evidence(
        case_id=test_case.id,
        original_filename="test.bin",
        storage_path="db://evidence/test.bin",
        content_bytes=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    db_session.add(ev)
    db_session.commit()

    # Raw SQL UPDATE on evidence content_bytes must trigger RAISE(ABORT)
    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text("UPDATE evidence SET content_bytes = :tampered WHERE id = :id"),
            {"tampered": b"NEW_DATA", "id": ev.id},
        )
        db_session.commit()
    db_session.rollback()

    # Create audit log entry
    audit_entry = AuditService.append(db=db_session, action="STEP_TRIGGER", case_id=test_case.id)

    # Raw SQL UPDATE on audit_log must trigger RAISE(ABORT)
    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text("UPDATE audit_log SET action = 'HACKED' WHERE seq = :seq"),
            {"seq": audit_entry.seq},
        )
        db_session.commit()
    db_session.rollback()

    # Raw SQL DELETE on audit_log must trigger RAISE(ABORT)
    with pytest.raises(DBAPIError, match="cannot be deleted"):
        db_session.execute(
            text("DELETE FROM audit_log WHERE seq = :seq"),
            {"seq": audit_entry.seq},
        )
        db_session.commit()
    db_session.rollback()


def test_ensure_integrity_success_and_audit(db_session: Session, test_case: Case):
    """Assert ensure_integrity validates intact bytes, returns result, and records audit entry."""
    data = b"REAL_VALID_FORENSIC_BYTES_XYZ"
    sha = hashlib.sha256(data).hexdigest()
    ev = Evidence(
        case_id=test_case.id,
        original_filename="chat.db",
        storage_path="db://evidence/chat.db",
        content_bytes=data,
        sha256=sha,
    )
    db_session.add(ev)
    db_session.commit()

    result = ensure_integrity(ev.id, db_session, action_context="parsing_stage")
    assert result.is_valid is True
    assert result.state == "VERIFIED_INTACT"
    assert result.actual_sha256 == sha
    assert result.hashes["sha256"] == sha
    assert "sha512" in result.hashes
    assert "md5" in result.hashes
    assert "sha1" in result.hashes

    # Verify audit log entry
    latest_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.evidence_id == ev.id, AuditLog.action == "INTEGRITY_VERIFIED")
        .first()
    )
    assert latest_audit is not None
    assert latest_audit.details_json["action_context"] == "parsing_stage"
    assert latest_audit.details_json["sha256"] == sha


def test_ensure_integrity_mismatch_and_audit(db_session: Session, test_case: Case):
    """Assert ensure_integrity detects hash mismatch, flags row, and records audit failure."""
    data = b"DATA_BEFORE_CORRUPTION"
    claimed_sha = hashlib.sha256(b"DIFFERENT_ORIGINAL_DATA").hexdigest()
    ev = Evidence(
        case_id=test_case.id,
        original_filename="corrupted.db",
        storage_path="db://evidence/corrupted.db",
        content_bytes=data,
        sha256=claimed_sha,  # mismatch on purpose
    )
    db_session.add(ev)
    db_session.commit()

    with pytest.raises(EvidenceIntegrityError) as exc_info:
        ensure_integrity(ev.id, db_session, action_context="recovery_stage")

    assert exc_info.value.evidence_id == ev.id
    assert exc_info.value.expected == claimed_sha

    db_session.refresh(ev)
    assert ev.integrity_state == "HASH_MISMATCH"

    # Verify audit failure entry
    failure_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.evidence_id == ev.id, AuditLog.action == "INTEGRITY_FAILURE")
        .first()
    )
    assert failure_audit is not None
    assert failure_audit.details_json["expected_sha256"] == claimed_sha
    assert failure_audit.details_json["actual_sha256"] == hashlib.sha256(data).hexdigest()


def test_ensure_integrity_legacy_unverifiable(db_session: Session, test_case: Case):
    """Assert legacy rows with content_bytes=NULL raise LegacyUnverifiableError (A5.3)."""
    ev = Evidence(
        case_id=test_case.id,
        original_filename="legacy.db",
        content_bytes=None,
        storage_path="/legacy/disk/path/legacy.db",
        sha256="abcd" * 16,
        integrity_state="LEGACY_UNVERIFIABLE",
    )
    db_session.add(ev)
    db_session.commit()

    with pytest.raises(LegacyUnverifiableError, match="LEGACY_UNVERIFIABLE"):
        ensure_integrity(ev.id, db_session, action_context="timeline_stage")


def test_ensure_integrity_missing_evidence(db_session: Session):
    """Assert non-existent evidence_id raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found in database"):
        ensure_integrity(999999, db_session)
