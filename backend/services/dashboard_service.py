"""Dashboard service for business logic."""

from typing import Dict, Any

from sqlalchemy.orm import Session

from backend.repositories.dashboard_repo import DashboardRepository
from backend.schemas.dashboard import (
    CaseStats,
    AppStats,
    CorrelationStats,
    TimelineStats,
    TimelineMiniEvent,
    CaseOverview,
)


class DashboardService:
    """Service for dashboard operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardRepository(db)

    def get_case_stats(self, case_id: int) -> CaseStats:
        """
        Get comprehensive statistics for a case.

        Args:
            case_id: The case ID

        Returns:
            CaseStats with message, contact, media, deleted, and group counts
        """
        stats = self.repo.get_case_stats(case_id)
        evidence_ids = self.repo._get_evidence_ids(case_id)
        wa_evidence_ids = self.repo._get_evidence_ids(case_id, "whatsapp")
        tg_evidence_ids = self.repo._get_evidence_ids(case_id, "telegram")

        # Get app-specific stats
        wa_data = self.repo._get_app_stats(wa_evidence_ids, "whatsapp") if wa_evidence_ids else {}
        tg_data = self.repo._get_app_stats(tg_evidence_ids, "telegram") if tg_evidence_ids else {}

        whatsapp_stats = AppStats(
            app="whatsapp",
            message_count=wa_data.get("message_count", 0),
            contact_count=wa_data.get("contact_count", 0),
            group_count=wa_data.get("group_count", 0),
            media_count=wa_data.get("media_count", 0),
            first_activity=wa_data.get("first_activity"),
            last_activity=wa_data.get("last_activity"),
        )

        telegram_stats = AppStats(
            app="telegram",
            message_count=tg_data.get("message_count", 0),
            contact_count=tg_data.get("contact_count", 0),
            group_count=tg_data.get("group_count", 0),
            media_count=tg_data.get("media_count", 0),
            first_activity=tg_data.get("first_activity"),
            last_activity=tg_data.get("last_activity"),
        )

        return CaseStats(
            total_messages=stats["total_messages"],
            total_contacts=stats["total_contacts"],
            total_media=stats["total_media"],
            total_deleted=stats["total_deleted"],
            total_groups=stats["total_groups"],
            whatsapp=whatsapp_stats,
            telegram=telegram_stats,
        )

    def get_correlation_stats(self, case_id: int) -> CorrelationStats:
        """
        Get correlation edge statistics.

        Args:
            case_id: The case ID

        Returns:
            CorrelationStats with edge counts
        """
        data = self.repo.get_correlation_stats(case_id)
        return CorrelationStats(**data)

    def get_timeline_stats(self, case_id: int) -> TimelineStats:
        """
        Get timeline event statistics.

        Args:
            case_id: The case ID

        Returns:
            TimelineStats with event counts
        """
        data = self.repo.get_timeline_stats(case_id)
        return TimelineStats(**data)

    def get_case_overview(self, case_id: int, case_name: str, case_status: str) -> CaseOverview:
        """
        Get comprehensive case overview for dashboard.

        Args:
            case_id: The case ID
            case_name: The case name
            case_status: The case status

        Returns:
            CaseOverview with all dashboard data
        """
        stats = self.get_case_stats(case_id)
        correlation_stats = self.get_correlation_stats(case_id)
        timeline_stats = self.get_timeline_stats(case_id)

        # Get recent events
        recent_events_data = self.repo.get_recent_events(case_id, limit=10)
        recent_events = [
            TimelineMiniEvent(
                id=e["id"],
                event_type=e["event_type"],
                source_app=e["source_app"],
                normalized_timestamp=e["normalized_timestamp"],
                description=e["description"],
                metadata=e["metadata"],
            )
            for e in recent_events_data
        ]

        # Get apps
        apps = self.repo.get_apps_for_case(case_id)

        # Get date range
        date_start, date_end = self.repo.get_date_range(case_id)

        return CaseOverview(
            case_id=case_id,
            case_name=case_name,
            case_status=case_status,
            stats=stats,
            correlation_stats=correlation_stats,
            timeline_stats=timeline_stats,
            recent_events=recent_events,
            apps=apps,
            date_range_start=date_start,
            date_range_end=date_end,
        )


def get_dashboard_service(db: Session) -> DashboardService:
    """Factory function to create DashboardService."""
    return DashboardService(db)