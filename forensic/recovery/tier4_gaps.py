"""
Tier 4: Primary Key ID-Gap Indicator (spec B10.4, master.md R7, R8, R10).

Demoted heuristic indicator of sequence gaps in autoincrement keys / message IDs.
Guarantees:
- Capped confidence_score <= 0.30
- Explicit 'weak_hint' strength label
- Mandatory non-deletion limitation disclosures
- Suppressed when stronger tiers (Tier 1, 2, 3) already explain the missing IDs
- Stored as factual gap bounds; never presented as confirmed deleted messages
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.common.contracts import Provenance
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.common.sqlite_open import open_sqlite_ro
from forensic.recovery.models import RecoveryFinding


def detect_tier4_gaps(
    db_bytes: bytes,
    app_hint: str = "whatsapp",
    evidence_id: str = "0",
    evidence_sha256: str = "",
    stronger_tier_rowids: Optional[Set[int]] = None,
) -> List[RecoveryFinding]:
    """
    Detect autoincrement / sequence ID gaps across chats in the active database view.
    Suppresses gaps if stronger tiers already account for the missing IDs.
    """
    findings: List[RecoveryFinding] = []
    explained_ids = stronger_tier_rowids or set()

    conn = open_sqlite_ro(db_bytes)
    cursor = conn.cursor()

    # Discover tables present
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}

    is_tg = "telegram" in app_hint.lower() or "tg" in app_hint.lower() or "messages_v2" in tables

    if is_tg and "messages_v2" in tables:
        # Detect table-level primary key sequence gaps in Telegram messages_v2 (mid)
        cursor.execute("SELECT mid FROM messages_v2 WHERE mid > 0 ORDER BY mid ASC")
        mids = [r[0] for r in cursor.fetchall()]

        for i in range(len(mids) - 1):
            prev_id = mids[i]
            curr_id = mids[i + 1]
            gap_size = curr_id - prev_id - 1

            if gap_size > 0:
                gap_range = range(prev_id + 1, curr_id)
                # If any ID in the gap is already explained by stronger tiers (Tier 1-3), suppress
                if any(gid in explained_ids for gid in gap_range):
                    continue

                fid = deterministic_finding_id(
                    method="tier4_tg_id_gap",
                    evidence_sha256=evidence_sha256,
                    source_table="messages_v2",
                    row_or_offset=prev_id + 1,
                    key_facts={"gap_start": prev_id + 1, "gap_end": curr_id - 1},
                )

                findings.append(
                    RecoveryFinding(
                        finding_id=fid,
                        confidence_score=0.25,  # Strictly capped <= 0.30 (B10.4)
                        strength="weak_hint",
                        limitations=(
                            "ID gaps can arise without deletion (e.g. rolled-back transactions, system/ephemeral messages, sequence jumping)",
                            "indicator only: does not prove that messages existed or were deleted",
                        ),
                        provenance=Provenance(
                            evidence_id=evidence_id,
                            evidence_sha256=evidence_sha256,
                            source_table="messages_v2",
                            row_id=prev_id + 1,
                            method="tier4_tg_id_gap",
                        ),
                        tier=4,
                        kind="id_gap",
                        validation_status="PARTIAL",
                        table_name="messages_v2",
                        row_id=prev_id + 1,
                        view="main_view",
                        recovered_fields={
                            "gap_start": prev_id + 1,
                            "gap_end": curr_id - 1,
                            "missing_count": gap_size,
                        },
                        raw_payload_hash=sha256_hex(f"gap:tg:{prev_id+1}:{curr_id-1}".encode("utf-8")),
                        raw_payload_preview=f"TG ID GAP range=[{prev_id + 1}..{curr_id - 1}] ({gap_size} missing IDs)",
                    )
                )

    elif "message" in tables or "messages" in tables:
        target_table = "message" if "message" in tables else "messages"
        cursor.execute(f"SELECT _id FROM {target_table} WHERE _id > 0 ORDER BY _id ASC")
        ids = [r[0] for r in cursor.fetchall()]

        for i in range(len(ids) - 1):
            prev_id = ids[i]
            curr_id = ids[i + 1]
            gap_size = curr_id - prev_id - 1

            if gap_size > 0:
                gap_range = range(prev_id + 1, curr_id)
                # If any ID in the gap is already explained by stronger tiers (Tier 1-3), suppress
                if any(gid in explained_ids for gid in gap_range):
                    continue

                fid = deterministic_finding_id(
                    method="tier4_wa_id_gap",
                    evidence_sha256=evidence_sha256,
                    source_table=target_table,
                    row_or_offset=prev_id + 1,
                    key_facts={"gap_start": prev_id + 1, "gap_end": curr_id - 1},
                )

                findings.append(
                    RecoveryFinding(
                        finding_id=fid,
                        confidence_score=0.25,  # Strictly capped <= 0.30 (B10.4)
                        strength="weak_hint",
                        limitations=(
                            "ID gaps can arise without deletion (e.g. rolled-back transactions, system/ephemeral messages, sequence jumping)",
                            "indicator only: does not prove that messages existed or were deleted",
                        ),
                        provenance=Provenance(
                            evidence_id=evidence_id,
                            evidence_sha256=evidence_sha256,
                            source_table=target_table,
                            row_id=prev_id + 1,
                            method="tier4_wa_id_gap",
                        ),
                        tier=4,
                        kind="id_gap",
                        validation_status="PARTIAL",
                        table_name=target_table,
                        row_id=prev_id + 1,
                        view="main_view",
                        recovered_fields={
                            "gap_start": prev_id + 1,
                            "gap_end": curr_id - 1,
                            "missing_count": gap_size,
                        },
                        raw_payload_hash=sha256_hex(f"gap:wa:{prev_id+1}:{curr_id-1}".encode("utf-8")),
                        raw_payload_preview=f"WA ID GAP range=[{prev_id + 1}..{curr_id - 1}] ({gap_size} missing IDs)",
                    )
                )

    conn.close()
    return findings
