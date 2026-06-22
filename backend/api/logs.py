"""Log management API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.schemas.log import (
    ActivityLogEntry,
    AnalysisLogEntry,
    ErrorLogEntry,
    LogSummary,
)
from backend.services.log_service import get_log_service

router = APIRouter()


@router.get("/analysis", response_model=list[AnalysisLogEntry])
def get_analysis_logs(
    evidence_id: Optional[int] = Query(None, description="Filter by evidence ID"),
    log_type: Optional[str] = Query(None, description="Filter by log type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get analysis logs with optional filters."""
    service = get_log_service(db)
    return service.get_analysis_logs(
        evidence_id=evidence_id,
        log_type=log_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/errors", response_model=list[ErrorLogEntry])
def get_error_logs(
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    evidence_id: Optional[int] = Query(None, description="Filter by evidence ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get error logs with optional filters."""
    service = get_log_service(db)
    return service.get_error_logs(
        case_id=case_id,
        evidence_id=evidence_id,
        start_date=start_date,
        end_date=end_date,
        error_type=error_type,
        limit=limit,
        offset=offset,
    )


@router.get("/activity", response_model=list[ActivityLogEntry])
def get_activity_logs(
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get activity logs with optional filters."""
    service = get_log_service(db)
    return service.get_activity_logs(
        case_id=case_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/summary/{case_id}", response_model=LogSummary)
def get_log_summary(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Get a summary of all logs for a case."""
    service = get_log_service(db)
    return service.get_log_summary(case_id)