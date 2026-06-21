"""Timeline reconstruction service."""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.repositories.timeline_repo import TimelineRepository
from forensic.timeline.builder import TimelineBuilder


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
        # Delete existing timeline events for this case
        self.timeline_repo.delete_events_by_case_id(db, case_id)

        # Build timeline events using the forensic builder
        timeline_events = self.timeline_builder.build_timeline_for_case(db, case_id)

        # Save timeline events
        if timeline_events:
            self.timeline_repo.save_events(db, timeline_events)

        return len(timeline_events)

    def get_timeline_for_case(self, db: Session, case_id: int) -> List[dict]:
        """Get timeline events for a case."""
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


timeline_service = TimelineService()