"""Chat API endpoints for interactive WhatsApp and Telegram thread viewing."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import (
    Case,
    DeletedMessage,
    Evidence,
    EvidenceFile,
    MediaItem,
    TelegramContact,
    TelegramGroup,
    TelegramMessage,
    WhatsAppContact,
    WhatsAppGroup,
    WhatsAppMessage,
)

router = APIRouter()


def _calculate_msg_hash(msg_id: str, sender: str, ts: int, body: str) -> str:
    """Calculate cryptographic SHA-256 signature for message auditability."""
    payload = f"{msg_id}:{sender}:{ts}:{body or ''}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.get("/{case_id}/chats")
def get_case_chats(case_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get all WhatsApp and Telegram chat threads for a case.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    evidence_ids = [ev.id for ev in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()]
    if not evidence_ids:
        return []

    # Get WhatsApp contacts & groups lookup
    wa_contacts = {
        c.jid: c.display_name or c.phone_number or c.jid
        for c in db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id.in_(evidence_ids)).all()
        if c.jid
    }
    wa_groups = {
        g.group_jid: g.subject
        for g in db.query(WhatsAppGroup).filter(WhatsAppGroup.evidence_id.in_(evidence_ids)).all()
        if g.group_jid
    }

    # Get Telegram contacts & groups lookup
    tg_contacts = {}
    for c in db.query(TelegramContact).filter(TelegramContact.evidence_id.in_(evidence_ids)).all():
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or c.username or (f"+{c.phone}" if c.phone else str(c.user_id))
        tg_contacts[str(c.user_id)] = name

    tg_groups = {
        str(g.group_id): g.title
        for g in db.query(TelegramGroup).filter(TelegramGroup.evidence_id.in_(evidence_ids)).all()
        if g.group_id
    }

    # Get deletion counts by chat_jid
    deletion_counts = {}
    deleted_records = db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).all()
    for del_msg in deleted_records:
        jid = del_msg.chat_jid
        if jid:
            deletion_counts[jid] = deletion_counts.get(jid, 0) + (del_msg.missing_count or 1)

    threads_map: Dict[str, Dict[str, Any]] = {}

    # Query WhatsApp messages
    wa_msgs = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.evidence_id.in_(evidence_ids))
        .order_by(WhatsAppMessage.timestamp.asc())
        .all()
    )

    for msg in wa_msgs:
        jid = msg.key_remote_jid
        if not jid:
            continue
        if jid not in threads_map:
            # Resolve name
            name = wa_contacts.get(jid) or wa_groups.get(jid) or jid
            is_group = "@g.us" in jid
            threads_map[jid] = {
                "jid": jid,
                "name": name,
                "source_app": "whatsapp",
                "is_group": is_group,
                "message_count": 0,
                "last_message_body": "",
                "last_message_timestamp": 0,
                "deletion_count": deletion_counts.get(jid, 0),
                "unread_count": 0,
            }

        threads_map[jid]["message_count"] += 1
        threads_map[jid]["last_message_body"] = msg.body or (f"[{msg.media_type or 'Media'}]" if msg.media_path else "")
        threads_map[jid]["last_message_timestamp"] = msg.timestamp or threads_map[jid]["last_message_timestamp"]

    # Query Telegram messages
    tg_msgs = (
        db.query(TelegramMessage)
        .filter(TelegramMessage.evidence_id.in_(evidence_ids))
        .order_by(TelegramMessage.timestamp.asc())
        .all()
    )

    for msg in tg_msgs:
        dialog_id = str(msg.dialog_id or "default_dialog")
        if dialog_id not in threads_map:
            name = tg_contacts.get(dialog_id) or tg_groups.get(dialog_id) or f"Chat {dialog_id}"
            threads_map[dialog_id] = {
                "jid": dialog_id,
                "name": name,
                "source_app": "telegram",
                "is_group": False,
                "message_count": 0,
                "last_message_body": "",
                "last_message_timestamp": 0,
                "deletion_count": deletion_counts.get(dialog_id, 0),
                "unread_count": 0,
            }

        threads_map[dialog_id]["message_count"] += 1
        threads_map[dialog_id]["last_message_body"] = msg.body or (f"[{msg.media_type or 'Media'}]" if msg.media_path else "")
        threads_map[dialog_id]["last_message_timestamp"] = msg.timestamp or threads_map[dialog_id]["last_message_timestamp"]

    # Sort threads by last message timestamp descending
    sorted_threads = sorted(list(threads_map.values()), key=lambda t: t["last_message_timestamp"], reverse=True)
    return sorted_threads


@router.get("/{case_id}/chats/{jid_raw:path}/messages")
def get_chat_messages(case_id: int, jid_raw: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get message stream and deletion indicators for a specific chat JID or dialog_id.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    target_jid = unquote(jid_raw)

    evidence_ids = [ev.id for ev in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()]
    if not evidence_ids:
        return {"thread": None, "messages": []}

    # WhatsApp contact & group lookup
    wa_contacts = {
        c.jid: c.display_name or c.phone_number or c.jid
        for c in db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id.in_(evidence_ids)).all()
        if c.jid
    }
    wa_groups = {
        g.group_jid: g.subject
        for g in db.query(WhatsAppGroup).filter(WhatsAppGroup.evidence_id.in_(evidence_ids)).all()
        if g.group_jid
    }

    # Telegram contacts lookup
    tg_contacts = {}
    for c in db.query(TelegramContact).filter(TelegramContact.evidence_id.in_(evidence_ids)).all():
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or c.username or (f"+{c.phone}" if c.phone else str(c.user_id))
        tg_contacts[str(c.user_id)] = name

    # Fetch WhatsApp messages for this JID
    wa_msgs = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.evidence_id.in_(evidence_ids),
            WhatsAppMessage.key_remote_jid == target_jid,
        )
        .order_by(WhatsAppMessage.timestamp.asc())
        .all()
    )

    # Fetch Telegram messages for this dialog_id
    tg_msgs = (
        db.query(TelegramMessage)
        .filter(
            TelegramMessage.evidence_id.in_(evidence_ids),
            TelegramMessage.dialog_id == target_jid,
        )
        .order_by(TelegramMessage.timestamp.asc())
        .all()
    )

    # Fetch media items lookup
    media_items_map = {}
    m_items = db.query(MediaItem).filter(MediaItem.case_id == case_id).all()
    for mi in m_items:
        if mi.linked_message_id:
            media_items_map[mi.linked_message_id] = mi

    # Fetch evidence files lookup
    evidence_files_map = {}
    efs = db.query(EvidenceFile).filter(EvidenceFile.evidence_id.in_(evidence_ids)).all()
    for ef in efs:
        evidence_files_map[ef.relative_path] = ef
        evidence_files_map[ef.relative_path.split("/")[-1]] = ef

    messages_list = []

    if wa_msgs:
        thread_name = wa_contacts.get(target_jid) or wa_groups.get(target_jid) or target_jid
        source_app = "whatsapp"
        for msg in wa_msgs:
            sender_name = wa_contacts.get(msg.sender_jid) or msg.sender_jid or "Unknown Sender"
            ts_sec = (msg.timestamp or 0) / 1000.0
            ts_iso = datetime.fromtimestamp(ts_sec, tz=timezone.utc).isoformat() if msg.timestamp else ""

            # Check media details
            mi = media_items_map.get(str(msg.message_id))
            ef = evidence_files_map.get(msg.media_path.split("/")[-1]) if msg.media_path else None

            media_info = None
            if msg.media_path or mi or ef:
                media_info = {
                    "media_type": msg.media_type or (mi.media_type if mi else None) or "image",
                    "media_path": msg.media_path or (mi.file_path if mi else None),
                    "file_id": ef.id if ef else None,
                    "evidence_id": msg.evidence_id,
                    "sha256": (mi.sha256 if mi else None) or (ef.sha256 if ef else None),
                    "mime_type": (mi.mime_type if mi else None) or (ef.mime_type if ef else None),
                    "file_size": (mi.file_size if mi else None) or (ef.file_size if ef else None),
                    "exif_data": mi.exif_data if mi else {},
                }

            sha_sig = _calculate_msg_hash(str(msg.message_id), str(msg.sender_jid), msg.timestamp or 0, msg.body or "")

            messages_list.append(
                {
                    "is_deletion_marker": False,
                    "id": f"wa_{msg.id}",
                    "message_id": str(msg.message_id),
                    "chat_jid": target_jid,
                    "source_app": "whatsapp",
                    "sender_jid": msg.sender_jid,
                    "sender_name": sender_name,
                    "body": msg.body,
                    "timestamp": msg.timestamp,
                    "timestamp_iso": ts_iso,
                    "message_type": msg.message_type or ("media" if msg.media_path else "text"),
                    "media_info": media_info,
                    "status": msg.status or "delivered",
                    "sha256_signature": sha_sig,
                    "evidence_id": msg.evidence_id,
                }
            )

    elif tg_msgs:
        thread_name = tg_contacts.get(target_jid) or f"Telegram Chat {target_jid}"
        source_app = "telegram"
        for msg in tg_msgs:
            sender_id_str = str(msg.sender_id)
            sender_name = tg_contacts.get(sender_id_str) or f"User {sender_id_str}"
            ts_sec = (msg.timestamp or 0) / 1000.0
            ts_iso = datetime.fromtimestamp(ts_sec, tz=timezone.utc).isoformat() if msg.timestamp else ""

            mi = media_items_map.get(str(msg.message_id))
            ef = evidence_files_map.get(msg.media_path.split("/")[-1]) if msg.media_path else None

            media_info = None
            if msg.media_path or mi or ef:
                media_info = {
                    "media_type": msg.media_type or (mi.media_type if mi else None) or "image",
                    "media_path": msg.media_path or (mi.file_path if mi else None),
                    "file_id": ef.id if ef else None,
                    "evidence_id": msg.evidence_id,
                    "sha256": (mi.sha256 if mi else None) or (ef.sha256 if ef else None),
                    "mime_type": (mi.mime_type if mi else None) or (ef.mime_type if ef else None),
                    "file_size": (mi.file_size if mi else None) or (ef.file_size if ef else None),
                    "exif_data": mi.exif_data if mi else {},
                }

            sha_sig = _calculate_msg_hash(str(msg.message_id), sender_id_str, msg.timestamp or 0, msg.body or "")

            messages_list.append(
                {
                    "is_deletion_marker": False,
                    "id": f"tg_{msg.id}",
                    "message_id": str(msg.message_id),
                    "chat_jid": target_jid,
                    "source_app": "telegram",
                    "sender_jid": sender_id_str,
                    "sender_name": sender_name,
                    "body": msg.body,
                    "timestamp": msg.timestamp,
                    "timestamp_iso": ts_iso,
                    "message_type": msg.message_type or ("media" if msg.media_path else "text"),
                    "media_info": media_info,
                    "status": "delivered",
                    "sha256_signature": sha_sig,
                    "evidence_id": msg.evidence_id,
                }
            )
    else:
        # Fallback if no messages found directly
        return {"thread": None, "messages": []}

    # Fetch deleted messages associated with this chat
    deleted_records = (
        db.query(DeletedMessage)
        .filter(
            DeletedMessage.case_id == case_id,
            DeletedMessage.chat_jid == target_jid,
        )
        .all()
    )

    # Sort messages by timestamp ascending
    messages_list.sort(key=lambda m: m["timestamp"] or 0)

    # Merge deleted message markers into stream
    final_stream = []
    del_markers = []
    for d in deleted_records:
        del_markers.append(
            {
                "is_deletion_marker": True,
                "id": f"del_{d.id}",
                "gap_start": d.gap_start,
                "gap_end": d.gap_end,
                "missing_count": d.missing_count,
                "confidence_score": d.confidence_score,
                "detection_method": d.detection_method or "sequence_gap_analysis",
                "timestamp": d.gap_start or 0,
            }
        )

    # Simple chronological merge
    all_elements = messages_list + del_markers
    all_elements.sort(key=lambda e: e["timestamp"] or 0)

    thread_info = {
        "jid": target_jid,
        "name": thread_name,
        "source_app": source_app,
        "total_messages": len(messages_list),
        "total_deletions": sum(d.missing_count or 1 for d in deleted_records),
    }

    return {"thread": thread_info, "messages": all_elements}
