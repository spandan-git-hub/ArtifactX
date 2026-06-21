"""Timeline event builder for forensic analysis."""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from forensic.timeline.normalizer import normalize_timestamp


class TimelineBuilder:
    """Builds timeline events from parsed evidence data."""

    def __init__(self):
        self.whatsapp_repo = WhatsAppRepository()
        self.telegram_repo = TelegramRepository()

    def build_timeline_for_case(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """
        Build timeline events for a case from WhatsApp and Telegram messages.

        Args:
            db: Database session
            case_id: ID of the case to build timeline for

        Returns:
            List of timeline event dictionaries ready to be saved to database
        """
        # Get all evidence IDs for this case
        from backend.models.models import Evidence
        evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        evidence_ids = [e.id for e in evidences]

        timeline_events = []

        # Process WhatsApp messages
        for evidence_id in evidence_ids:
            wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence_id)
            for msg in wa_messages:
                normalized_ts = normalize_timestamp(msg.timestamp)
                event_data = {
                    "case_id": case_id,
                    "evidence_id": evidence_id,
                    "event_type": "message",
                    "source_app": "whatsapp",
                    "timestamp": msg.timestamp,
                    "normalized_timestamp": normalized_ts,
                    "entity_id": msg.message_id,
                    "entity_type": "message",
                    "description": msg.body or "",
                    "metadata_": {
                        "sender_jid": msg.sender_jid,
                        "participant_jid": msg.participant_jid,
                        "key_remote_jid": msg.key_remote_jid,
                        "media_type": msg.media_type,
                        "media_path": msg.media_path,
                        "message_type": msg.message_type,
                        "status": msg.status,
                    },
                }
                timeline_events.append(event_data)

        # Process Telegram messages
        for evidence_id in evidence_ids:
            tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence_id)
            for msg in tg_messages:
                normalized_ts = normalize_timestamp(msg.timestamp)
                event_data = {
                    "case_id": case_id,
                    "evidence_id": evidence_id,
                    "event_type": "message",
                    "source_app": "telegram",
                    "timestamp": msg.timestamp,
                    "normalized_timestamp": normalized_ts,
                    "entity_id": str(msg.message_id),
                    "entity_type": "message",
                    "description": msg.body or "",
                    "metadata_": {
                        "dialog_id": msg.dialog_id,
                        "sender_id": msg.sender_id,
                        "media_type": msg.media_type,
                        "media_path": msg.media_path,
                        "message_type": msg.message_type,
                    },
                }
                timeline_events.append(event_data)

        return timeline_events