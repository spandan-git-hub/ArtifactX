"""Correlation service for forensic evidence."""

import traceback
from typing import List
from sqlalchemy.orm import Session

from backend.repositories.correlation_repo import CorrelationRepository
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.repositories.media_repo import MediaRepository
from backend.models.models import Evidence
from forensic.correlation.matcher import (
    correlate_message_to_contact_whatsapp,
    correlate_message_to_media_whatsapp,
    correlate_message_to_contact_telegram,
    correlate_message_to_media_telegram,
    correlate_cross_app_contact,
    correlate_all,
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
)
from backend.services.log_service import get_log_service


class CorrelationService:
    """Service for correlation operations."""

    def __init__(self):
        self.correlation_repo = CorrelationRepository()
        self.whatsapp_repo = WhatsAppRepository()
        self.telegram_repo = TelegramRepository()
        self.media_repo = MediaRepository()

    def correlate_case(self, db: Session, case_id: int) -> int:
        """
        Correlate evidence for a case.

        Args:
            db: Database session
            case_id: ID of the case to correlate

        Returns:
            Number of correlation edges created.
        """
        # Get log service
        log_service = get_log_service(db)

        # Log analysis start
        log_service.log_analysis(
            evidence_id=None,  # Case-level analysis
            log_type="correlation_start",
            message="Starting correlation for case",
            details={"case_id": case_id}
        )

        try:
            # Delete existing correlation edges for this case
            self.correlation_repo.delete_edges_by_case_id(db, case_id)

            # Get all evidences for the case
            evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
            if not evidences:
                return 0

            # Collect data from all evidences
            all_wa_messages: List[WhatsAppMessage] = []
            all_wa_contacts: List[WhatsAppContact] = []
            all_tg_messages: List[TelegramMessage] = []
            all_tg_contacts: List[TelegramContact] = []
            all_media_items: List[MediaItem] = []

            # Import service singletons for auto-analysis if needed
            from backend.services.whatsapp_service import WhatsAppService
            from backend.services.telegram_service import TelegramService
            wa_service = WhatsAppService()
            tg_service = TelegramService()

            for evidence in evidences:
                # Check if evidence needs to be parsed first
                wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence.id)
                tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence.id)

                if evidence.evidence_type != "demo" and not wa_messages and not tg_messages:
                    # Trigger parsers on real non-demo evidence
                    wa_service.analyze_evidence_sync(evidence.id, db)
                    tg_service.analyze_evidence_sync(evidence.id, db)


                # Re-fetch parsed evidence data
                wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence.id)
                wa_contacts = self.whatsapp_repo.get_contacts_by_evidence_id(db, evidence.id)
                tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence.id)
                tg_contacts = self.telegram_repo.get_contacts_by_evidence_id(db, evidence.id)

                # Convert ORM objects to forensic dataclasses
                for msg in wa_messages:
                    all_wa_messages.append(WhatsAppMessage(
                        evidence_id=msg.evidence_id,
                        message_id=msg.message_id,
                        key_remote_jid=msg.key_remote_jid,
                        sender_jid=msg.sender_jid,
                        participant_jid=msg.participant_jid,
                        body=msg.body,
                        timestamp=msg.timestamp,
                        media_type=msg.media_type,
                        media_path=msg.media_path,
                        message_type=msg.message_type,
                        status=msg.status,
                    ))
                for contact in wa_contacts:
                    all_wa_contacts.append(WhatsAppContact(
                        evidence_id=contact.evidence_id,
                        jid=contact.jid,
                        display_name=contact.display_name,
                        phone_number=contact.phone_number,
                        status=contact.status,
                    ))

                # Telegram data
                tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence.id)
                tg_contacts = self.telegram_repo.get_contacts_by_evidence_id(db, evidence.id)
                for msg in tg_messages:
                    all_tg_messages.append(TelegramMessage(
                        evidence_id=msg.evidence_id,
                        message_id=msg.message_id,
                        dialog_id=msg.dialog_id,
                        sender_id=msg.sender_id,
                        body=msg.body,
                        timestamp=msg.timestamp,
                        media_type=msg.media_type,
                        media_path=msg.media_path,
                        message_type=msg.message_type,
                    ))
                for contact in tg_contacts:
                    all_tg_contacts.append(TelegramContact(
                        evidence_id=contact.evidence_id,
                        user_id=contact.user_id,
                        first_name=contact.first_name,
                        last_name=contact.last_name,
                        username=contact.username,
                        phone=contact.phone,
                    ))

                # Media items
                media_items = self.media_repo.get_media_items_by_evidence_id(db, evidence.id)
                for media in media_items:
                    all_media_items.append(MediaItem(
                        evidence_id=media.evidence_id,
                        file_path=media.file_path,
                        sha256=media.sha256,
                        mime_type=media.mime_type,
                        media_type=media.media_type,
                        file_size=media.file_size,
                        width=media.width,
                        height=media.height,
                        duration=media.duration,
                        exif_data=media.exif_data or {},
                        is_orphan=media.is_orphan,
                        linked_message_id=media.linked_message_id,
                    ))

            # Auto-align demo message bodies & timestamps for authentic forensic correlation
            if any(e.evidence_type == "demo" for e in evidences):
                from datetime import datetime, timezone, timedelta
                import random
                from backend.models.models import WhatsAppMessage as ORMWhatsAppMessage, TelegramMessage as ORMTelegramMessage
                from backend.api.demo import REALISTIC_EXCHANGES

                base_time = datetime.now(timezone.utc) - timedelta(days=3)
                demo_ev_ids = [e.id for e in evidences if e.evidence_type == "demo"]
                wa_db_msgs = db.query(ORMWhatsAppMessage).filter(ORMWhatsAppMessage.evidence_id.in_(demo_ev_ids)).order_by(ORMWhatsAppMessage.id).all()
                tg_db_msgs = db.query(ORMTelegramMessage).filter(ORMTelegramMessage.evidence_id.in_(demo_ev_ids)).order_by(ORMTelegramMessage.id).all()

                if wa_db_msgs and tg_db_msgs:
                    min_count = min(len(wa_db_msgs), len(tg_db_msgs))
                    for idx in range(min_count):
                        pair = REALISTIC_EXCHANGES[idx % len(REALISTIC_EXCHANGES)]
                        slot_time = base_time + timedelta(minutes=idx * 20)
                        wa_sec = int(slot_time.timestamp())
                        tg_sec = int((slot_time + timedelta(seconds=random.randint(15, 45))).timestamp())

                        wa_db_msgs[idx].body = pair["wa"]
                        wa_db_msgs[idx].timestamp = wa_sec
                        tg_db_msgs[idx].body = pair["tg"]
                        tg_db_msgs[idx].timestamp = tg_sec

                    db.commit()

                    all_wa_messages = [WhatsAppMessage(
                        evidence_id=m.evidence_id, message_id=m.message_id, key_remote_jid=m.key_remote_jid,
                        sender_jid=m.sender_jid, participant_jid=m.participant_jid, body=m.body,
                        timestamp=m.timestamp, media_type=m.media_type, media_path=m.media_path,
                        message_type=m.message_type, status=m.status
                    ) for m in wa_db_msgs]

                    all_tg_messages = [TelegramMessage(
                        evidence_id=m.evidence_id, message_id=m.message_id, dialog_id=m.dialog_id,
                        sender_id=m.sender_id, body=m.body, timestamp=m.timestamp,
                        media_type=m.media_type, media_path=m.media_path, message_type=m.message_type
                    ) for m in tg_db_msgs]

            # Run correlation
            edges = correlate_all(
                all_wa_messages,
                all_wa_contacts,
                all_tg_messages,
                all_tg_contacts,
                all_media_items,
                time_window_seconds=300,
            )


            # Add case_id to each edge and save
            for edge in edges:
                edge["case_id"] = case_id

            self.correlation_repo.save_edges(db, edges)

            # Log analysis success
            log_service.log_analysis(
                evidence_id=None,
                log_type="correlation_completed",
                message="Correlation completed successfully",
                details={"case_id": case_id, "edges_created": len(edges)}
            )

            return len(edges)
        except Exception as e:
            # Log error
            log_service.log_error(
                error_type="correlation_error",
                message=f"Error during correlation: {str(e)}",
                case_id=case_id,
                evidence_id=None,
                stack_trace=traceback.format_exc(),
                endpoint="/api/cases/{case_id}/correlate",
                method="POST"
            )
            return 0

    def get_edges_for_case(self, db: Session, case_id: int) -> List[dict]:
        """Get correlation edges for a case as dictionaries."""
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        return [
            {
                "id": edge.id,
                "case_id": edge.case_id,
                "source_type": edge.source_type,
                "source_id": edge.source_id,
                "target_type": edge.target_type,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "metadata": edge.metadata_,
            }
            for edge in edges
        ]

    def get_entity_resolutions(self, db: Session, case_id: int) -> List[dict]:
        """Get resolved cross-app entity contact mappings for a case."""
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        contact_edges = [e for e in edges if e.relation_type == "matches_contact"]

        resolutions = []
        for edge in contact_edges:
            meta = edge.metadata_ or {}
            resolutions.append({
                "id": edge.id,
                "wa_jid": edge.source_id,
                "tg_user_id": edge.target_id,
                "phone_number": meta.get("phone_number", ""),
                "confidence_score": meta.get("confidence_score", 1.0),
                "match_reason": meta.get("match_reason", "Contact Match"),
                "wa_name": meta.get("wa_name", edge.source_id),
                "tg_name": meta.get("tg_name", edge.target_id),
                "tg_username": meta.get("tg_username", ""),
            })

        # Sort by highest confidence score first
        resolutions.sort(key=lambda x: x["confidence_score"], reverse=True)
        return resolutions

    def get_cross_app_message_matrix(self, db: Session, case_id: int, window_seconds: int = 300) -> List[dict]:
        """Get correlated cross-app message exchanges within the specified time window threshold."""
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        matrix_edges = [
            e for e in edges
            if e.relation_type == "time_window_correlated"
            and (e.metadata_ or {}).get("time_delta_seconds", 999999) <= window_seconds
        ]

        matrix = []
        for edge in matrix_edges:
            meta = edge.metadata_ or {}
            matrix.append({
                "id": edge.id,
                "wa_message_id": edge.source_id,
                "tg_message_id": edge.target_id,
                "time_delta_seconds": meta.get("time_delta_seconds", 0),
                "wa_timestamp": meta.get("wa_timestamp"),
                "tg_timestamp": meta.get("tg_timestamp"),
                "wa_sender_jid": meta.get("wa_sender_jid", ""),
                "tg_sender_id": meta.get("tg_sender_id", ""),
                "wa_body": meta.get("wa_body", ""),
                "tg_body": meta.get("tg_body", ""),
                "same_entity_pair": meta.get("same_entity_pair", False),
                "confidence_score": meta.get("confidence_score", 0.75),
            })

        # Sort by smallest time delta first
        matrix.sort(key=lambda x: (x["time_delta_seconds"], -x["confidence_score"]))
        return matrix


# Singleton instance
correlation_service = CorrelationService()

# Singleton instance
correlation_service = CorrelationService()