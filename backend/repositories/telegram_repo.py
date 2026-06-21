"""Repository for Telegram analysis data."""

from typing import List
from sqlalchemy.orm import Session

from backend.models.models import TelegramMessage, TelegramContact, TelegramGroup


class TelegramRepository:
    """Repository for Telegram analysis data operations."""

    def save_messages(self, db: Session, messages: List[dict]):
        """Save Telegram messages to database."""
        for msg_data in messages:
            # Check if message already exists (by message_id and evidence_id)
            existing = db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id == msg_data["evidence_id"],
                TelegramMessage.message_id == msg_data["message_id"]
            ).first()

            if not existing:
                message = TelegramMessage(**msg_data)
                db.add(message)

        db.commit()

    def save_contacts(self, db: Session, contacts: List[dict]):
        """Save Telegram contacts to database."""
        for contact_data in contacts:
            # Check if contact already exists (by user_id and evidence_id)
            existing = db.query(TelegramContact).filter(
                TelegramContact.evidence_id == contact_data["evidence_id"],
                TelegramContact.user_id == contact_data["user_id"]
            ).first()

            if not existing:
                contact = TelegramContact(**contact_data)
                db.add(contact)

        db.commit()

    def save_groups(self, db: Session, groups: List[dict]):
        """Save Telegram groups to database."""
        for group_data in groups:
            # Check if group already exists (by group_id and evidence_id)
            existing = db.query(TelegramGroup).filter(
                TelegramGroup.evidence_id == group_data["evidence_id"],
                TelegramGroup.group_id == group_data["group_id"]
            ).first()

            if not existing:
                group = TelegramGroup(**group_data)
                db.add(group)

        db.commit()

    def get_messages_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramMessage]:
        """Get Telegram messages by evidence ID."""
        return db.query(TelegramMessage).filter(
            TelegramMessage.evidence_id == evidence_id
        ).order_by(TelegramMessage.timestamp).all()

    def get_contacts_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramContact]:
        """Get Telegram contacts by evidence ID."""
        return db.query(TelegramContact).filter(
            TelegramContact.evidence_id == evidence_id
        ).order_by(TelegramContact.first_name).all()

    def get_groups_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramGroup]:
        """Get Telegram groups by evidence ID."""
        return db.query(TelegramGroup).filter(
            TelegramGroup.evidence_id == evidence_id
        ).order_by(TelegramGroup.title).all()