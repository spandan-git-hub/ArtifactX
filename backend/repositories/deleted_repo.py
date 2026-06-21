"""Repository for Deleted Message data."""

from typing import List
from sqlalchemy.orm import Session

from backend.models.models import DeletedMessage


class DeletedRepository:
    """Repository for Deleted Message data operations."""

    def save_deleted_messages(self, db: Session, messages: List[dict]):
        """Save deleted messages to database."""
        for msg_data in messages:
            # Check if deleted message already exists (by case_id, evidence_id, chat_jid, gap_start, gap_end)
            existing = db.query(DeletedMessage).filter(
                DeletedMessage.case_id == msg_data["case_id"],
                DeletedMessage.evidence_id == msg_data["evidence_id"],
                DeletedMessage.chat_jid == msg_data["chat_jid"],
                DeletedMessage.gap_start == msg_data["gap_start"],
                DeletedMessage.gap_end == msg_data["gap_end"]
            ).first()

            if not existing:
                message = DeletedMessage(**msg_data)
                db.add(message)

        db.commit()

    def get_deleted_messages_by_case_id(self, db: Session, case_id: int) -> List[DeletedMessage]:
        """Get deleted messages by case ID."""
        return db.query(DeletedMessage).filter(
            DeletedMessage.case_id == case_id
        ).order_by(DeletedMessage.detected_at.desc()).all()

    def get_deleted_messages_by_case_and_evidence(self, db: Session, case_id: int, evidence_id: int) -> List[DeletedMessage]:
        """Get deleted messages by case ID and evidence ID."""
        return db.query(DeletedMessage).filter(
            DeletedMessage.case_id == case_id,
            DeletedMessage.evidence_id == evidence_id
        ).order_by(DeletedMessage.detected_at.desc()).all()