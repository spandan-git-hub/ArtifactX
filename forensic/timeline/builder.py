"""Timeline event builder for forensic analysis."""

import hashlib
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from forensic.timeline.normalizer import normalize_timestamp
from backend.models.models import Evidence, DeletedMessage


def _compute_hash(raw_str: str) -> str:
    """Compute a 64-char SHA-256 hex digest for an event string."""
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()


class TimelineBuilder:
    """Builds timeline events from parsed evidence data."""

    def __init__(self):
        self.whatsapp_repo = WhatsAppRepository()
        self.telegram_repo = TelegramRepository()

    def build_timeline_for_case(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """
        Build timeline events for a case from WhatsApp, Telegram, deleted gaps, and evidence files.

        Args:
            db: Database session
            case_id: ID of the case to build timeline for

        Returns:
            List of timeline event dictionaries ready to be saved to database
        """
        evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        evidence_ids = [e.id for e in evidences]

        timeline_events = []

        # 1. Process Evidence Ingestion events
        for ev in evidences:
            ts_dt = ev.uploaded_at or datetime.utcnow()
            ts_ms = int(ts_dt.replace(tzinfo=timezone.utc).timestamp() * 1000) if ts_dt.tzinfo else int(ts_dt.timestamp() * 1000)
            fname = ev.original_filename or f"evidence_{ev.id}"
            hash_fp = ev.sha256 or _compute_hash(f"evidence:{ev.id}:{fname}")
            event_data = {
                "case_id": case_id,
                "evidence_id": ev.id,
                "event_type": "evidence_ingest",
                "source_app": ev.evidence_type or "system",
                "timestamp": ts_ms,
                "normalized_timestamp": ts_dt,
                "entity_id": str(ev.id),
                "entity_type": "evidence",
                "description": f"Evidence ingested: {fname}",
                "metadata_": {
                    "entity_jid": fname,
                    "file_name": fname,
                    "sha256": ev.sha256,
                    "hash_fingerprint": hash_fp,
                },
            }
            timeline_events.append(event_data)


        valid_ev_ids = set(evidence_ids)

        # 2. Process WhatsApp messages
        wa_messages = []
        if evidence_ids:
            for evidence_id in evidence_ids:
                wa_messages.extend(self.whatsapp_repo.get_messages_by_evidence_id(db, evidence_id))
        else:
            from backend.models.models import WhatsAppMessage
            wa_messages = db.query(WhatsAppMessage).all()

        for msg in wa_messages:
            normalized_ts = normalize_timestamp(msg.timestamp)
            entity_jid = msg.sender_jid or msg.key_remote_jid or msg.participant_jid or "whatsapp_user"
            raw_fp_str = f"wa:{msg.message_id}:{msg.timestamp}:{entity_jid}:{msg.body or ''}"
            hash_fp = _compute_hash(raw_fp_str)
            safe_ev_id = msg.evidence_id if (msg.evidence_id and msg.evidence_id in valid_ev_ids) else (evidence_ids[0] if evidence_ids else None)

            event_data = {
                "case_id": case_id,
                "evidence_id": safe_ev_id,
                "event_type": "message",
                "source_app": "whatsapp",
                "timestamp": msg.timestamp,
                "normalized_timestamp": normalized_ts,
                "entity_id": str(msg.message_id),
                "entity_type": "message",
                "description": msg.body or "",
                "metadata_": {
                    "entity_jid": entity_jid,
                    "sender_jid": msg.sender_jid,
                    "participant_jid": msg.participant_jid,
                    "key_remote_jid": msg.key_remote_jid,
                    "media_type": msg.media_type,
                    "media_path": msg.media_path,
                    "message_type": msg.message_type,
                    "status": msg.status,
                    "hash_fingerprint": hash_fp,
                },
            }
            timeline_events.append(event_data)

        # 3. Process Telegram messages
        tg_messages = []
        if evidence_ids:
            for evidence_id in evidence_ids:
                tg_messages.extend(self.telegram_repo.get_messages_by_evidence_id(db, evidence_id))
        else:
            from backend.models.models import TelegramMessage
            tg_messages = db.query(TelegramMessage).all()

        for msg in tg_messages:
            normalized_ts = normalize_timestamp(msg.timestamp)
            entity_jid = f"tg_{msg.sender_id}" if msg.sender_id else (str(msg.dialog_id) if msg.dialog_id else "telegram_user")
            raw_fp_str = f"tg:{msg.message_id}:{msg.timestamp}:{entity_jid}:{msg.body or ''}"
            hash_fp = _compute_hash(raw_fp_str)
            safe_ev_id = msg.evidence_id if (msg.evidence_id and msg.evidence_id in valid_ev_ids) else (evidence_ids[0] if evidence_ids else None)

            event_data = {
                "case_id": case_id,
                "evidence_id": safe_ev_id,
                "event_type": "message",
                "source_app": "telegram",
                "timestamp": msg.timestamp,
                "normalized_timestamp": normalized_ts,
                "entity_id": str(msg.message_id),
                "entity_type": "message",
                "description": msg.body or "",
                "metadata_": {
                    "entity_jid": entity_jid,
                    "dialog_id": msg.dialog_id,
                    "sender_id": msg.sender_id,
                    "media_type": msg.media_type,
                    "media_path": msg.media_path,
                    "message_type": msg.message_type,
                    "hash_fingerprint": hash_fp,
                },
            }
            timeline_events.append(event_data)

        # 4. Process Deleted Message Gaps
        deleted_gaps = db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).all()
        if not deleted_gaps:
            try:
                from backend.services.deleted_service import deleted_service
                deleted_service.detect_deletions_for_case(db, case_id)
                deleted_gaps = db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).all()
            except Exception as ex:
                print(f"[TimelineBuilder] Error auto-detecting deleted messages: {ex}")

        for gap in deleted_gaps:
            ts_val = gap.gap_start if (gap.gap_start and gap.gap_start > 1e11) else (int(gap.detected_at.timestamp() * 1000) if gap.detected_at else 0)
            normalized_ts = normalize_timestamp(ts_val) if ts_val > 0 else (gap.detected_at or datetime.utcnow())
            entity_jid = gap.chat_jid or "unknown_chat"
            hash_fp = _compute_hash(f"deleted:{gap.id}:{gap.gap_start}:{entity_jid}")
            safe_ev_id = gap.evidence_id if (gap.evidence_id and gap.evidence_id in valid_ev_ids) else (evidence_ids[0] if evidence_ids else None)

            event_data = {
                "case_id": case_id,
                "evidence_id": safe_ev_id,
                "event_type": "deleted_gap",
                "source_app": gap.source_app or "whatsapp",
                "timestamp": ts_val,
                "normalized_timestamp": normalized_ts,
                "entity_id": f"gap_{gap.id}",
                "entity_type": "deletion_gap",
                "description": f"[DELETED MESSAGE GAP] ~{gap.missing_count} missing messages in {entity_jid} (Confidence: {int(gap.confidence_score * 100)}%)",

                "metadata_": {
                    "entity_jid": entity_jid,
                    "chat_jid": gap.chat_jid,
                    "gap_start": gap.gap_start,
                    "gap_end": gap.gap_end,
                    "missing_count": gap.missing_count,
                    "confidence_score": gap.confidence_score,
                    "detection_method": gap.detection_method,
                    "hash_fingerprint": hash_fp,
                },
            }
            timeline_events.append(event_data)


        return timeline_events