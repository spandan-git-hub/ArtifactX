"""Correlation matcher for forensic evidence."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class WhatsAppMessage:
    evidence_id: int
    message_id: str
    key_remote_jid: str
    sender_jid: str
    participant_jid: str
    body: str
    timestamp: int
    media_type: Optional[str]
    media_path: Optional[str]
    message_type: Optional[str]
    status: str


@dataclass
class WhatsAppContact:
    evidence_id: int
    jid: str
    display_name: str
    phone_number: str
    status: str


@dataclass
class TelegramMessage:
    evidence_id: int
    message_id: int
    dialog_id: str
    sender_id: int
    body: str
    timestamp: int
    media_type: Optional[str]
    media_path: Optional[str]
    message_type: Optional[str]


@dataclass
class TelegramContact:
    evidence_id: int
    user_id: int
    first_name: str
    last_name: str
    username: str
    phone: str


@dataclass
class MediaItem:
    evidence_id: int
    file_path: str
    sha256: str
    mime_type: str
    media_type: str  # image, video, audio, document
    file_size: int
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]
    exif_data: Dict[str, Any]
    is_orphan: bool
    linked_message_id: Optional[str]


@dataclass
class WhatsAppGroup:
    evidence_id: int
    group_jid: str
    subject: str
    creator_jid: str
    creation_timestamp: int


@dataclass
class TelegramGroup:
    evidence_id: int
    group_id: int
    title: str
    username: str
    type: str


def correlate_message_to_contact_whatsapp(
    messages: List[WhatsAppMessage],
    contacts: List[WhatsAppContact],
) -> List[Dict[str, Any]]:
    """Correlate WhatsApp messages to contacts based on JID.

    Returns a list of correlation edges.
    """
    edges = []
    # Build a lookup for contacts by jid
    contact_lookup = {contact.jid: contact for contact in contacts}

    for msg in messages:
        # Check sender_jid
        if msg.sender_jid in contact_lookup:
            edges.append({
                "source_type": "wa_message",
                "source_id": msg.message_id,
                "target_type": "wa_contact",
                "target_id": msg.sender_jid,
                "relation_type": "sent_by",
                "metadata": {
                    "evidence_id": msg.evidence_id,
                    "timestamp": msg.timestamp,
                }
            })
        # Check participant_jid (for group messages, the other participant)
        if msg.participant_jid in contact_lookup:
            edges.append({
                "source_type": "wa_message",
                "source_id": msg.message_id,
                "target_type": "wa_contact",
                "target_id": msg.participant_jid,
                "relation_type": "participant_in",
                "metadata": {
                    "evidence_id": msg.evidence_id,
                    "timestamp": msg.timestamp,
                }
            })
    return edges


def correlate_message_to_contact_telegram(
    messages: List[TelegramMessage],
    contacts: List[TelegramContact],
) -> List[Dict[str, Any]]:
    """Correlate Telegram messages to contacts based on user ID.

    Returns a list of correlation edges.
    """
    edges = []
    # Build a lookup for contacts by user_id
    contact_lookup = {str(contact.user_id): contact for contact in contacts}

    for msg in messages:
        # Check sender_id
        sender_id_str = str(msg.sender_id)
        if sender_id_str in contact_lookup:
            edges.append({
                "source_type": "tg_message",
                "source_id": str(msg.message_id),
                "target_type": "tg_contact",
                "target_id": sender_id_str,
                "relation_type": "sent_by",
                "metadata": {
                    "evidence_id": msg.evidence_id,
                    "timestamp": msg.timestamp,
                }
            })
    return edges


def correlate_message_to_media_whatsapp(
    messages: List[WhatsAppMessage],
    media_items: List[MediaItem],
) -> List[Dict[str, Any]]:
    """Correlate WhatsApp messages to media items based on media path.

    Returns a list of correlation edges.
    """
    edges = []
    # Build a lookup for media items by file_path (or relative path?)
    # We'll assume media_item.file_path is the absolute path on disk.
    # The message media_path might be relative or absolute? We'll need to normalize.
    # For simplicity, we'll assume the media_path in the message is the same as the file_path in MediaItem.
    # In reality, we might need to compare the filename or use a hash.
    # We'll use the media_path from the message and check if it matches the file_path of any media item.
    media_lookup = {media.file_path: media for media in media_items}

    for msg in messages:
        if msg.media_path and msg.media_path in media_lookup:
            edges.append({
                "source_type": "wa_message",
                "source_id": msg.message_id,
                "target_type": "media_item",
                "target_id": msg.media_path,  # Using file_path as target_id for now
                "relation_type": "contains_media",
                "metadata": {
                    "evidence_id": msg.evidence_id,
                    "media_type": msg.media_type,
                }
            })
    return edges


def correlate_message_to_media_telegram(
    messages: List[TelegramMessage],
    media_items: List[MediaItem],
) -> List[Dict[str, Any]]:
    """Correlate Telegram messages to media items based on media path.

    Returns a list of correlation edges.
    """
    edges = []
    # Build a lookup for media items by file_path
    media_lookup = {media.file_path: media for media in media_items}

    for msg in messages:
        if msg.media_path and msg.media_path in media_lookup:
            edges.append({
                "source_type": "tg_message",
                "source_id": str(msg.message_id),
                "target_type": "media_item",
                "target_id": msg.media_path,
                "relation_type": "contains_media",
                "metadata": {
                    "evidence_id": msg.evidence_id,
                    "media_type": msg.media_type,
                }
            })
    return edges


def normalize_phone_number(raw_phone: str) -> str:
    """Normalize raw phone strings or JIDs into standard E.164 format (+1234567890)."""
    if not raw_phone:
        return ""
    clean = str(raw_phone).split("@")[0].split(":")[0].strip()
    digits = "".join(ch for ch in clean if ch.isdigit())
    if not digits:
        return ""
    if str(raw_phone).strip().startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}"


def correlate_cross_app_contact(
    wa_contacts: List[WhatsAppContact],
    tg_contacts: List[TelegramContact],
) -> List[Dict[str, Any]]:
    """Correlate contacts across WhatsApp and Telegram based on phone number, handle, and display name.

    Returns a list of correlation edges.
    """
    edges = []
    seen_pairs = set()

    # 1. Match by normalized E.164 phone number (Confidence 1.0)
    wa_by_phone = {}
    for wa in wa_contacts:
        phone = normalize_phone_number(wa.phone_number or wa.jid)
        if phone:
            wa_by_phone.setdefault(phone, []).append(wa)

    tg_by_phone = {}
    for tg in tg_contacts:
        phone = normalize_phone_number(tg.phone)
        if phone:
            tg_by_phone.setdefault(phone, []).append(tg)

    common_phones = set(wa_by_phone.keys()) & set(tg_by_phone.keys())
    for phone in common_phones:
        for wa in wa_by_phone[phone]:
            for tg in tg_by_phone[phone]:
                pair_key = (wa.jid, str(tg.user_id))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    edges.append({
                        "source_type": "wa_contact",
                        "source_id": wa.jid,
                        "target_type": "tg_contact",
                        "target_id": str(tg.user_id),
                        "relation_type": "matches_contact",
                        "metadata": {
                            "phone_number": phone,
                            "confidence_score": 1.0,
                            "match_reason": "Exact E.164 Phone Match",
                            "wa_name": wa.display_name or wa.jid,
                            "tg_name": f"{tg.first_name or ''} {tg.last_name or ''}".strip() or tg.username or str(tg.user_id),
                            "tg_username": tg.username,
                            "evidence_id": wa.evidence_id,
                        }
                    })

    # 2. Match by Username / Handle similarity (Confidence 0.85)
    for wa in wa_contacts:
        wa_name_clean = (wa.display_name or "").strip().lower()
        for tg in tg_contacts:
            pair_key = (wa.jid, str(tg.user_id))
            if pair_key in seen_pairs:
                continue
            tg_username = (tg.username or "").strip().lower()
            if tg_username and (tg_username == wa_name_clean or tg_username in wa.jid.lower()):
                seen_pairs.add(pair_key)
                phone = normalize_phone_number(wa.phone_number or tg.phone or wa.jid)
                edges.append({
                    "source_type": "wa_contact",
                    "source_id": wa.jid,
                    "target_type": "tg_contact",
                    "target_id": str(tg.user_id),
                    "relation_type": "matches_contact",
                    "metadata": {
                        "phone_number": phone,
                        "confidence_score": 0.85,
                        "match_reason": "Telegram Handle Match",
                        "wa_name": wa.display_name or wa.jid,
                        "tg_name": f"{tg.first_name or ''} {tg.last_name or ''}".strip() or tg.username,
                        "tg_username": tg.username,
                        "evidence_id": wa.evidence_id,
                    }
                })

    # 3. Match by Display Name Similarity (Confidence 0.75)
    for wa in wa_contacts:
        wa_name = (wa.display_name or "").strip().lower()
        if not wa_name or len(wa_name) < 3:
            continue
        for tg in tg_contacts:
            pair_key = (wa.jid, str(tg.user_id))
            if pair_key in seen_pairs:
                continue
            tg_full_name = f"{tg.first_name or ''} {tg.last_name or ''}".strip().lower()
            if tg_full_name and (tg_full_name == wa_name):
                seen_pairs.add(pair_key)
                phone = normalize_phone_number(wa.phone_number or tg.phone or wa.jid)
                edges.append({
                    "source_type": "wa_contact",
                    "source_id": wa.jid,
                    "target_type": "tg_contact",
                    "target_id": str(tg.user_id),
                    "relation_type": "matches_contact",
                    "metadata": {
                        "phone_number": phone,
                        "confidence_score": 0.75,
                        "match_reason": "Display Name Match",
                        "wa_name": wa.display_name or wa.jid,
                        "tg_name": f"{tg.first_name or ''} {tg.last_name or ''}".strip(),
                        "tg_username": tg.username,
                        "evidence_id": wa.evidence_id,
                    }
                })

    return edges


def correlate_cross_app_messages(
    wa_messages: List[WhatsAppMessage],
    tg_messages: List[TelegramMessage],
    wa_contacts: List[WhatsAppContact],
    tg_contacts: List[TelegramContact],
    time_window_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """Correlate messages across WhatsApp and Telegram occurring within a specified time window."""
    edges = []

    # Map contacts to resolved phones for entity check
    wa_contact_phones = {wa.jid: normalize_phone_number(wa.phone_number or wa.jid) for wa in wa_contacts}
    tg_contact_phones = {str(tg.user_id): normalize_phone_number(tg.phone) for tg in tg_contacts}

    for wa_msg in wa_messages:
        wa_ts = wa_msg.timestamp
        if not wa_ts:
            continue
        wa_sec = wa_ts // 1000 if wa_ts > 10_000_000_000 else wa_ts
        wa_sender_phone = wa_contact_phones.get(wa_msg.sender_jid, "")

        for tg_msg in tg_messages:
            tg_ts = tg_msg.timestamp
            if not tg_ts:
                continue
            tg_sec = tg_ts // 1000 if tg_ts > 10_000_000_000 else tg_ts

            delta = abs(wa_sec - tg_sec)
            if delta <= time_window_seconds:
                tg_sender_id = str(tg_msg.sender_id)
                tg_sender_phone = tg_contact_phones.get(tg_sender_id, "")

                same_entity = bool(wa_sender_phone and tg_sender_phone and wa_sender_phone == tg_sender_phone)
                confidence = 0.95 if same_entity else max(0.60, 0.90 - (delta / time_window_seconds) * 0.30)

                edges.append({
                    "source_type": "wa_message",
                    "source_id": str(wa_msg.message_id),
                    "target_type": "tg_message",
                    "target_id": str(tg_msg.message_id),
                    "relation_type": "time_window_correlated",
                    "metadata": {
                        "time_delta_seconds": delta,
                        "time_window_seconds": time_window_seconds,
                        "wa_timestamp": wa_sec,
                        "tg_timestamp": tg_sec,
                        "wa_sender_jid": wa_msg.sender_jid,
                        "tg_sender_id": tg_msg.sender_id,
                        "wa_body": wa_msg.body,
                        "tg_body": tg_msg.body,
                        "same_entity_pair": same_entity,
                        "confidence_score": round(confidence, 2),
                        "evidence_id": wa_msg.evidence_id,
                    }
                })


    return edges


def correlate_all(
    wa_messages: List[WhatsAppMessage],
    wa_contacts: List[WhatsAppContact],
    tg_messages: List[TelegramMessage],
    tg_contacts: List[TelegramContact],
    media_items: List[MediaItem],
    time_window_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """Run all correlation functions and return combined edges."""
    edges = []
    edges.extend(correlate_message_to_contact_whatsapp(wa_messages, wa_contacts))
    edges.extend(correlate_message_to_media_whatsapp(wa_messages, media_items))
    edges.extend(correlate_message_to_contact_telegram(tg_messages, tg_contacts))
    edges.extend(correlate_message_to_media_telegram(tg_messages, media_items))
    edges.extend(correlate_cross_app_contact(wa_contacts, tg_contacts))
    edges.extend(correlate_cross_app_messages(wa_messages, tg_messages, wa_contacts, tg_contacts, time_window_seconds))
    return edges