"""Repository for Timeline Event data."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.models import TimelineEvent


class TimelineRepository:
    """Repository for Timeline Event data operations."""

    def save_events(self, db: Session, events: List[dict]):
        """Save timeline events to database."""
        for event_data in events:
            # Check if event already exists (by evidence_id and some unique identifier?)
            # For simplicity, we will delete all events for a case before rebuild.
            # So we assume caller handles deduplication.
            event = TimelineEvent(**event_data)
            db.add(event)

        db.commit()

    def get_events_by_case_id(self, db: Session, case_id: int) -> List[TimelineEvent]:
        """Get timeline events by case ID."""
        return db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).order_by(TimelineEvent.normalized_timestamp).all()

    def delete_events_by_case_id(self, db: Session, case_id: int):
        """Delete all timeline events for a case."""
        db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()
        db.commit()

    def filter_events(
        self,
        db: Session,
        case_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        source_app: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[TimelineEvent]:
        """Filter timeline events for a case."""
        query = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id)

        if start_date:
            query = query.filter(TimelineEvent.normalized_timestamp >= start_date)
        if end_date:
            query = query.filter(TimelineEvent.normalized_timestamp <= end_date)
        if event_type:
            query = query.filter(TimelineEvent.event_type == event_type)
        if source_app:
            query = query.filter(TimelineEvent.source_app == source_app)
        if entity_type:
            query = query.filter(TimelineEvent.entity_type == entity_type)
        if search:
            search_term = f"%{search}%"
            query = query.filter(TimelineEvent.description.ilike(search_term))

        return query.order_by(TimelineEvent.normalized_timestamp).all()