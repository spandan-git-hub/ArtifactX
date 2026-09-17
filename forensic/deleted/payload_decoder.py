"""
Schema-adaptive payload decoders for WhatsApp and Telegram physical recovery.
Classifies carved byte structures into forensic evidence with judicial status labeling.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


MIN_PLAUSIBLE_TIMESTAMP = 1262304000  # 2010-01-01 00:00:00 UTC
MAX_PLAUSIBLE_TIMESTAMP = 1893456000  # 2030-01-01 00:00:00 UTC

WA_JID_PATTERN = re.compile(r"^\+?\d{7,15}@(s\.whatsapp\.net|g\.us|broadcast)$")
PHONE_PATTERN = re.compile(r"^\+?\d{8,15}$")


@dataclass
class DecodedPayload:
    source_app: str  # 'whatsapp', 'telegram', 'unknown'
    validation_status: str  # 'RECOVERED', 'PARTIALLY_RECONSTRUCTED', 'CANDIDATE', 'UNVALIDATED'
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    sender_id: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[int] = None
    media_reference: Optional[str] = None
    limitations: List[str] = field(default_factory=list)


def normalize_timestamp(val: Any) -> Tuple[Optional[int], Optional[str]]:
    """Validate and normalize a candidate integer timestamp to seconds."""
    if not isinstance(val, int):
        return None, None

    # Check if milliseconds
    if MIN_PLAUSIBLE_TIMESTAMP * 1000 <= val <= MAX_PLAUSIBLE_TIMESTAMP * 1000:
        return val // 1000, "Normalized from millisecond timestamp"
    elif MIN_PLAUSIBLE_TIMESTAMP <= val <= MAX_PLAUSIBLE_TIMESTAMP:
        return val, None
    return None, None


class WhatsAppPayloadDecoder:
    """Adapts carved column values and raw payloads into candidate WhatsApp records."""

    @staticmethod
    def decode_record(values: List[Any], raw_bytes: bytes) -> Optional[DecodedPayload]:
        # Look for typical WhatsApp columns:
        # e.g., key_remote_jid, data/body, timestamp, key_id
        text_cols = [v for v in values if isinstance(v, str) and len(v.strip()) > 0]
        int_cols = [v for v in values if isinstance(v, int)]

        chat_jid = None
        message_id = None
        body = None
        ts = None
        media_ref = None
        limitations = []

        # Find JID or phone
        for s in text_cols:
            if WA_JID_PATTERN.match(s.strip()):
                chat_jid = s.strip()
            elif s.startswith("3EB0") or (len(s) in (16, 20, 32) and s.isalnum()):
                message_id = s
            elif any(ext in s.lower() for ext in (".jpg", ".mp4", ".opus", ".enc", ".webp")):
                media_ref = s

        # Find message body: longest non-JID, non-ID string
        for s in text_cols:
            if s != chat_jid and s != message_id and s != media_ref:
                if len(s.strip()) > 1:
                    body = s.strip()
                    break

        # Find timestamp
        for num in int_cols:
            norm_ts, note = normalize_timestamp(num)
            if norm_ts:
                ts = norm_ts
                if note:
                    limitations.append(note)
                break

        # Check if raw bytes contain JID string even if not in column
        if not chat_jid:
            raw_str = raw_bytes.decode("latin-1", errors="ignore")
            jid_match = re.search(r"(\+?\d{8,15}@(s\.whatsapp\.net|g\.us))", raw_str)
            if jid_match:
                chat_jid = jid_match.group(1)
                limitations.append("Chat JID carved from residual raw string rather than typed cell")

        if not body and not chat_jid and not ts:
            return None

        # Determine validation status
        if body and chat_jid and ts and message_id:
            status = "RECOVERED"
        elif body and (chat_jid or ts):
            status = "PARTIALLY_RECONSTRUCTED"
        elif body or chat_jid:
            status = "CANDIDATE"
        else:
            status = "UNVALIDATED"

        if status != "RECOVERED":
            limitations.append("Incomplete record closure in physical unallocated/slack space")

        return DecodedPayload(
            source_app="whatsapp",
            validation_status=status,
            message_id=message_id,
            chat_id=chat_jid,
            sender_id=chat_jid,
            body=body,
            timestamp=ts,
            media_reference=media_ref,
            limitations=limitations,
        )


class TelegramPayloadDecoder:
    """Adapts carved column values and raw payloads into candidate Telegram records."""

    @staticmethod
    def decode_record(values: List[Any], raw_bytes: bytes) -> Optional[DecodedPayload]:
        text_cols = [v for v in values if isinstance(v, str) and len(v.strip()) > 0]
        int_cols = [v for v in values if isinstance(v, int)]

        dialog_id = None
        sender_id = None
        message_id = None
        body = None
        ts = None
        media_ref = None
        limitations = []

        # Find dialog/uid or message ID
        for num in int_cols:
            norm_ts, note = normalize_timestamp(num)
            if norm_ts and not ts:
                ts = norm_ts
                if note:
                    limitations.append(note)
            elif 1000 <= num <= 9999999999:
                if not sender_id:
                    sender_id = str(num)
                elif not dialog_id:
                    dialog_id = str(num)
            elif 1 <= num < 10000000 and not message_id:
                message_id = str(num)

        for s in text_cols:
            if s.startswith("dialog_") or s.startswith("tg_") or s.startswith("-100"):
                dialog_id = s
            elif any(ext in s.lower() for ext in (".jpg", ".mp4", ".ogg", ".tg")):
                media_ref = s
            elif not body and len(s.strip()) > 1:
                body = s.strip()

        if not body and not dialog_id and not ts:
            return None

        if body and dialog_id and ts:
            status = "RECOVERED"
        elif body and (dialog_id or ts or sender_id):
            status = "PARTIALLY_RECONSTRUCTED"
        elif body or dialog_id:
            status = "CANDIDATE"
        else:
            status = "UNVALIDATED"

        if status != "RECOVERED":
            limitations.append("Telegram record carved from unallocated or fragmented space")

        return DecodedPayload(
            source_app="telegram",
            validation_status=status,
            message_id=message_id,
            chat_id=dialog_id,
            sender_id=sender_id,
            body=body,
            timestamp=ts,
            media_reference=media_ref,
            limitations=limitations,
        )
