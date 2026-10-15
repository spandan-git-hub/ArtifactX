"""
Tier 1: Explicit Deletion and Modification Evidence (spec B10.1, master.md R7, R8, R20).
Extracts deterministic deletion and edit markers from application schema structures.
"""

from __future__ import annotations

import binascii
from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.common.contracts import Provenance
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.common.sqlite_open import open_sqlite_ro
from forensic.recovery.models import RecoveryFinding


def extract_tier1_whatsapp(
    db_bytes: bytes,
    evidence_id: str,
    evidence_sha256: str,
) -> List[RecoveryFinding]:
    """
    Extract Tier 1 WhatsApp revocations ('Delete for Everyone') and edit markers.
    Inspects message_revoked, message_edit_info, and cross-references message_quoted
    for candidate snapshot text.
    """
    findings: List[RecoveryFinding] = []
    conn = open_sqlite_ro(db_bytes)
    cursor = conn.cursor()

    # Discover tables present
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}

    # 1. Build index of quoted messages by key_id for candidate original text recovery
    quoted_by_key: Dict[str, Dict[str, Any]] = {}
    if "message_quoted" in tables:
        cursor.execute(
            """
            SELECT message_row_id, key_id, parent_key_id, text_data, timestamp
            FROM message_quoted
            WHERE text_data IS NOT NULL AND text_data != ''
            """
        )
        for q_row in cursor.fetchall():
            q_row_id, q_key, q_parent_key, q_text, q_ts = q_row
            entry = {
                "quoted_row_id": q_row_id,
                "text": q_text,
                "timestamp": q_ts,
            }
            if q_key:
                quoted_by_key[q_key] = entry
            if q_parent_key:
                quoted_by_key[q_parent_key] = entry

    # 2. Extract revocations from message_revoked
    if "message_revoked" in tables:
        has_admin = False
        try:
            cursor.execute("PRAGMA table_info(message_revoked)")
            rev_cols = {r[1] for r in cursor.fetchall()}
            has_admin = "admin_jid_row_id" in rev_cols
        except Exception:
            pass

        query = (
            "SELECT message_row_id, revoked_key_id, admin_jid_row_id FROM message_revoked"
            if has_admin
            else "SELECT message_row_id, revoked_key_id, NULL FROM message_revoked"
        )

        cursor.execute(query)
        for r_row in cursor.fetchall():
            r_msg_id, rev_key, admin_jid_id = r_row
            rev_key_str = rev_key or ""

            # Check if a quoted message snapshot exists
            quoted_entry = quoted_by_key.get(rev_key_str)
            candidate_text: Optional[str] = None
            limitations_list: List[str] = [
                "does not prove whether recipient read original message before revocation",
            ]

            if quoted_entry:
                candidate_text = quoted_entry["text"]
                strength = "moderate"
                limitations_list.append(
                    "candidate text is from a quoted message snapshot which may differ from the actual deleted message"
                )
            else:
                strength = "deterministic"
                limitations_list.append("original message body is not preserved in live database row")

            fid = deterministic_finding_id(
                method="tier1_wa_revocation",
                evidence_sha256=evidence_sha256,
                source_table="message_revoked",
                row_or_offset=r_msg_id,
                key_facts={"revoked_key_id": rev_key_str},
            )

            raw_preview = f"REVOKED key_id={rev_key_str} row_id={r_msg_id}"
            if candidate_text:
                raw_preview += f"\nCandidate Quoted Text: {candidate_text[:80]}"

            findings.append(
                RecoveryFinding(
                    finding_id=fid,
                    confidence_score=1.0 if not candidate_text else 0.85,
                    strength=strength,
                    limitations=tuple(limitations_list),
                    provenance=Provenance(
                        evidence_id=evidence_id,
                        evidence_sha256=evidence_sha256,
                        source_table="message_revoked",
                        row_id=r_msg_id,
                        method="tier1_wa_revocation",
                    ),
                    tier=1,
                    kind="revocation",
                    validation_status="FULL_RECORD_VALID",
                    table_name="message_revoked",
                    row_id=r_msg_id,
                    view="main_view",
                    recovered_fields={
                        "message_row_id": r_msg_id,
                        "key_id": rev_key_str,
                        "admin_jid_id": admin_jid_id,
                        "candidate_text": candidate_text,
                    },
                    candidate_original_text=candidate_text,
                    raw_payload_hash=sha256_hex(rev_key_str.encode("utf-8")),
                    raw_payload_preview=raw_preview,
                )
            )

    # 3. Extract edit history from message_edit_info
    if "message_edit_info" in tables:
        cursor.execute(
            """
            SELECT message_row_id, original_key_id, edit_type, original_timestamp
            FROM message_edit_info
            """
        )
        for e_row in cursor.fetchall():
            e_msg_id, orig_key, edit_type, orig_ts = e_row
            orig_key_str = orig_key or ""

            quoted_entry = quoted_by_key.get(orig_key_str)
            candidate_text = quoted_entry["text"] if quoted_entry else None
            limitations_list = [
                "prior text is not present in live database row",
                "intermediate edit versions require WAL or carved cell recovery",
            ]

            if candidate_text:
                strength = "moderate"
                limitations_list.append(
                    "candidate text is from a quoted message snapshot which may differ from the original message"
                )
            else:
                strength = "deterministic"

            fid = deterministic_finding_id(
                method="tier1_wa_edit",
                evidence_sha256=evidence_sha256,
                source_table="message_edit_info",
                row_or_offset=e_msg_id,
                key_facts={"original_key_id": orig_key_str, "orig_ts": orig_ts or 0},
            )

            raw_preview = f"EDIT original_key_id={orig_key_str} row_id={e_msg_id} orig_ts={orig_ts}"
            if candidate_text:
                raw_preview += f"\nCandidate Quoted Text: {candidate_text[:80]}"

            findings.append(
                RecoveryFinding(
                    finding_id=fid,
                    confidence_score=1.0 if not candidate_text else 0.85,
                    strength=strength,
                    limitations=tuple(limitations_list),
                    provenance=Provenance(
                        evidence_id=evidence_id,
                        evidence_sha256=evidence_sha256,
                        source_table="message_edit_info",
                        row_id=e_msg_id,
                        method="tier1_wa_edit",
                    ),
                    tier=1,
                    kind="edit",
                    validation_status="FULL_RECORD_VALID",
                    table_name="message_edit_info",
                    row_id=e_msg_id,
                    view="main_view",
                    recovered_fields={
                        "message_row_id": e_msg_id,
                        "key_id": orig_key_str,
                        "original_timestamp": orig_ts,
                        "edit_type": edit_type,
                        "candidate_text": candidate_text,
                    },
                    candidate_original_text=candidate_text,
                    raw_payload_hash=sha256_hex(orig_key_str.encode("utf-8")),
                    raw_payload_preview=raw_preview,
                )
            )

    conn.close()
    return findings


def extract_tier1_telegram(
    db_bytes: bytes,
    evidence_id: str,
    evidence_sha256: str,
) -> List[RecoveryFinding]:
    """
    Tier 1 Telegram extraction.
    Per spec B10.1 and R20: Only emit Tier 1 findings for markers whose semantics
    were verified against primary sources. No synthetic or guessed markers emitted.
    """
    # Telegram cache4.db schema does not maintain an un-purged deletion table in verified Android releases.
    # Return empty list per R7 / R20.
    return []
