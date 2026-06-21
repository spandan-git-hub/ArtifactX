"""Repository for WhatsApp analysis data."""

from typing import List
from sqlalchemy.orm import Session

from backend.models.models import WhatsAppMessage, WhatsAppContact, WhatsAppGroup


class WhatsAppRepository:
    """Repository for WhatsApp analysis data operations."""

    def save_messages(self, db: Session, messages: List[dict]):
        """Save WhatsApp messages to database."""
        for msg_data in messages:
            # Check if message already exists (by message_id and evidence_id)
            existing = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id == msg_data["evidence_id"],
                WhatsAppMessage.message_id == msg_data["message_id"]
            ).first()

            if not existing:
                message = WhatsAppMessage(**msg_data)
                db.add(message)

        db.commit()

    def save_contacts(self, db: Session, contacts: List[dict]):
        """Save WhatsApp contacts to database."""
        for contact_data in contacts:
            # Check if contact already exists (by jid and evidence_id)
            existing = db.query(WhatsAppContact).filter(
                WhatsAppContact.evidence_id == contact_data["evidence_id"],
                WhatsAppContact.jid == contact_data["jid"]
            ).first()

            if not existing:
                contact = WhatsAppContact(**contact_data)
                db.add(contact)

        db.commit()

    def save_groups(self, db: Session, groups: List[dict]):
        """Save WhatsApp groups to database."""
        for group_data in groups:
            # Check if group already exists (by group_jid and evidence_id)
            existing = db.query(WhatsAppGroup).filter(
                WhatsAppGroup.evidence_id == group_data["evidence_id"],
                WhatsAppGroup.group_jid == group_data["group_jid"]
            ).first()

            if not existing:
                group = WhatsAppGroup(**group_data)
                db.add(group)

        db.commit()

    def get_messages_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppMessage]:
        """Get WhatsApp messages by evidence ID."""
        return db.query(WhatsAppMessage).filter(
            WhatsAppMessage.evidence_id == evidence_id
        ).order_by(WhatsAppMessage.timestamp).all()

    def get_contacts_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppContact]:
        """Get WhatsApp contacts by evidence ID."""
        return db.query(WhatsAppContact).filter(
            WhatsAppContact.evidence_id == evidence_id
        ).order_by(WhatsAppContact.display_name).all()

    def get_groups_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppGroup]:
        """Get WhatsApp groups by evidence ID."""
        return db.query(WhatsAppGroup).filter(
            WhatsAppGroup.evidence_id == evidence_id
        ).order_by(WhatsAppGroup.subject).all()