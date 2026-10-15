"""
Deduplication and Validation Status Filtering (spec B10.5, master.md R8, R11).

Implements:
1. Live row identification (WhatsApp key_id/composite, Telegram uid+mid/composite)
2. Tagging matching records as DUPLICATE_OF_LIVE (retained for traceability, excluded from deletion counts)
3. Cross-tier deduplication (stronger tier wins, weaker marked DUPLICATE_OF_OTHER_TIER)
4. Deterministic sort ordering: (tier, table, page_no, byte_offset, row_id, finding_id)
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.common.hashing import sha256_hex
from forensic.common.sqlite_open import open_sqlite_ro
from forensic.recovery.models import RecoveryFinding, ValidationStatus


def build_live_row_index(
    db_bytes: bytes,
    app_hint: str = "whatsapp",
) -> Set[Any]:
    """
    Build identity keys for all live rows currently in the database view.
    WhatsApp identity key: key_id (string) or (chat_id, timestamp, body_hash)
    Telegram identity key: (uid, mid) or (uid, date, data_hash)
    """
    conn = open_sqlite_ro(db_bytes)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}

    live_keys: Set[Any] = set()
    is_tg = "telegram" in app_hint.lower() or "tg" in app_hint.lower() or "messages_v2" in tables

    if is_tg and "messages_v2" in tables:
        cursor.execute("SELECT mid, uid, date, data FROM messages_v2 WHERE mid IS NOT NULL")
        for row in cursor.fetchall():
            mid, uid, date_s, data_blob = row
            if mid is not None and uid is not None:
                live_keys.add((int(uid), int(mid)))
                live_keys.add(int(mid))
            if uid is not None and date_s is not None and data_blob:
                h = sha256_hex(bytes(data_blob))
                live_keys.add((int(uid), int(date_s), h))

    elif "message" in tables or "messages" in tables:
        target_table = "message" if "message" in tables else "messages"
        cursor.execute(f"PRAGMA table_info({target_table})")
        cols = {r[1] for r in cursor.fetchall()}

        key_col = "key_id" if "key_id" in cols else None
        chat_col = "chat_row_id" if "chat_row_id" in cols else ("key_remote_jid" if "key_remote_jid" in cols else None)
        ts_col = "timestamp" if "timestamp" in cols else None
        text_col = "text_data" if "text_data" in cols else ("data" if "data" in cols else None)

        select_cols = [c for c in [key_col, chat_col, ts_col, text_col, "_id"] if c]
        if key_col:
            cursor.execute(f"SELECT {', '.join(select_cols)} FROM {target_table}")
            for row in cursor.fetchall():
                row_dict = dict(zip(select_cols, row))
                k = row_dict.get(key_col)
                if k:
                    live_keys.add(str(k))
                row_id = row_dict.get("_id")
                if row_id:
                    live_keys.add(f"rowid:{row_id}")

                cid = row_dict.get(chat_col)
                ts = row_dict.get(ts_col)
                txt = row_dict.get(text_col)
                if cid is not None and ts is not None and txt:
                    h = sha256_hex(str(txt).encode("utf-8"))
                    live_keys.add((str(cid), int(ts), h))

    conn.close()
    return live_keys


def get_finding_identity_key(finding: RecoveryFinding) -> Optional[Any]:
    """Extract canonical identity key for deduplication."""
    rf = finding.recovered_fields

    # WhatsApp: primary key_id, secondary composite
    if "key_id" in rf and rf["key_id"]:
        return str(rf["key_id"])

    # Telegram: (uid, mid)
    if "mid" in rf and rf["mid"] is not None:
        uid = rf.get("uid")
        if uid is not None:
            return (int(uid), int(rf["mid"]))
        return int(rf["mid"])

    # Row ID fallback
    if finding.row_id is not None:
        return f"rowid:{finding.row_id}"

    # Composite payload hash fallback
    if finding.raw_payload_hash:
        return finding.raw_payload_hash

    return None


def deduplicate_and_sort_findings(
    findings: List[RecoveryFinding],
    live_keys: Set[Any],
) -> List[RecoveryFinding]:
    """
    Apply B10.5 de-duplication rules:
    1. Mark records matching live rows as DUPLICATE_OF_LIVE
    2. Cross-tier deduplication: stronger tier wins, weaker marked DUPLICATE_OF_OTHER_TIER
    3. Deterministic ordering: (tier, table, page_no, byte_offset, row_id, finding_id)
    """
    processed: List[RecoveryFinding] = []
    seen_identities: Dict[Any, int] = {}  # identity_key -> tier

    # First pass: sort preliminarily by tier so stronger tiers are evaluated first
    sorted_by_tier = sorted(
        findings,
        key=lambda f: (
            f.tier,
            f.table_name or "",
            f.page_no or 0,
            f.byte_offset or 0,
            f.row_id or 0,
            f.finding_id,
        ),
    )

    for f in sorted_by_tier:
        ident = get_finding_identity_key(f)

        # 1. Check if record matches an active live row
        is_live = False
        if ident in live_keys:
            is_live = True
        elif f.row_id is not None and f"rowid:{f.row_id}" in live_keys:
            is_live = True

        if is_live and f.kind != "revocation" and f.kind != "edit":
            # Retain in output with DUPLICATE_OF_LIVE status (B10.5)
            updated = RecoveryFinding(
                finding_id=f.finding_id,
                confidence_score=f.confidence_score,
                strength=f.strength,
                limitations=f.limitations + ("record identity matches active live database row; not counted as deleted",),
                provenance=f.provenance,
                tier=f.tier,
                kind=f.kind,
                validation_status="DUPLICATE_OF_LIVE",
                table_name=f.table_name,
                row_id=f.row_id,
                page_no=f.page_no,
                byte_offset=f.byte_offset,
                frame_index=f.frame_index,
                view=f.view,
                recovered_fields=f.recovered_fields,
                candidate_original_text=f.candidate_original_text,
                raw_payload_hash=f.raw_payload_hash,
                raw_payload_preview=f.raw_payload_preview,
            )
            processed.append(updated)
            if ident:
                seen_identities[ident] = f.tier
            continue

        # 2. Check cross-tier deduplication
        if ident and ident in seen_identities:
            prior_tier = seen_identities[ident]
            if f.tier >= prior_tier:
                # Weaker or duplicate tier
                updated = RecoveryFinding(
                    finding_id=f.finding_id,
                    confidence_score=f.confidence_score,
                    strength=f.strength,
                    limitations=f.limitations + (f"superseded by stronger finding in Tier {prior_tier}",),
                    provenance=f.provenance,
                    tier=f.tier,
                    kind=f.kind,
                    validation_status="DUPLICATE_OF_OTHER_TIER",
                    table_name=f.table_name,
                    row_id=f.row_id,
                    page_no=f.page_no,
                    byte_offset=f.byte_offset,
                    frame_index=f.frame_index,
                    view=f.view,
                    recovered_fields=f.recovered_fields,
                    candidate_original_text=f.candidate_original_text,
                    raw_payload_hash=f.raw_payload_hash,
                    raw_payload_preview=f.raw_payload_preview,
                )
                processed.append(updated)
                continue

        if ident:
            seen_identities[ident] = f.tier

        processed.append(f)

    # Deterministic sort order (B10.5, R11)
    processed.sort(
        key=lambda f: (
            f.tier,
            f.table_name or "",
            f.page_no or 0,
            f.byte_offset or 0,
            f.row_id or 0,
            f.finding_id,
        )
    )

    return processed
