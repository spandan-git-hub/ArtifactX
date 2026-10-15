"""Repository for Telegram analysis data (spec B9.6)."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.models import (
    TelegramChat,
    TelegramContact,
    TelegramDialog,
    TelegramGroup,
    TelegramMessage,
    TelegramUnparsedBlob,
    TelegramUser,
)
from forensic.telegram.models import TgParseResult


class TelegramRepository:
    """Repository for Telegram analysis data operations."""

    def clear_telegram_data(self, db: Session, evidence_id: int) -> None:
        """Idempotently clear all extracted Telegram records for evidence in current transaction (B9.6)."""
        db.query(TelegramMessage).filter(TelegramMessage.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramDialog).filter(TelegramDialog.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramUser).filter(TelegramUser.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramChat).filter(TelegramChat.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramUnparsedBlob).filter(TelegramUnparsedBlob.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramContact).filter(TelegramContact.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramGroup).filter(TelegramGroup.evidence_id == evidence_id).delete(synchronize_session=False)

    def save_parse_result(self, db: Session, evidence_id: int, result: TgParseResult) -> None:
        """Persist complete TgParseResult records idempotently in one transaction (B9.6)."""
        self.clear_telegram_data(db, evidence_id)

        # 1. Dialogs
        for d in result.dialogs:
            row = TelegramDialog(
                evidence_id=evidence_id,
                dialog_id=d.dialog_id,
                peer_kind=d.peer_kind,
                peer_id=d.peer_id,
                title=d.title,
                last_mid=d.last_mid,
                unread_count=d.unread_count,
                pinned=d.pinned,
                finding_id=d.finding_id,
                provenance=d.provenance.to_dict(),
                limitations=list(d.limitations),
            )
            db.add(row)

        # 2. Users
        for u in result.users:
            row = TelegramUser(
                evidence_id=evidence_id,
                uid=u.uid,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                phone=u.phone,
                is_self=u.is_self,
                contact=u.contact,
                deleted=u.deleted,
                bot=u.bot,
                finding_id=u.finding_id,
                provenance=u.provenance.to_dict(),
            )
            db.add(row)
            # Legacy contact mapping
            c_row = TelegramContact(
                evidence_id=evidence_id,
                user_id=u.uid,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                phone=u.phone,
            )
            db.add(c_row)

        # 3. Chats
        for c in result.chats:
            row = TelegramChat(
                evidence_id=evidence_id,
                did=c.did,
                chat_id=c.chat_id,
                title=c.title,
                is_channel=c.is_channel,
                is_group=c.is_group,
                participants_count=c.participants_count,
                participant_uids=list(c.participant_uids),
                finding_id=c.finding_id,
                provenance=c.provenance.to_dict(),
            )
            db.add(row)
            # Legacy group mapping
            g_row = TelegramGroup(
                evidence_id=evidence_id,
                group_id=c.chat_id,
                title=c.title,
                username=None,
                type="channel" if c.is_channel else "group",
            )
            db.add(g_row)

        # 4. Messages
        for m in result.messages:
            row = TelegramMessage(
                evidence_id=evidence_id,
                mid=m.mid,
                message_id=m.mid,
                dialog_id=str(m.dialog_id),
                from_id=m.from_id,
                sender_id=m.from_id,
                out=m.out,
                text=m.text,
                body=m.text,
                date_raw=m.date_raw,
                date_unit=m.date_unit,
                date_utc_ms=m.date_utc_ms,
                timestamp=m.date_utc_ms,
                media_kind=m.media_kind,
                media_type=m.media_kind,
                media_ref=m.media_ref,
                media_path=m.media_ref,
                message_type="chat",
                reply_to_mid=m.reply_to_mid,
                geo_lat=m.geo_lat,
                geo_lon=m.geo_lon,
                entities=list(m.entities),
                flags=list(m.flags),
                read_state=m.read_state,
                send_state=m.send_state,
                view=m.view,
                source_table="messages_v2",
                source_row_id=m.mid,
                finding_id=m.finding_id,
                confidence_score=m.confidence_score,
                strength=m.strength,
                provenance=m.provenance.to_dict(),
                limitations=list(m.limitations),
                trailing_bytes_info=m.trailing_bytes_info,
            )
            db.add(row)

        # 5. Unparsed Blobs
        for b in result.unparsed_blobs:
            row = TelegramUnparsedBlob(
                evidence_id=evidence_id,
                table=b.table,
                row_id=b.row_id,
                mid=b.mid,
                uid=b.uid,
                constructor_id_hex=b.constructor_id_hex,
                length=b.length,
                sha256=b.sha256,
                reason=b.reason,
                container_metadata=b.container_metadata,
                finding_id=b.finding_id,
                provenance=b.provenance.to_dict(),
            )
            db.add(row)

        db.commit()

    def get_messages_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramMessage]:
        """Get Telegram messages by evidence ID."""
        return db.query(TelegramMessage).filter(
            TelegramMessage.evidence_id == evidence_id
        ).order_by(TelegramMessage.mid.asc(), TelegramMessage.id.asc()).all()

    def get_dialogs_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramDialog]:
        """Get Telegram dialogs by evidence ID."""
        return db.query(TelegramDialog).filter(
            TelegramDialog.evidence_id == evidence_id
        ).order_by(TelegramDialog.dialog_id.asc()).all()

    def get_users_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramUser]:
        """Get Telegram users by evidence ID."""
        return db.query(TelegramUser).filter(
            TelegramUser.evidence_id == evidence_id
        ).order_by(TelegramUser.uid.asc()).all()

    def get_chats_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramChat]:
        """Get Telegram chats by evidence ID."""
        return db.query(TelegramChat).filter(
            TelegramChat.evidence_id == evidence_id
        ).order_by(TelegramChat.did.asc()).all()

    def get_unparsed_blobs_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramUnparsedBlob]:
        """Get Telegram unparsed blobs by evidence ID."""
        return db.query(TelegramUnparsedBlob).filter(
            TelegramUnparsedBlob.evidence_id == evidence_id
        ).order_by(TelegramUnparsedBlob.id.asc()).all()

    def get_contacts_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramContact]:
        """Get Telegram contacts by evidence ID (legacy endpoint compatibility)."""
        return db.query(TelegramContact).filter(
            TelegramContact.evidence_id == evidence_id
        ).order_by(TelegramContact.first_name.asc(), TelegramContact.id.asc()).all()

    def get_groups_by_evidence_id(self, db: Session, evidence_id: int) -> List[TelegramGroup]:
        """Get Telegram groups by evidence ID (legacy endpoint compatibility)."""
        return db.query(TelegramGroup).filter(
            TelegramGroup.evidence_id == evidence_id
        ).order_by(TelegramGroup.title.asc(), TelegramGroup.id.asc()).all()