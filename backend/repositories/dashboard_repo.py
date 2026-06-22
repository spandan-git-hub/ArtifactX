"""Dashboard repository for data access."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from backend.models.models import (
    Case,
    Evidence,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppGroup,
    TelegramMessage,
    TelegramContact,
    TelegramGroup,
    TimelineEvent,
    MediaItem,
    DeletedMessage,
    CorrelationEdge,
)


def timestamp_to_datetime(ts: int) -> Optional[datetime]:
    """Convert Unix timestamp (milliseconds) to datetime."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000)


class DashboardRepository:
    """Repository for dashboard queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_case_stats(self, case_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a case."""
        evidence_ids = self._get_evidence_ids(case_id)

        # Get evidence by app type
        wa_evidence_ids = self._get_evidence_ids(case_id, "whatsapp")
        tg_evidence_ids = self._get_evidence_ids(case_id, "telegram")

        # WhatsApp stats
        wa_stats = self._get_app_stats(wa_evidence_ids, "whatsapp") if wa_evidence_ids else {
            "message_count": 0,
            "contact_count": 0,
            "group_count": 0,
            "media_count": 0,
            "first_activity": None,
            "last_activity": None,
        }

        # Telegram stats
        tg_stats = self._get_app_stats(tg_evidence_ids, "telegram") if tg_evidence_ids else {
            "message_count": 0,
            "contact_count": 0,
            "group_count": 0,
            "media_count": 0,
            "first_activity": None,
            "last_activity": None,
        }

        # Media stats
        media_count = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).count()

        # Deleted message stats
        deleted_count = self.db.query(DeletedMessage).filter(
            DeletedMessage.case_id == case_id
        ).count()

        # Total groups
        total_groups = (wa_stats.get("group_count", 0) or 0) + (tg_stats.get("group_count", 0) or 0)

        total_messages = wa_stats.get("message_count", 0) + tg_stats.get("message_count", 0)
        total_contacts = wa_stats.get("contact_count", 0) + tg_stats.get("contact_count", 0)

        return {
            "total_messages": total_messages,
            "total_contacts": total_contacts,
            "total_media": media_count,
            "total_deleted": deleted_count,
            "total_groups": total_groups,
        }

    def _get_app_stats(self, evidence_ids: List[int], app: str) -> Dict[str, Any]:
        """Get statistics for a specific app."""
        if not evidence_ids:
            return {
                "message_count": 0,
                "contact_count": 0,
                "group_count": 0,
                "media_count": 0,
                "first_activity": None,
                "last_activity": None,
            }

        if app == "whatsapp":
            message_count = self.db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).count()

            contact_count = self.db.query(WhatsAppContact).filter(
                WhatsAppContact.evidence_id.in_(evidence_ids)
            ).count()

            group_count = self.db.query(WhatsAppGroup).filter(
                WhatsAppGroup.evidence_id.in_(evidence_ids)
            ).count()

            first_msg = self.db.query(func.min(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            last_msg = self.db.query(func.max(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()

        else:  # telegram
            message_count = self.db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).count()

            contact_count = self.db.query(TelegramContact).filter(
                TelegramContact.evidence_id.in_(evidence_ids)
            ).count()

            group_count = self.db.query(TelegramGroup).filter(
                TelegramGroup.evidence_id.in_(evidence_ids)
            ).count()

            first_msg = self.db.query(func.min(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            last_msg = self.db.query(func.max(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()

        # Media count for this app
        media_count = self.db.query(MediaItem).filter(
            and_(
                MediaItem.case_id.in_(
                    e for e in self._get_case_ids_for_evidence(evidence_ids)
                ),
                MediaItem.evidence_id.in_(evidence_ids)
            )
        ).count() if self._get_case_ids_for_evidence(evidence_ids) else 0

        return {
            "message_count": message_count,
            "contact_count": contact_count,
            "group_count": group_count,
            "media_count": media_count,
            "first_activity": timestamp_to_datetime(first_msg) if first_msg else None,
            "last_activity": timestamp_to_datetime(last_msg) if last_msg else None,
        }

    def get_correlation_stats(self, case_id: int) -> Dict[str, Any]:
        """Get correlation edge statistics for a case."""
        edges = self.db.query(CorrelationEdge).filter(
            CorrelationEdge.case_id == case_id
        ).all()

        total_edges = len(edges)
        message_contact_links = 0
        message_media_links = 0
        cross_app_links = 0

        for edge in edges:
            if edge.source_type and edge.source_type.startswith("wa_message") or \
               edge.source_type and edge.source_type.startswith("tg_message"):
                if edge.target_type and ("contact" in edge.target_type or "Contact" in edge.target_type):
                    message_contact_links += 1
                if edge.target_type and "media" in edge.target_type:
                    message_media_links += 1

            # Cross-app links: WhatsApp <-> Telegram
            if edge.source_type and edge.target_type:
                source_is_wa = "wa" in edge.source_type.lower()
                target_is_tg = "tg" in edge.target_type.lower()
                source_is_tg = "tg" in edge.source_type.lower()
                target_is_wa = "wa" in edge.target_type.lower()
                if (source_is_wa and target_is_tg) or (source_is_tg and target_is_wa):
                    cross_app_links += 1

        return {
            "total_edges": total_edges,
            "message_contact_links": message_contact_links,
            "message_media_links": message_media_links,
            "cross_app_links": cross_app_links,
        }

    def get_timeline_stats(self, case_id: int) -> Dict[str, Any]:
        """Get timeline event statistics."""
        events = self.db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).all()

        total_events = len(events)
        events_by_type: Dict[str, int] = {}
        events_by_app: Dict[str, int] = {"whatsapp": 0, "telegram": 0}
        date_range_start = None
        date_range_end = None

        for event in events:
            # Count by type
            event_type = event.event_type or "unknown"
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            # Count by app
            if event.source_app:
                events_by_app[event.source_app] = events_by_app.get(event.source_app, 0) + 1

            # Date range
            if event.normalized_timestamp:
                if date_range_start is None or event.normalized_timestamp < date_range_start:
                    date_range_start = event.normalized_timestamp
                if date_range_end is None or event.normalized_timestamp > date_range_end:
                    date_range_end = event.normalized_timestamp

        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_app": events_by_app,
            "date_range_start": date_range_start,
            "date_range_end": date_range_end,
        }

    def get_recent_events(self, case_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent timeline events."""
        events = self.db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).order_by(
            TimelineEvent.normalized_timestamp.desc()
        ).limit(limit).all()

        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "source_app": event.source_app,
                "normalized_timestamp": event.normalized_timestamp,
                "description": event.description,
                "metadata": event.metadata_ or {},
            }
            for event in events
        ]

    def get_apps_for_case(self, case_id: int) -> List[str]:
        """Get list of apps with data in the case."""
        evidence_ids = self._get_evidence_ids(case_id)

        apps = []
        if evidence_ids:
            # Check WhatsApp
            wa_count = self.db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).count()
            if wa_count > 0:
                apps.append("whatsapp")

            # Check Telegram
            tg_count = self.db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).count()
            if tg_count > 0:
                apps.append("telegram")

        return apps

    def get_date_range(self, case_id: int) -> tuple:
        """Get overall date range for case data."""
        evidence_ids = self._get_evidence_ids(case_id)

        earliest = None
        latest = None

        if evidence_ids:
            # Check WhatsApp
            first_wa = self.db.query(func.min(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()
            last_wa = self.db.query(func.max(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            if first_wa:
                wa_earliest = timestamp_to_datetime(first_wa)
                if earliest is None or wa_earliest < earliest:
                    earliest = wa_earliest
            if last_wa:
                wa_latest = timestamp_to_datetime(last_wa)
                if latest is None or wa_latest > latest:
                    latest = wa_latest

            # Check Telegram
            first_tg = self.db.query(func.min(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()
            last_tg = self.db.query(func.max(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            if first_tg:
                tg_earliest = timestamp_to_datetime(first_tg)
                if earliest is None or tg_earliest < earliest:
                    earliest = tg_earliest
            if last_tg:
                tg_latest = timestamp_to_datetime(last_tg)
                if latest is None or tg_latest > latest:
                    latest = tg_latest

        return earliest, latest

    def _get_evidence_ids(self, case_id: int, app: str = None) -> List[int]:
        """Get evidence IDs for a case, optionally filtered by app type."""
        stmt = self.db.query(Evidence.id).filter(Evidence.case_id == case_id)
        evidence_records = stmt.all()
        return [e.id for e in evidence_records]

    def _get_case_ids_for_evidence(self, evidence_ids: List[int]) -> List[int]:
        """Get case IDs for given evidence IDs."""
        if not evidence_ids:
            return []
        evidence_records = self.db.query(Evidence.case_id).filter(
            Evidence.id.in_(evidence_ids)
        ).distinct().all()
        return [e[0] for e in evidence_records]