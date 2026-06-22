"""Search repository for data access."""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import or_, and_, func, text
from sqlalchemy.orm import Session

from backend.models.models import (
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
    Evidence,
    Case,
)


def timestamp_to_datetime(ts: int) -> datetime:
    """Convert Unix timestamp (milliseconds) to datetime."""
    return datetime.fromtimestamp(ts / 1000) if ts else None


class SearchRepository:
    """Repository for search queries."""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Message Search ====================

    def search_messages(
        self,
        case_id: int,
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        app: str = "all",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[dict], int]:
        """
        Search messages across WhatsApp and Telegram.

        Returns (results, total_count).
        """
        results = []
        total = 0

        # Convert datetime to timestamp for comparison
        date_from_ts = int(date_from.timestamp() * 1000) if date_from else None
        date_to_ts = int(date_to.timestamp() * 1000) if date_to else None

        if app in ("all", "whatsapp"):
            wa_results, wa_total = self._search_wa_messages(
                case_id, query, date_from_ts, date_to_ts, page, page_size
            )
            results.extend(wa_results)
            total += wa_total

        if app in ("all", "telegram"):
            tg_results, tg_total = self._search_tg_messages(
                case_id, query, date_from_ts, date_to_ts, page, page_size
            )
            results.extend(tg_results)
            total += tg_total

        # Sort by timestamp descending
        results.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)

        # Apply pagination to combined results
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]

        return paginated_results, total

    def _search_wa_messages(
        self,
        case_id: int,
        query: Optional[str],
        date_from: Optional[int],
        date_to: Optional[int],
        page: int,
        page_size: int,
    ) -> Tuple[List[dict], int]:
        """Search WhatsApp messages."""
        # Get evidence IDs for this case
        evidence_ids = self._get_evidence_ids(case_id, "whatsapp")

        if not evidence_ids:
            return [], 0

        # Build query
        stmt = self.db.query(WhatsAppMessage).filter(
            WhatsAppMessage.evidence_id.in_(evidence_ids) if evidence_ids else False
        )

        # Apply text search
        if query:
            stmt = stmt.filter(WhatsAppMessage.body.ilike(f"%{query}%"))

        # Apply date filters
        if date_from:
            stmt = stmt.filter(WhatsAppMessage.timestamp >= date_from)
        if date_to:
            stmt = stmt.filter(WhatsAppMessage.timestamp <= date_to)

        # Get total count
        total = stmt.count()

        # Apply pagination and order
        offset = (page - 1) * page_size
        messages = stmt.order_by(
            WhatsAppMessage.timestamp.desc()
        ).offset(offset).limit(page_size).all()

        # Convert to dict
        results = []
        for msg in messages:
            results.append({
                "id": msg.id,
                "evidence_id": msg.evidence_id,
                "app": "whatsapp",
                "message_id": msg.message_id,
                "chat_jid": msg.key_remote_jid,
                "sender": msg.sender_jid,
                "body": msg.body,
                "timestamp": timestamp_to_datetime(msg.timestamp),
                "media_type": msg.media_type,
                "media_path": msg.media_path,
                "message_type": msg.message_type,
                "status": msg.status,
            })

        return results, total

    def _search_tg_messages(
        self,
        case_id: int,
        query: Optional[str],
        date_from: Optional[int],
        date_to: Optional[int],
        page: int,
        page_size: int,
    ) -> Tuple[List[dict], int]:
        """Search Telegram messages."""
        # Get evidence IDs for this case
        evidence_ids = self._get_evidence_ids(case_id, "telegram")

        if not evidence_ids:
            return [], 0

        # Build query
        stmt = self.db.query(TelegramMessage).filter(
            TelegramMessage.evidence_id.in_(evidence_ids) if evidence_ids else False
        )

        # Apply text search
        if query:
            stmt = stmt.filter(TelegramMessage.body.ilike(f"%{query}%"))

        # Apply date filters
        if date_from:
            stmt = stmt.filter(TelegramMessage.timestamp >= date_from)
        if date_to:
            stmt = stmt.filter(TelegramMessage.timestamp <= date_to)

        # Get total count
        total = stmt.count()

        # Apply pagination and order
        offset = (page - 1) * page_size
        messages = stmt.order_by(
            TelegramMessage.timestamp.desc()
        ).offset(offset).limit(page_size).all()

        # Convert to dict
        results = []
        for msg in messages:
            results.append({
                "id": msg.id,
                "evidence_id": msg.evidence_id,
                "app": "telegram",
                "message_id": str(msg.message_id),
                "chat_jid": msg.dialog_id,
                "sender": str(msg.sender_id),
                "body": msg.body,
                "timestamp": timestamp_to_datetime(msg.timestamp),
                "media_type": msg.media_type,
                "media_path": msg.media_path,
                "message_type": msg.message_type,
                "status": None,
            })

        return results, total

    # ==================== Contact Search ====================

    def search_contacts(
        self,
        case_id: int,
        query: Optional[str] = None,
        app: str = "all",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[dict], int]:
        """
        Search contacts across WhatsApp and Telegram.

        Returns (results, total_count).
        """
        results = []
        total = 0

        if app in ("all", "whatsapp"):
            wa_results, wa_total = self._search_wa_contacts(
                case_id, query, page, page_size
            )
            results.extend(wa_results)
            total += wa_total

        if app in ("all", "telegram"):
            tg_results, tg_total = self._search_tg_contacts(
                case_id, query, page, page_size
            )
            results.extend(tg_results)
            total += tg_total

        # Sort by display_name/title
        results.sort(key=lambda x: x.get("display_name") or "")

        # Apply pagination to combined results
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]

        return paginated_results, total

    def _search_wa_contacts(
        self,
        case_id: int,
        query: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[dict], int]:
        """Search WhatsApp contacts."""
        evidence_ids = self._get_evidence_ids(case_id, "whatsapp")

        if not evidence_ids:
            return [], 0

        stmt = self.db.query(WhatsAppContact).filter(
            WhatsAppContact.evidence_id.in_(evidence_ids) if evidence_ids else False
        )

        # Apply text search on display_name, phone, jid
        if query:
            stmt = stmt.filter(
                or_(
                    WhatsAppContact.display_name.ilike(f"%{query}%"),
                    WhatsAppContact.phone_number.ilike(f"%{query}%"),
                    WhatsAppContact.jid.ilike(f"%{query}%"),
                    WhatsAppContact.status.ilike(f"%{query}%"),
                )
            )

        total = stmt.count()

        offset = (page - 1) * page_size
        contacts = stmt.order_by(
            WhatsAppContact.display_name.asc()
        ).offset(offset).limit(page_size).all()

        results = []
        for contact in contacts:
            results.append({
                "id": contact.id,
                "evidence_id": contact.evidence_id,
                "app": "whatsapp",
                "jid": contact.jid,
                "display_name": contact.display_name,
                "phone": contact.phone_number,
                "username": None,
                "status": contact.status,
            })

        return results, total

    def _search_tg_contacts(
        self,
        case_id: int,
        query: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[dict], int]:
        """Search Telegram contacts."""
        evidence_ids = self._get_evidence_ids(case_id, "telegram")

        if not evidence_ids:
            return [], 0

        stmt = self.db.query(TelegramContact).filter(
            TelegramContact.evidence_id.in_(evidence_ids) if evidence_ids else False
        )

        # Apply text search on name, username, phone
        if query:
            stmt = stmt.filter(
                or_(
                    TelegramContact.first_name.ilike(f"%{query}%"),
                    TelegramContact.last_name.ilike(f"%{query}%"),
                    TelegramContact.username.ilike(f"%{query}%"),
                    TelegramContact.phone.ilike(f"%{query}%"),
                )
            )

        total = stmt.count()

        offset = (page - 1) * page_size
        contacts = stmt.order_by(
            TelegramContact.first_name.asc()
        ).offset(offset).limit(page_size).all()

        results = []
        for contact in contacts:
            display_name = " ".join(
                filter(None, [contact.first_name, contact.last_name])
            ) or contact.username or contact.phone
            results.append({
                "id": contact.id,
                "evidence_id": contact.evidence_id,
                "app": "telegram",
                "jid": None,
                "display_name": display_name,
                "phone": contact.phone,
                "username": contact.username,
                "status": None,
            })

        return results, total

    # ==================== Media Search ====================

    def search_media(
        self,
        case_id: int,
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        app: str = "all",
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[dict], int]:
        """
        Search media items.

        Returns (results, total_count).
        """
        stmt = self.db.query(MediaItem).filter(MediaItem.case_id == case_id)

        # Apply text search on file_path
        if query:
            stmt = stmt.filter(MediaItem.file_path.ilike(f"%{query}%"))

        # Apply media type filter
        if media_type and media_type != "all":
            stmt = stmt.filter(MediaItem.media_type == media_type)

        total = stmt.count()

        offset = (page - 1) * page_size
        media_items = stmt.order_by(
            MediaItem.id.desc()
        ).offset(offset).limit(page_size).all()

        results = []
        for item in media_items:
            results.append({
                "id": item.id,
                "case_id": item.case_id,
                "evidence_id": item.evidence_id,
                "file_path": item.file_path,
                "sha256": item.sha256,
                "mime_type": item.mime_type,
                "media_type": item.media_type,
                "file_size": item.file_size,
                "width": item.width,
                "height": item.height,
                "duration": item.duration,
                "is_orphan": item.is_orphan,
                "linked_message_id": item.linked_message_id,
            })

        return results, total

    # ==================== Global Search ====================

    def global_search(
        self,
        case_id: int,
        query: str,
        app: str = "all",
        limit: int = 20,
    ) -> dict:
        """
        Perform global search across messages, contacts, and media.

        Returns dict with categorized results.
        """
        # Get message results
        msg_results, msg_total = self.search_messages(
            case_id, query, app=app, page=1, page_size=limit
        )

        # Get contact results
        contact_results, contact_total = self.search_contacts(
            case_id, query, app=app, page=1, page_size=limit
        )

        # Get media results
        media_results, media_total = self.search_media(
            case_id, query, app=app, page=1, page_size=limit
        )

        return {
            "query": query,
            "messages": msg_results,
            "contacts": contact_results,
            "media": media_results,
            "total_results": msg_total + contact_total + media_total,
            "counts": {
                "messages": msg_total,
                "contacts": contact_total,
                "media": media_total,
            }
        }

    # ==================== Helper Methods ====================

    def _get_evidence_ids(self, case_id: int, app: str) -> List[int]:
        """Get evidence IDs for a case filtered by app type."""
        stmt = self.db.query(Evidence.id).filter(Evidence.case_id == case_id)

        evidence_records = stmt.all()
        return [e.id for e in evidence_records]

    def get_search_summary(self, case_id: int) -> dict:
        """Get summary statistics for search."""
        # Get WA stats
        wa_evidence_ids = self._get_evidence_ids(case_id, "whatsapp")
        wa_msg_count = 0
        wa_contact_count = 0
        if wa_evidence_ids:
            wa_msg_count = self.db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id.in_(wa_evidence_ids)
            ).count()
            wa_contact_count = self.db.query(WhatsAppContact).filter(
                WhatsAppContact.evidence_id.in_(wa_evidence_ids)
            ).count()

        # Get TG stats
        tg_evidence_ids = self._get_evidence_ids(case_id, "telegram")
        tg_msg_count = 0
        tg_contact_count = 0
        if tg_evidence_ids:
            tg_msg_count = self.db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id.in_(tg_evidence_ids)
            ).count()
            tg_contact_count = self.db.query(TelegramContact).filter(
                TelegramContact.evidence_id.in_(tg_evidence_ids)
            ).count()

        # Get media count
        media_count = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).count()

        # Get date range
        first_msg_ts = None
        last_msg_ts = None

        if wa_evidence_ids:
            first_wa = self.db.query(WhatsAppMessage.timestamp).filter(
                WhatsAppMessage.evidence_id.in_(wa_evidence_ids)
            ).order_by(WhatsAppMessage.timestamp.asc()).first()
            last_wa = self.db.query(WhatsAppMessage.timestamp).filter(
                WhatsAppMessage.evidence_id.in_(wa_evidence_ids)
            ).order_by(WhatsAppMessage.timestamp.desc()).first()
            if first_wa:
                first_msg_ts = first_wa[0]
            if last_wa:
                last_msg_ts = last_wa[0]

        if not first_msg_ts and tg_evidence_ids:
            first_tg = self.db.query(TelegramMessage.timestamp).filter(
                TelegramMessage.evidence_id.in_(tg_evidence_ids)
            ).order_by(TelegramMessage.timestamp.asc()).first()
            last_tg = self.db.query(TelegramMessage.timestamp).filter(
                TelegramMessage.evidence_id.in_(tg_evidence_ids)
            ).order_by(TelegramMessage.timestamp.desc()).first()
            if first_tg:
                first_msg_ts = first_tg[0]
            if last_tg:
                last_msg_ts = last_tg[0]

        apps = []
        if wa_evidence_ids:
            apps.append("whatsapp")
        if tg_evidence_ids:
            apps.append("telegram")

        return {
            "total_messages": wa_msg_count + tg_msg_count,
            "total_contacts": wa_contact_count + tg_contact_count,
            "total_media": media_count,
            "date_range_start": timestamp_to_datetime(first_msg_ts) if first_msg_ts else None,
            "date_range_end": timestamp_to_datetime(last_msg_ts) if last_msg_ts else None,
            "apps": apps,
        }