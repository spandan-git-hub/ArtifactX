"""Shared record-identity matching rules for evaluation (spec C1.1, C1.2).

Provides documented matching definitions for:
1. Messages: (id/key_id, sender, timestamp_utc_ms, text_body, message_type, chat_id).
2. Recovery deletions: marker, key_id, row_id, expected_tier vs RecoveryFinding.
3. Correlation links: candidate pair (type, source_evidence, target_evidence, entity).
4. Timeline events: total sort key ordering vs manifest sequence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def normalize_text(text: Optional[str]) -> str:
    if text is None:
        return ""
    return text.strip()


def match_message_record(
    parsed: Any,
    manifest_item: Dict[str, Any],
    is_whatsapp: bool = True,
) -> Dict[str, bool]:
    """Evaluate field-by-field accuracy between a parsed message and a ground-truth manifest item.

    Returns dict of boolean matches per field:
    {
        "id": bool,
        "sender": bool,
        "timestamp": bool,
        "body": bool,
        "type": bool,
        "chat": bool,
        "all_match": bool,
    }
    """
    field_matches: Dict[str, bool] = {}

    if is_whatsapp:
        # WhatsApp matching
        key_id = getattr(parsed, "key_id", None) or getattr(parsed, "id", None) or getattr(parsed, "row_id", None) or getattr(parsed, "message_id", None)
        exp_id = manifest_item.get("key_id") or manifest_item.get("id") or manifest_item.get("row_id") or manifest_item.get("message_id")
        field_matches["id"] = bool(key_id is not None and str(key_id) == str(exp_id))

        sender = getattr(parsed, "sender_jid", None) or getattr(parsed, "sender", None)
        exp_sender = manifest_item.get("sender_jid") or manifest_item.get("sender")
        field_matches["sender"] = bool(str(sender or "").split("@")[0] == str(exp_sender or "").split("@")[0])

        ts_ms = getattr(parsed, "ts_utc_ms", None) or getattr(parsed, "timestamp_ms", None) or getattr(parsed, "timestamp_utc_ms", None) or getattr(parsed, "timestamp", None)
        exp_ts = manifest_item.get("ts_utc_ms") or manifest_item.get("timestamp_ms") or manifest_item.get("timestamp_utc_ms") or manifest_item.get("timestamp")
        field_matches["timestamp"] = bool(ts_ms is not None and exp_ts is not None and abs(int(ts_ms) - int(exp_ts)) <= 1000)

        body = getattr(parsed, "text", None) or getattr(parsed, "text_content", None) or getattr(parsed, "body", None)
        exp_body = manifest_item.get("text") or manifest_item.get("body") or manifest_item.get("text_content")
        field_matches["body"] = normalize_text(body) == normalize_text(exp_body)

        msg_type = getattr(parsed, "message_type_name", None) or getattr(parsed, "message_type", None) or getattr(parsed, "type", None)
        exp_type = manifest_item.get("type") or manifest_item.get("message_type")
        field_matches["type"] = bool(str(msg_type or "").lower() == str(exp_type or "").lower())

        chat = getattr(parsed, "chat_jid", None) or getattr(parsed, "chat", None)
        exp_chat = manifest_item.get("chat_jid") or manifest_item.get("chat")
        field_matches["chat"] = bool(str(chat or "").split("@")[0] == str(exp_chat or "").split("@")[0])

    else:
        # Telegram matching
        mid = getattr(parsed, "mid", None) or getattr(parsed, "id", None)
        exp_mid = manifest_item.get("mid") or manifest_item.get("id")
        field_matches["id"] = bool(mid is not None and int(mid) == int(exp_mid or -1))

        sender = getattr(parsed, "from_id", None) or getattr(parsed, "sender", None)
        exp_sender = manifest_item.get("from_id") or manifest_item.get("sender")
        field_matches["sender"] = bool(str(sender or "") == str(exp_sender or ""))

        ts_ms = getattr(parsed, "date_utc_ms", None) or getattr(parsed, "timestamp_utc_ms", None)
        exp_ts = manifest_item.get("date_utc_ms") or manifest_item.get("timestamp_utc_ms")
        field_matches["timestamp"] = bool(ts_ms is not None and exp_ts is not None and abs(int(ts_ms) - int(exp_ts)) <= 1000)

        body = getattr(parsed, "text", None) or getattr(parsed, "message_text", None) or getattr(parsed, "body", None)
        exp_body = manifest_item.get("text") or manifest_item.get("message_text") or manifest_item.get("body")
        field_matches["body"] = normalize_text(body) == normalize_text(exp_body)

        msg_type = getattr(parsed, "media_kind", None) or getattr(parsed, "message_type", None) or getattr(parsed, "type", None) or "text"
        exp_type = manifest_item.get("media_type") or manifest_item.get("message_type") or manifest_item.get("type") or "text"
        field_matches["type"] = bool(str(msg_type or "").lower() == str(exp_type or "").lower())

        chat = getattr(parsed, "dialog_id", None) or getattr(parsed, "chat", None)
        exp_chat = manifest_item.get("uid") or manifest_item.get("dialog_id") or manifest_item.get("chat")
        field_matches["chat"] = bool(str(chat or "") == str(exp_chat or ""))

    field_matches["all_match"] = all(field_matches.values())
    return field_matches


def match_recovery_item(
    finding: Any,
    manifest_deletion: Dict[str, Any],
) -> Tuple[bool, bool]:
    """Match a RecoveryFinding against a manifest deletion item.

    Returns:
        (is_exact_match, is_partial_match)
    """
    marker = manifest_deletion.get("marker")
    key_id = manifest_deletion.get("original_key_id")
    row_id = manifest_deletion.get("original_message_row_id") or manifest_deletion.get("original_mid")
    expected_tier_str = manifest_deletion.get("expected_tier", "unrecoverable")

    expected_tier = 0
    if "tier_1" in expected_tier_str:
        expected_tier = 1
    elif "tier_2" in expected_tier_str:
        expected_tier = 2
    elif "tier_3" in expected_tier_str:
        expected_tier = 3
    elif "tier_4" in expected_tier_str:
        expected_tier = 4

    # Check tier match
    tier = getattr(finding, "tier", 0)
    if expected_tier != 0 and tier != expected_tier:
        return (False, False)

    rf = getattr(finding, "recovered_fields", {}) or {}
    raw_preview = getattr(finding, "raw_payload_preview", "") or ""

    marker_match = False
    if marker:
        body = str(rf.get("body") or "")
        k_id = str(rf.get("key_id") or "")
        marker_match = (marker in body) or (marker in raw_preview) or (marker == k_id)

    key_match = False
    if key_id and rf.get("key_id"):
        key_match = str(rf.get("key_id")) == str(key_id)

    row_match = False
    f_row_id = getattr(finding, "row_id", None)
    if row_id is not None and f_row_id is not None:
        if tier == 4:
            # For Tier 4 gaps, check range if present
            gap_start = rf.get("gap_start_id")
            gap_end = rf.get("gap_end_id")
            if gap_start is not None and gap_end is not None:
                row_match = gap_start <= row_id <= gap_end
            else:
                row_match = f_row_id == row_id
        else:
            row_match = f_row_id == row_id

    # Validation status
    val_status = getattr(finding, "validation_status", "FULL_RECORD_VALID")

    if (marker_match or key_match or row_match):
        if val_status == "FULL_RECORD_VALID":
            return (True, False)
        elif val_status == "PARTIAL":
            return (False, True)

    return (False, False)


def match_correlation_item(
    finding: Any,
    planted_link: Dict[str, Any],
) -> bool:
    """Check if a correlation finding identifies a planted shared entity."""
    exp_type = str(planted_link.get("type", "")).lower()
    val_norm = str(planted_link.get("value_norm") or planted_link.get("entity") or "")

    f_kind = str(getattr(finding, "kind", "") or getattr(finding, "correlation_type", "")).lower()
    f_val = str(getattr(finding, "normalized_value", ""))
    f_details = getattr(finding, "details", {}) or {}

    # Type matching
    type_matches = False
    if exp_type in ("btc_address", "evm_address", "iban", "crypto") and ("crypto" in f_kind or "iban" in f_kind or "banking" in f_kind):
        type_matches = True
    elif exp_type in ("phone",) and "phone" in f_kind:
        type_matches = True
    elif exp_type in ("url",) and "url" in f_kind:
        type_matches = True
    elif exp_type in ("image_near_duplicate", "media") and "media" in f_kind:
        type_matches = True
    elif exp_type in ("gps_rendezvous", "rendezvous") and ("rendezvous" in f_kind or "geo" in f_kind or "spatiotemporal" in f_kind):
        type_matches = True
    elif not exp_type or exp_type in f_kind or f_kind in exp_type:
        type_matches = True

    if not type_matches:
        return False

    # Value matching
    if val_norm:
        if val_norm.lower() in f_val.lower() or f_val.lower() in val_norm.lower():
            return True
        for v in f_details.values():
            if val_norm.lower() in str(v).lower():
                return True
        # For near-duplicate image, match on media dhash
        if exp_type in ("image_near_duplicate", "media") and ("media" in f_kind or "dhash" in f_kind):
            return True
        # For rendezvous, match on spatiotemporal rendezvous finding
        if exp_type in ("gps_rendezvous", "rendezvous") and ("rendezvous" in f_kind or "spatiotemporal" in f_kind):
            return True

    return False
