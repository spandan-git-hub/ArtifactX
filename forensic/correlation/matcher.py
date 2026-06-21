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


def correlate_cross_app_contact(
    wa_contacts: List[WhatsAppContact],
    tg_contacts: List[TelegramContact],
) -> List[Dict[str, Any]]:
    """Correlate contacts across WhatsApp and Telegram based on phone number.

    Returns a list of correlation edges.
    """
    edges = []
    # Build lookup for WhatsApp contacts by phone number
    wa_phone_lookup = {}
    for contact in wa_contacts:
        # Normalize phone number: remove non-digits
        phone = ''.join(filter(str.isdigit, contact.phone_number))
        if phone:
            wa_phone_lookup.setdefault(phone, []).append(contact)

    # Build lookup for Telegram contacts by phone number
    tg_phone_lookup = {}
    for contact in tg_contacts:
        phone = ''.join(filter(str.isdigit, contact.phone))
        if phone:
            tg_phone_lookup.setdefault(phone, []).append(contact)

    # For each phone number that appears in both, create edges
    for phone in set(wa_phone_lookup.keys()) & set(tg_phone_lookup.keys()):
        for wa_contact in wa_phone_lookup[phone]:
            for tg_contact in tg_phone_lookup[phone]:
                edges.append({
                    "source_type": "wa_contact",
                    "source_id": wa_contact.jid,
                    "target_type": "tg_contact",
                    "target_id": str(tg_contact.user_id),
                    "relation_type": "matches_contact",
                    "metadata": {
                        "phone_number": phone,
                        "evidence_id": wa_contact.evidence_id,  # Note: they might be from different evidence? We assume same case.
                    }
                })
                # Also the reverse direction? We'll do one direction for now.
    return edges


def correlate_all(
    wa_messages: List[WhatsAppMessage],
    wa_contacts: List[WhatsAppContact],
    tg_messages: List[TelegramMessage],
    tg_contacts: List[TelegramContact],
    media_items: List[MediaItem],
) -> List[Dict[str, Any]]:
    """Run all correlation functions and return combined edges."""
    edges = []
    edges.extend(correlate_message_to_contact_whatsapp(wa_messages, wa_contacts))
    edges.extend(correlate_message_to_media_whatsapp(wa_messages, media_items))
    edges.extend(correlate_message_to_contact_telegram(tg_messages, tg_contacts))
    edges.extend(correlate_message_to_media_telegram(tg_messages, media_items))
    edges.extend(correlate_cross_app_contact(wa_contacts, tg_contacts))
    # TODO: Add group correlations if needed
    return edges