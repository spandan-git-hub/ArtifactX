"""Repository for Timeline Event data (Rule R10, R11, R19)."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.models import TimelineEvent


class TimelineRepository:
    """Repository for Timeline Event data operations."""

    def save_events(self, db: Session, events: List[dict]):
        """Save timeline events to database with fallback error protection."""
        if not events:
            return

        try:
            for event_data in events:
                event = TimelineEvent(**event_data)
                db.add(event)
            db.commit()
        except Exception:
            db.rollback()
            # Retry one-by-one with evidence_id=None fallback if FK fails
            for event_data in events:
                try:
                    event = TimelineEvent(**event_data)
                    db.add(event)
                    db.commit()
                except Exception:
                    db.rollback()
                    event_data_copy = dict(event_data)
                    event_data_copy["evidence_id"] = None
                    try:
                        event = TimelineEvent(**event_data_copy)
                        db.add(event)
                        db.commit()
                    except Exception:
                        db.rollback()

    def get_events_by_case_id(self, db: Session, case_id: int) -> List[TimelineEvent]:
        """Get timeline events by case ID ordered deterministically."""
        return db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).order_by(
            TimelineEvent.utc_ms.is_(None),
            TimelineEvent.utc_ms.asc(),
            TimelineEvent.id.asc()
        ).all()

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
        if event_type and event_type != "all":
            query = query.filter(TimelineEvent.event_type == event_type)
        if source_app and source_app != "all":
            query = query.filter(TimelineEvent.source_app == source_app)
        if entity_type and entity_type != "all":
            query = query.filter(TimelineEvent.entity_type == entity_type)
        if search:
            search_term = f"%{search}%"
            query = query.filter(TimelineEvent.description.ilike(search_term))

        return query.order_by(
            TimelineEvent.utc_ms.is_(None),
            TimelineEvent.utc_ms.asc(),
            TimelineEvent.id.asc()
        ).all()

    def get_histogram_data(
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
        """Calculate time-density histogram data for a case."""
        events = self.filter_events(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            search=search,
        )

        bins_map: Dict[str, Dict[str, Any]] = {}
        apps_breakdown = {"whatsapp": 0, "telegram": 0, "media": 0, "system": 0, "other": 0}
        types_breakdown = {
            "message": 0,
            "revocation": 0,
            "edit": 0,
            "recovered_record": 0,
            "media_exif": 0,
            "location": 0,
            "evidence_ingest": 0,
            "other": 0,
        }

        for ev in events:
            # Breakdown counts
            app_key = ev.source_app if ev.source_app in apps_breakdown else "other"
            apps_breakdown[app_key] = apps_breakdown.get(app_key, 0) + 1

            type_key = ev.event_type if ev.event_type in types_breakdown else "other"
            types_breakdown[type_key] = types_breakdown.get(type_key, 0) + 1

            # Binning key with timestamp fallback
            ts = ev.normalized_timestamp
            if not ts and ev.utc_ms is not None:
                try:
                    ts = datetime.fromtimestamp(ev.utc_ms / 1000.0, tz=timezone.utc)
                except Exception:
                    ts = None
            elif not ts and ev.timestamp:
                try:
                    ts_val = ev.timestamp / 1000.0 if ev.timestamp > 1e11 else float(ev.timestamp)
                    ts = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                except Exception:
                    ts = None

            if not ts:
                ts = datetime.now(timezone.utc)

            if interval == "hour":
                date_key = ts.strftime("%Y-%m-%d %H:00")
            elif interval == "month":
                date_key = ts.strftime("%Y-%m")
            else:  # default 'day'
                date_key = ts.strftime("%Y-%m-%d")

            if date_key not in bins_map:
                bins_map[date_key] = {
                    "date": date_key,
                    "total": 0,
                    "whatsapp": 0,
                    "telegram": 0,
                    "media": 0,
                    "system": 0,
                    "other": 0,
                }

            bins_map[date_key]["total"] += 1
            if ev.source_app in bins_map[date_key]:
                bins_map[date_key][ev.source_app] += 1
            else:
                bins_map[date_key]["other"] += 1

        sorted_bins = [bins_map[k] for k in sorted(bins_map.keys())]

        return {
            "case_id": case_id,
            "interval": interval,
            "total_events": len(events),
            "apps_breakdown": apps_breakdown,
            "types_breakdown": types_breakdown,
            "bins": sorted_bins,
        }