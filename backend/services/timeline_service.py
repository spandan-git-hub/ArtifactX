"""Timeline reconstruction service."""

import traceback
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.repositories.timeline_repo import TimelineRepository
from forensic.timeline.builder import TimelineBuilder
from backend.services.log_service import get_log_service


class TimelineService:
    """Service for timeline reconstruction operations."""

    def __init__(self):
        self.timeline_repo = TimelineRepository()
        self.timeline_builder = TimelineBuilder()

    def build_timeline_for_case(self, db: Session, case_id: int) -> int:
        """
        Build timeline for a case by collecting messages from WhatsApp and Telegram.
        Deletes existing timeline events for the case before rebuilding.

        Returns:
            Number of timeline events created.
        """
        # Get log service
        log_service = get_log_service(db)

        # Log analysis start
        log_service.log_analysis(
            evidence_id=None,  # Not tied to specific evidence; case-level analysis
            log_type="timeline_building_start",
            message="Starting timeline building for case",
            details={"case_id": case_id}
        )

        try:
            # Delete existing timeline events for this case
            self.timeline_repo.delete_events_by_case_id(db, case_id)

            # Build timeline events using the forensic builder
            timeline_events = self.timeline_builder.build_timeline_for_case(db, case_id)

            # Save timeline events
            if timeline_events:
                self.timeline_repo.save_events(db, timeline_events)

            # Log analysis success
            log_service.log_analysis(
                evidence_id=None,
                log_type="timeline_building_completed",
                message="Timeline building completed successfully",
                details={"case_id": case_id, "events_created": len(timeline_events)}
            )

            return len(timeline_events)
        except Exception as e:
            # Log error
            log_service.log_error(
                error_type="timeline_building_error",
                message=f"Error during timeline building: {str(e)}",
                case_id=case_id,
                evidence_id=None,
                stack_trace=traceback.format_exc(),
                endpoint="/api/cases/{case_id}/timeline/build",
                method="POST"
            )
            return 0

    def get_timeline_for_case(self, db: Session, case_id: int) -> List[dict]:
        """Get timeline events for a case, auto-building if no events exist yet."""
        events = self.timeline_repo.get_events_by_case_id(db, case_id)
        if not events:
            self.build_timeline_for_case(db, case_id)
            events = self.timeline_repo.get_events_by_case_id(db, case_id)

        return [
            {
                "id": e.id,
                "case_id": e.case_id,
                "evidence_id": e.evidence_id,
                "event_type": e.event_type,
                "source_app": e.source_app,
                "timestamp": e.timestamp,
                "normalized_timestamp": e.normalized_timestamp.isoformat() if e.normalized_timestamp else None,
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "description": e.description,
                "metadata": e.metadata_,
            }
            for e in events
        ]

    def filter_timeline(
        self,
        db: Session,
        case_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        source_app: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Filter timeline events for a case."""
        events = self.timeline_repo.filter_events(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            entity_type=entity_type,
            search=search,
        )
        if not events and not start_date and not end_date and not search:
            # If timeline is unbuilt, attempt build & filter again
            self.build_timeline_for_case(db, case_id)
            events = self.timeline_repo.filter_events(
                db,
                case_id=case_id,
                start_date=start_date,
                end_date=end_date,
                event_type=event_type,
                source_app=source_app,
                entity_type=entity_type,
                search=search,
            )

        return [
            {
                "id": e.id,
                "case_id": e.case_id,
                "evidence_id": e.evidence_id,
                "event_type": e.event_type,
                "source_app": e.source_app,
                "timestamp": e.timestamp,
                "normalized_timestamp": e.normalized_timestamp.isoformat() if e.normalized_timestamp else None,
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "description": e.description,
                "metadata": e.metadata_,
            }
            for e in events
        ]

    def get_histogram(
        self,
        db: Session,
        case_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        source_app: Optional[str] = None,
        search: Optional[str] = None,
        interval: str = "day"
    ) -> dict:
        """Get histogram data for a case."""
        # Ensure events exist
        events = self.timeline_repo.get_events_by_case_id(db, case_id)
        if not events:
            self.build_timeline_for_case(db, case_id)

        return self.timeline_repo.get_histogram_data(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            search=search,
            interval=interval,
        )


timeline_service = TimelineService()