"""Report repository for data access."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.models import (
    Case,
    Evidence,
    EvidenceFile,
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


class ReportRepository:
    """Repository for report data queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_evidence_data(self, case_id: int) -> Dict[str, Any]:
        """Get evidence data for a report."""
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {}

        # Get all evidence
        evidence_items = self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()

        # Count extracted files
        total_extracted = 0
        evidence_list = []
        for ev in evidence_items:
            file_count = self.db.query(EvidenceFile).filter(
                EvidenceFile.evidence_id == ev.id
            ).count()
            total_extracted += file_count
            evidence_list.append({
                "id": ev.id,
                "filename": ev.original_filename,
                "type": ev.evidence_type,
                "file_count": file_count,
                "uploaded_at": ev.uploaded_at.isoformat() if ev.uploaded_at else None,
            })

        # Media distribution
        media_items = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).all()

        media_summary = {
            "total": len(media_items),
            "images": 0,
            "videos": 0,
            "audio": 0,
            "documents": 0,
        }
        for item in media_items:
            if item.media_type == "image":
                media_summary["images"] += 1
            elif item.media_type == "video":
                media_summary["videos"] += 1
            elif item.media_type == "audio":
                media_summary["audio"] += 1
            elif item.media_type:
                media_summary["documents"] += 1

        # Apps found
        apps = self._get_apps_for_case(case_id)

        # Date range
        date_from, date_to = self._get_date_range(case_id)

        return {
            "case_id": case_id,
            "case_name": case.name,
            "total_evidence_files": len(evidence_items),
            "total_extracted_files": total_extracted,
            "evidence_breakdown": {
                "WhatsApp databases": sum(1 for e in evidence_list if "wa" in str(e.get("filename", "")).lower()),
                "Telegram databases": sum(1 for e in evidence_list if "tg" in str(e.get("filename", "")).lower()),
                "ZIP packages": sum(1 for e in evidence_list if str(e.get("filename", "")).endswith(".zip")),
                "Other files": sum(1 for e in evidence_list if not any(x in str(e.get("filename", "")).lower() for x in ["wa", "tg", ".zip"])),
            },
            "media_summary": media_summary,
            "apps_found": apps,
            "date_range": {
                "start": date_from,
                "end": date_to,
            } if date_from or date_to else None,
            "evidence_list": evidence_list,
        }

    def get_evidence_summary(self, case_id: int) -> Dict[str, Any]:
        """Get evidence summary for a report."""
        data = self.get_evidence_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "case_name": data.get("case_name"),
            "total_evidence_files": data.get("total_evidence_files", 0),
            "total_extracted_files": data.get("total_extracted_files", 0),
            "evidence_breakdown": data.get("evidence_breakdown", {}),
            "media_summary": data.get("media_summary", {}),
            "apps_found": data.get("apps_found", []),
            "date_range": data.get("date_range"),
        }

    def get_timeline_data(self, case_id: int) -> Dict[str, Any]:
        """Get timeline data for a report."""
        events = self.db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).order_by(TimelineEvent.normalized_timestamp.asc()).all()

        total_events = len(events)
        events_by_type: Dict[str, int] = {}
        events_by_app: Dict[str, int] = {"whatsapp": 0, "telegram": 0}
        date_range_start = None
        date_range_end = None

        event_list = []
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

            event_list.append({
                "id": event.id,
                "type": event.event_type,
                "app": event.source_app,
                "timestamp": event.normalized_timestamp,
                "description": event.description,
            })

        # App breakdown
        apps = self._get_apps_for_case(case_id)
        app_breakdown = {}
        for app in apps:
            app_events = [e for e in events if e.source_app == app]
            app_breakdown[app] = {
                "total_events": len(app_events),
                "by_type": {},
            }
            for event in app_events:
                event_type = event.event_type or "unknown"
                app_breakdown[app]["by_type"][event_type] = (
                    app_breakdown[app]["by_type"].get(event_type, 0) + 1
                )

        return {
            "case_id": case_id,
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_app": events_by_app,
            "date_range": {
                "start": date_range_start,
                "end": date_range_end,
            } if date_range_start or date_range_end else None,
            "app_breakdown": app_breakdown,
            "events": event_list[:200],  # Limit for PDF
        }

    def get_timeline_summary(self, case_id: int) -> Dict[str, Any]:
        """Get timeline summary for a report."""
        data = self.get_timeline_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "total_events": data.get("total_events", 0),
            "events_by_type": data.get("events_by_type", {}),
            "events_by_app": data.get("events_by_app", {}),
            "date_range": data.get("date_range"),
            "app_breakdown": data.get("app_breakdown", {}),
        }

    def get_deleted_data(self, case_id: int) -> Dict[str, Any]:
        """Get deleted message data for a report."""
        deletions = self.db.query(DeletedMessage).filter(
            DeletedMessage.case_id == case_id
        ).order_by(DeletedMessage.detected_at.desc()).all()

        total = len(deletions)
        wa_count = sum(1 for d in deletions if d.source_app == "whatsapp")
        tg_count = sum(1 for d in deletions if d.source_app == "telegram")

        high_conf = sum(1 for d in deletions if d.confidence_score and d.confidence_score >= 0.8)
        medium_conf = sum(1 for d in deletions if d.confidence_score and 0.5 <= d.confidence_score < 0.8)
        low_conf = sum(1 for d in deletions if d.confidence_score and d.confidence_score < 0.5)

        date_from = min((d.detected_at for d in deletions if d.detected_at), default=None)
        date_to = max((d.detected_at for d in deletions if d.detected_at), default=None)

        deletion_list = [
            {
                "id": d.id,
                "app": d.source_app,
                "chat": d.chat_jid,
                "gap_start": d.gap_start,
                "gap_end": d.gap_end,
                "missing_count": d.missing_count,
                "confidence": d.confidence_score,
                "method": d.detection_method,
                "detected_at": d.detected_at,
            }
            for d in deletions[:100]  # Limit for PDF
        ]

        return {
            "case_id": case_id,
            "total_deletions": total,
            "whatsapp_deletions": wa_count,
            "telegram_deletions": tg_count,
            "high_confidence_count": high_conf,
            "medium_confidence_count": medium_conf,
            "low_confidence_count": low_conf,
            "date_range": {
                "start": date_from,
                "end": date_to,
            } if date_from or date_to else None,
            "deletions": deletion_list,
        }

    def get_deleted_summary(self, case_id: int) -> Dict[str, Any]:
        """Get deleted message summary for a report."""
        data = self.get_deleted_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "total_deletions": data.get("total_deletions", 0),
            "whatsapp_deletions": data.get("whatsapp_deletions", 0),
            "telegram_deletions": data.get("telegram_deletions", 0),
            "high_confidence_count": data.get("high_confidence_count", 0),
            "medium_confidence_count": data.get("medium_confidence_count", 0),
            "low_confidence_count": data.get("low_confidence_count", 0),
            "date_range": data.get("date_range"),
        }

    def get_case_statistics(self, case_id: int) -> Dict[str, Any]:
        """Get case statistics for report."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        wa_stats = self._get_app_stats(evidence_ids, "whatsapp")
        tg_stats = self._get_app_stats(evidence_ids, "telegram")

        media_count = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).count()

        return {
            "total_messages": wa_stats["messages"] + tg_stats["messages"],
            "total_contacts": wa_stats["contacts"] + tg_stats["contacts"],
            "total_groups": wa_stats["groups"] + tg_stats["groups"],
            "total_media": media_count,
            "whatsapp": wa_stats,
            "telegram": tg_stats,
        }

    def get_correlation_data(self, case_id: int) -> Dict[str, Any]:
        """Get correlation data for report."""
        edges = self.db.query(CorrelationEdge).filter(
            CorrelationEdge.case_id == case_id
        ).all()

        total = len(edges)
        msg_contact = sum(1 for e in edges if "message" in str(e.source_type) and "contact" in str(e.target_type))
        msg_media = sum(1 for e in edges if "message" in str(e.source_type) and "media" in str(e.target_type))
        cross_app = sum(1 for e in edges if (
            ("wa" in str(e.source_type) and "tg" in str(e.target_type)) or
            ("tg" in str(e.source_type) and "wa" in str(e.target_type))
        ))

        return {
            "total_edges": total,
            "message_contact_links": msg_contact,
            "message_media_links": msg_media,
            "cross_app_links": cross_app,
        }

    def _get_apps_for_case(self, case_id: int) -> List[str]:
        """Get list of apps with data in the case."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        apps = []
        if evidence_ids:
            if self.db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).count() > 0:
                apps.append("whatsapp")

            if self.db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).count() > 0:
                apps.append("telegram")

        return apps

    def _get_date_range(self, case_id: int) -> tuple:
        """Get overall date range for case data."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        earliest = None
        latest = None

        if evidence_ids:
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

    def _get_app_stats(self, evidence_ids: List[int], app: str) -> Dict[str, int]:
        """Get statistics for a specific app."""
        if not evidence_ids:
            return {"messages": 0, "contacts": 0, "groups": 0}

        if app == "whatsapp":
            return {
                "messages": self.db.query(WhatsAppMessage).filter(
                    WhatsAppMessage.evidence_id.in_(evidence_ids)
                ).count(),
                "contacts": self.db.query(WhatsAppContact).filter(
                    WhatsAppContact.evidence_id.in_(evidence_ids)
                ).count(),
                "groups": self.db.query(WhatsAppGroup).filter(
                    WhatsAppGroup.evidence_id.in_(evidence_ids)
                ).count(),
            }
        else:
            return {
                "messages": self.db.query(TelegramMessage).filter(
                    TelegramMessage.evidence_id.in_(evidence_ids)
                ).count(),
                "contacts": self.db.query(TelegramContact).filter(
                    TelegramContact.evidence_id.in_(evidence_ids)
                ).count(),
                "groups": self.db.query(TelegramGroup).filter(
                    TelegramGroup.evidence_id.in_(evidence_ids)
                ).count(),
            }