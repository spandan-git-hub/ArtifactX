"""
Repository for WhatsApp forensic analysis data operations (spec B7.5).
Supports idempotent transaction-safe storage, provenance tracking, and zero-BYTEA queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.models import (
    WhatsAppChat,
    WhatsAppContact,
    WhatsAppEdit,
    WhatsAppGroup,
    WhatsAppJid,
    WhatsAppMessage,
    WhatsAppRevocation,
)

if TYPE_CHECKING:
    from forensic.whatsapp.parser import WAParseResult


class WhatsAppRepository:
    """Repository for WhatsApp analysis data operations."""

    def clear_whatsapp_data(self, db: Session, evidence_id: int) -> None:
        """
        Delete all existing WhatsApp artifacts for a given evidence ID.
        Ensures idempotent re-runs per spec B7.5.
        """
        db.query(WhatsAppRevocation).filter(WhatsAppRevocation.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppEdit).filter(WhatsAppEdit.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppChat).filter(WhatsAppChat.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppJid).filter(WhatsAppJid.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppGroup).filter(WhatsAppGroup.evidence_id == evidence_id).delete(synchronize_session=False)

    def save_parse_result(
        self,
        db: Session,
        evidence_id: int,
        parse_result: WAParseResult,
        derived_artifact_id: Optional[str] = None,
    ) -> None:
        """
        Persist complete WhatsApp forensic extraction atomically and idempotently (B7.5).
        Replaces any prior extraction for this evidence in a single transaction.
        """
        self.clear_whatsapp_data(db, evidence_id)

        # 1. Persist Chats
        for c in parse_result.chats:
            chat_row = WhatsAppChat(
                evidence_id=evidence_id,
                chat_row_id=c.chat_row_id,
                jid=c.chat_jid,
                subject=c.subject,
                is_group=c.is_group,
                hidden=c.hidden,
                archived=c.archived,
                last_message_row_id=c.last_message_row_id,
                participant_jids=list(c.participant_jids),
                provenance=c.provenance.to_dict(),
            )
            db.add(chat_row)

            # Also maintain legacy WhatsAppGroup if group
            if c.is_group:
                grp_row = WhatsAppGroup(
                    evidence_id=evidence_id,
                    group_jid=c.chat_jid,
                    subject=c.subject or c.chat_jid,
                    creator_jid=c.participant_jids[0] if c.participant_jids else None,
                    creation_timestamp=None,
                )
                db.add(grp_row)

        # 2. Persist Contacts
        for cnt in parse_result.contacts:
            cnt_row = WhatsAppContact(
                evidence_id=evidence_id,
                jid=cnt.jid,
                display_name=cnt.display_name,
                phone_number=cnt.phone_number,
                status=None,
            )
            db.add(cnt_row)

            # Persist JID record
            jid_row = WhatsAppJid(
                evidence_id=evidence_id,
                jid_row_id=cnt.provenance.row_id,
                raw_string=cnt.jid,
                user=cnt.phone_number or cnt.jid.split("@")[0],
                server=cnt.jid.split("@")[1] if "@" in cnt.jid else None,
                jid_type=1 if cnt.is_group else 0,
                phone_number=cnt.phone_number,
                is_group=cnt.is_group,
                provenance=cnt.provenance.to_dict(),
            )
            db.add(jid_row)

        # 3. Persist Messages
        for m in parse_result.messages:
            msg_row = WhatsAppMessage(
                evidence_id=evidence_id,
                message_id=m.key_id,
                key_id=m.key_id,
                chat_row_id=m.chat_row_id,
                key_remote_jid=m.chat_jid,
                sender_jid="me" if m.from_me == 1 else (m.sender_jid or m.chat_jid),
                participant_jid=m.chat_jid if m.from_me == 1 else "me",
                body=m.text,
                timestamp=m.ts_utc_ms,
                ts_raw=m.ts_raw,
                ts_unit=m.ts_unit,
                ts_utc_ms=m.ts_utc_ms,
                received_ts_raw=m.received_ts_raw,
                media_type=m.media_ref.mime_type if m.media_ref else None,
                media_path=m.media_ref.file_path if m.media_ref else None,
                message_type=m.message_type_name,
                message_type_code=m.message_type_code,
                message_type_name=m.message_type_name,
                status=str(m.status),
                source_table=m.provenance.source_table,
                source_row_id=m.provenance.row_id,
                derived_artifact_id=derived_artifact_id,
                evidence_sha256=m.provenance.evidence_sha256,
                quoted_row_id=m.quoted_ref.quoted_row_id if m.quoted_ref else None,
                location_lat=m.location_ref.latitude if m.location_ref else None,
                location_lon=m.location_ref.longitude if m.location_ref else None,
                is_revoked=("revoked" in m.flags),
                is_edited=("edited" in m.flags),
                flags=list(m.flags),
            )
            db.add(msg_row)

        # 4. Persist Revocations
        for r in parse_result.revocations:
            rev_row = WhatsAppRevocation(
                evidence_id=evidence_id,
                derived_artifact_id=derived_artifact_id,
                message_row_id=r.message_row_id,
                revoked_key_id=r.revoked_key_id,
                revoke_ts=r.revoke_ts,
                admin_jid=r.admin_jid,
                original_sender=r.original_sender,
                original_ts=r.original_ts,
                finding_id=r.finding_id,
                confidence_score=r.confidence_score,
                strength=r.strength,
                limitations=list(r.limitations),
                provenance=r.provenance.to_dict(),
            )
            db.add(rev_row)

        # 5. Persist Edits
        for e in parse_result.edits:
            edit_row = WhatsAppEdit(
                evidence_id=evidence_id,
                derived_artifact_id=derived_artifact_id,
                message_row_id=e.message_row_id,
                original_key_id=e.original_key_id,
                edited_ts=e.edited_ts,
                sender_ts=e.sender_ts,
                prior_text_not_present=e.prior_text_not_present,
                edited_text=e.edited_text,
                finding_id=e.finding_id,
                confidence_score=e.confidence_score,
                strength=e.strength,
                limitations=list(e.limitations),
                provenance=e.provenance.to_dict(),
            )
            db.add(edit_row)

        db.commit()

    # Legacy compatibility methods
    def save_messages(self, db: Session, messages: List[dict]):
        """Legacy helper for backward compatibility."""
        for msg_data in messages:
            existing = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id == msg_data["evidence_id"],
                WhatsAppMessage.message_id == msg_data["message_id"]
            ).first()
            if not existing:
                db.add(WhatsAppMessage(**msg_data))
        db.commit()

    def save_contacts(self, db: Session, contacts: List[dict]):
        for contact_data in contacts:
            existing = db.query(WhatsAppContact).filter(
                WhatsAppContact.evidence_id == contact_data["evidence_id"],
                WhatsAppContact.jid == contact_data["jid"]
            ).first()
            if not existing:
                db.add(WhatsAppContact(**contact_data))
        db.commit()

    def save_groups(self, db: Session, groups: List[dict]):
        for group_data in groups:
            existing = db.query(WhatsAppGroup).filter(
                WhatsAppGroup.evidence_id == group_data["evidence_id"],
                WhatsAppGroup.group_jid == group_data["group_jid"]
            ).first()
            if not existing:
                db.add(WhatsAppGroup(**group_data))
        db.commit()

    def get_messages_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppMessage]:
        """Get WhatsApp messages by evidence ID in deterministic timestamp/row order."""
        return db.query(WhatsAppMessage).filter(
            WhatsAppMessage.evidence_id == evidence_id
        ).order_by(WhatsAppMessage.timestamp.asc(), WhatsAppMessage.id.asc()).all()

    def get_chats_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppChat]:
        """Get WhatsApp chats by evidence ID."""
        return db.query(WhatsAppChat).filter(
            WhatsAppChat.evidence_id == evidence_id
        ).order_by(WhatsAppChat.chat_row_id.asc(), WhatsAppChat.id.asc()).all()

    def get_contacts_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppContact]:
        """Get WhatsApp contacts by evidence ID."""
        return db.query(WhatsAppContact).filter(
            WhatsAppContact.evidence_id == evidence_id
        ).order_by(WhatsAppContact.display_name.asc()).all()

    def get_groups_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppGroup]:
        """Get WhatsApp groups by evidence ID."""
        return db.query(WhatsAppGroup).filter(
            WhatsAppGroup.evidence_id == evidence_id
        ).order_by(WhatsAppGroup.subject.asc()).all()

    def get_revocations_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppRevocation]:
        """Get WhatsApp revocation findings by evidence ID."""
        return db.query(WhatsAppRevocation).filter(
            WhatsAppRevocation.evidence_id == evidence_id
        ).order_by(WhatsAppRevocation.id.asc()).all()

    def get_edits_by_evidence_id(self, db: Session, evidence_id: int) -> List[WhatsAppEdit]:
        """Get WhatsApp edit findings by evidence ID."""
        return db.query(WhatsAppEdit).filter(
            WhatsAppEdit.evidence_id == evidence_id
        ).order_by(WhatsAppEdit.id.asc()).all()