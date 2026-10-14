"""
Cryptographically hash-chained append-only audit service (B5.5, R5, R11).

Maintains a tamper-evident audit log where every entry is chained:
    entry_hash = SHA256(prev_hash || canonical_json({seq, ts_utc, actor, action, case_id, evidence_id, details}))
Genesis prev_hash is 64 zeros.

Enforces:
- R5 key redaction (keys, passphrases, tokens never written to audit details).
- Append-only locking (prevents concurrent forks).
- Complete chain verification walk (detects mutation, row deletion, and corruption).
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.models import AuditLog
from forensic.common.canonical import canonical_json

_CHAIN_MUTEX = threading.Lock()
GENESIS_HASH = "0" * 64

SENSITIVE_KEY_NAMES = {
    "key",
    "key_hex",
    "root_key",
    "password",
    "passphrase",
    "secret",
    "private_key",
    "auth_key",
    "token",
    "key_bytes",
    "server_salt",
}


def redact_sensitive_keys(data: Any) -> Any:
    """
    Recursively redact cryptographic keys, passphrases, and secrets (R5).
    Replaces sensitive values with a safe truncated fingerprint or placeholder.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEY_NAMES):
                if isinstance(v, (str, bytes)):
                    val_bytes = v.encode("utf-8") if isinstance(v, str) else v
                    # Provide first 8 hex characters of SHA-256 fingerprint if applicable
                    fp = hashlib.sha256(val_bytes).hexdigest()[:8]
                    sanitized[k] = f"[REDACTED_KEY_FINGERPRINT_{fp}]"
                else:
                    sanitized[k] = "[REDACTED_SENSITIVE_DATA]"
            else:
                sanitized[k] = redact_sensitive_keys(v)
        return sanitized
    elif isinstance(data, (list, tuple)):
        return [redact_sensitive_keys(item) for item in data]
    return data


@dataclass
class AuditChainVerificationResult:
    """Result of walking the audit hash chain."""

    ok: bool
    checked: int
    first_bad_seq: Optional[int] = None
    head_hash: Optional[str] = None
    error_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "first_bad_seq": self.first_bad_seq,
            "head_hash": self.head_hash,
            "error_detail": self.error_detail,
        }


class AuditService:
    """Service for appending to and verifying the hash-chained audit log."""

    @classmethod
    def append(
        cls,
        db: Session,
        action: str,
        actor: str = "system",
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Append an entry to the hash-chained audit log with chain-head locking.
        Guarantees strictly monotonic seq and continuous cryptographic hash chain.
        """
        sanitized_details = redact_sensitive_keys(details or {})
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        with _CHAIN_MUTEX:
            # Query the latest entry to link the hash chain
            last_entry = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
            if last_entry is None:
                prev_hash = GENESIS_HASH
                next_seq = 1
            else:
                prev_hash = last_entry.entry_hash
                next_seq = last_entry.seq + 1

            # Canonical payload per spec B5.5
            canonical_payload = {
                "action": action,
                "actor": actor,
                "case_id": case_id,
                "details": sanitized_details,
                "evidence_id": evidence_id,
                "seq": next_seq,
                "ts_utc": now_utc,
            }
            canonical_str = canonical_json(canonical_payload)
            hash_input = prev_hash.encode("utf-8") + canonical_str.encode("utf-8")
            entry_hash = hashlib.sha256(hash_input).hexdigest()

            log_entry = AuditLog(
                seq=next_seq,
                ts_utc=now_utc,
                actor=actor,
                action=action,
                case_id=case_id,
                evidence_id=evidence_id,
                details_json=sanitized_details,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry

    @classmethod
    def verify_audit_chain(
        cls,
        db: Session,
        case_id: Optional[int] = None,
    ) -> AuditChainVerificationResult:
        """
        Verify the integrity of the audit hash chain from genesis to head.
        Recomputes hashes and verifies unbroken link for every entry.
        """
        query = db.query(AuditLog).order_by(AuditLog.seq.asc())
        entries: List[AuditLog] = query.all()

        if not entries:
            return AuditChainVerificationResult(
                ok=True,
                checked=0,
                head_hash=GENESIS_HASH,
            )

        expected_prev_hash = GENESIS_HASH
        expected_seq = 1

        for entry in entries:
            # Check seq continuity
            if entry.seq != expected_seq:
                return AuditChainVerificationResult(
                    ok=False,
                    checked=expected_seq - 1,
                    first_bad_seq=entry.seq,
                    head_hash=expected_prev_hash,
                    error_detail=f"Sequence discontinuity: expected seq {expected_seq}, got {entry.seq}",
                )

            # Check previous hash pointer
            if entry.prev_hash != expected_prev_hash:
                return AuditChainVerificationResult(
                    ok=False,
                    checked=entry.seq - 1,
                    first_bad_seq=entry.seq,
                    head_hash=expected_prev_hash,
                    error_detail=f"Hash chain broken at seq {entry.seq}: expected prev_hash {expected_prev_hash}, got {entry.prev_hash}",
                )

            # Recompute entry hash
            canonical_payload = {
                "action": entry.action,
                "actor": entry.actor,
                "case_id": entry.case_id,
                "details": entry.details_json,
                "evidence_id": entry.evidence_id,
                "seq": entry.seq,
                "ts_utc": entry.ts_utc,
            }
            try:
                canonical_str = canonical_json(canonical_payload)
            except Exception as exc:
                return AuditChainVerificationResult(
                    ok=False,
                    checked=entry.seq - 1,
                    first_bad_seq=entry.seq,
                    head_hash=expected_prev_hash,
                    error_detail=f"Canonical serialization failed at seq {entry.seq}: {exc}",
                )

            hash_input = entry.prev_hash.encode("utf-8") + canonical_str.encode("utf-8")
            recomputed_hash = hashlib.sha256(hash_input).hexdigest()

            if recomputed_hash != entry.entry_hash:
                return AuditChainVerificationResult(
                    ok=False,
                    checked=entry.seq - 1,
                    first_bad_seq=entry.seq,
                    head_hash=expected_prev_hash,
                    error_detail=f"Entry hash mismatch at seq {entry.seq}: stored {entry.entry_hash}, recomputed {recomputed_hash}",
                )

            expected_prev_hash = entry.entry_hash
            expected_seq += 1

        return AuditChainVerificationResult(
            ok=True,
            checked=len(entries),
            first_bad_seq=None,
            head_hash=expected_prev_hash,
        )
