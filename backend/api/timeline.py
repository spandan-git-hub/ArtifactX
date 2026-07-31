"""Timeline reconstruction API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.app.database import get_db
from backend.services.timeline_service import timeline_service
from backend.schemas.timeline import TimelineEventRead, TimelineEventFilter

router = APIRouter()


@router.post("/cases/{case_id}/timeline/build", status_code=status.HTTP_202_ACCEPTED)
async def build_timeline(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Build timeline for a case from WhatsApp, Telegram, deleted gaps, and evidence files."""
    count = timeline_service.build_timeline_for_case(db, case_id)
    return {"message": "Timeline built", "case_id": case_id, "events_created": count}


@router.get("/cases/{case_id}/timeline", response_model=List[TimelineEventRead])
def get_timeline(
    case_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    source_app: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get or filter timeline events for a case."""
    if start_date or end_date or event_type or source_app or entity_type or search:
        events = timeline_service.filter_timeline(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            entity_type=entity_type,
            search=search,
        )
    else:
        events = timeline_service.get_timeline_for_case(db, case_id)

    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    return events


@router.post("/cases/{case_id}/timeline/filter", response_model=List[TimelineEventRead])
def filter_timeline(
    case_id: int,
    filter_params: TimelineEventFilter,
    db: Session = Depends(get_db)
):
    """Filter timeline events for a case."""
    events = timeline_service.filter_timeline(
        db,
        case_id=case_id,
        start_date=filter_params.start_date,
        end_date=filter_params.end_date,
        event_type=filter_params.event_type,
        source_app=filter_params.source_app,
        entity_type=filter_params.entity_type,
        search=filter_params.search,
    )
    return events


@router.get("/cases/{case_id}/timeline/histogram")
@router.get("/timeline/cases/{case_id}/histogram")
def get_timeline_histogram(
    case_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    source_app: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    interval: str = Query("day"),
    db: Session = Depends(get_db)
):
    """Get time-density histogram for timeline visualization."""
    return timeline_service.get_histogram(
        db,
        case_id=case_id,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        source_app=source_app,
        search=search,
        interval=interval,
    )