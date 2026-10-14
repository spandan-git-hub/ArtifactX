"""
Forensic evidence integrity service (B5.3, R3, R4, R19).

Provides:
- ensure_integrity(evidence_id, db): recomputes hashes from stored bytes and verifies matching sha256 before stage execution.
- Typed exceptions and audit chain integration.
- LEGACY_UNVERIFIABLE protection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.models.models import Evidence
from backend.services.audit_service import AuditService
from backend.utils.hashing import compute_multi_hashes_bytes


class EvidenceIntegrityError(Exception):
    """Raised when an evidence file fails cryptographic integrity verification."""

    def __init__(self, message: str, evidence_id: int, expected: str, actual: str) -> None:
        super().__init__(message)
        self.evidence_id = evidence_id
        self.expected = expected
        self.actual = actual


class LegacyUnverifiableError(Exception):
    """Raised when an operation attempts to run on a legacy exhibit without stored content_bytes."""
    pass


@dataclass
class IntegrityResult:
    """Cryptographic verification assessment of evidence."""

    is_valid: bool
    state: str  # "VERIFIED_INTACT", "HASH_MISMATCH", "LEGACY_UNVERIFIABLE"
    expected_sha256: str
    actual_sha256: str
    hashes: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "state": self.state,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "hashes": self.hashes,
            "details": self.details,
        }


def ensure_integrity(
    evidence_id: int,
    db: Session,
    action_context: Optional[str] = None,
) -> IntegrityResult:
    """
    Verify the cryptographic integrity of an evidence item against its stored bytes (R3).
    MUST be called at the beginning of every forensic stage:
    (decryption, parsing, recovery, timeline, correlation, reporting).

    Raises:
    - LegacyUnverifiableError if evidence is flagged as LEGACY_UNVERIFIABLE.
    - EvidenceIntegrityError if recomputed SHA-256 differs from expected SHA-256.
    - FileNotFoundError if evidence does not exist in database.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise FileNotFoundError(f"Evidence exhibit {evidence_id} not found in database.")

    # 1. Handle legacy unverified rows (A5.3)
    if evidence.integrity_state == "LEGACY_UNVERIFIABLE" or evidence.content_bytes is None:
        raise LegacyUnverifiableError(
            f"Evidence {evidence_id} ({evidence.original_filename}) is marked LEGACY_UNVERIFIABLE: "
            "raw bytes were not retained in database storage."
        )

    # 2. Recompute cryptographic multi-hashes in memory
    hashes = compute_multi_hashes_bytes(evidence.content_bytes)
    actual_sha256 = hashes["sha256"]
    expected_sha256 = evidence.sha256

    # 3. Check for hash mismatch / tampering
    if actual_sha256.lower() != expected_sha256.lower():
        # Update integrity state
        evidence.integrity_state = "HASH_MISMATCH"
        db.commit()

        AuditService.append(
            db=db,
            action="INTEGRITY_FAILURE",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            details={
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "action_context": action_context or "stage_verification",
                "filename": evidence.original_filename,
            },
        )
        raise EvidenceIntegrityError(
            f"Evidence {evidence_id} integrity verification failed: expected {expected_sha256}, actual {actual_sha256}",
            evidence_id=evidence_id,
            expected=expected_sha256,
            actual=actual_sha256,
        )

    # 4. Verified intact: record audit entry
    AuditService.append(
        db=db,
        action="INTEGRITY_VERIFIED",
        actor="system",
        case_id=evidence.case_id,
        evidence_id=evidence.id,
        details={
            "sha256": actual_sha256,
            "action_context": action_context or "stage_verification",
            "filename": evidence.original_filename,
        },
    )

    return IntegrityResult(
        is_valid=True,
        state="VERIFIED_INTACT",
        expected_sha256=expected_sha256,
        actual_sha256=actual_sha256,
        hashes=hashes,
        details={"size_bytes": len(evidence.content_bytes)},
    )
