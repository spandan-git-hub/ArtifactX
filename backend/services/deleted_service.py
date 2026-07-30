"""Deleted message detection service."""

import traceback
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.repositories.deleted_repo import DeletedRepository
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.models.models import WhatsAppMessage, TelegramMessage, Evidence, DeletedMessage
from forensic.deleted.detector import DeletedDetector
from backend.services.log_service import get_log_service


class DeletedService:
    """Service for deleted message detection operations."""

    def __init__(self):
        self.deleted_repo = DeletedRepository()
        self.whatsapp_repo = WhatsAppRepository()
        self.telegram_repo = TelegramRepository()
        self.detector = DeletedDetector()

    def detect_deletions_for_case(self, db: Session, case_id: int) -> int:
        """
        Detect deleted messages for a case by analyzing WhatsApp and Telegram messages.
        Deletes existing deleted message records for the case before redetecting.

        Returns:
            Number of deleted message records created.
        """
        # Get log service
        log_service = get_log_service(db)

        # Log analysis start
        log_service.log_analysis(
            evidence_id=None,  # Case-level analysis
            log_type="deleted_detection_start",
            message="Starting deleted message detection for case",
            details={"case_id": case_id}
        )

        try:
            # Delete existing deleted message records for this case
            db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).delete()
            db.commit()

            # Get all evidence IDs for this case
            evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
            evidence_ids = [e.id for e in evidences]

            all_detected_deletions = []

            # Process WhatsApp messages
            for evidence_id in evidence_ids:
                wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence_id)
                if wa_messages:
                    deletions = self.detector.detect_deletions(
                        messages=wa_messages,
                        source_app="whatsapp",
                        evidence_id=evidence_id,
                        case_id=case_id
                    )
                    all_detected_deletions.extend(deletions)

            # Process Telegram messages
            for evidence_id in evidence_ids:
                tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence_id)
                if tg_messages:
                    deletions = self.detector.detect_deletions(
                        messages=tg_messages,
                        source_app="telegram",
                        evidence_id=evidence_id,
                        case_id=case_id
                    )
                    all_detected_deletions.extend(deletions)

            # Save detected deletions
            if all_detected_deletions:
                self.deleted_repo.save_deleted_messages(db, all_detected_deletions)

            # Log analysis success
            log_service.log_analysis(
                evidence_id=None,
                log_type="deleted_detection_completed",
                message="Deleted message detection completed successfully",
                details={"case_id": case_id, "deletions_detected": len(all_detected_deletions)}
            )

            return len(all_detected_deletions)
        except Exception as e:
            # Log error
            log_service.log_error(
                error_type="deleted_detection_error",
                message=f"Error during deleted message detection: {str(e)}",
                case_id=case_id,
                evidence_id=None,
                stack_trace=traceback.format_exc(),
                endpoint="/api/cases/{case_id}/deleted/detect",
                method="POST"
            )
            return 0

    def get_deleted_messages_for_case(self, db: Session, case_id: int) -> List[dict]:
        """Get deleted messages for a case."""
        messages = self.deleted_repo.get_deleted_messages_by_case_id(db, case_id)
        return [
            {
                "id": m.id,
                "case_id": m.case_id,
                "evidence_id": m.evidence_id,
                "source_app": m.source_app,
                "chat_jid": m.chat_jid,
                "gap_start": m.gap_start,
                "gap_end": m.gap_end,
                "missing_count": m.missing_count,
                "confidence_score": m.confidence_score,
                "detection_method": m.detection_method,
                "detected_at": m.detected_at.isoformat() if m.detected_at else None,
            }
            for m in messages
        ]


deleted_service = DeletedService()