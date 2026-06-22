"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.dashboard_service import DashboardService
from backend.schemas.dashboard import CaseStats, CorrelationStats, TimelineStats, CaseOverview

router = APIRouter()


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Dependency to get dashboard service."""
    return DashboardService(db)


def get_case_or_404(db: Session, case_id: int) -> Case:
    """Get case by ID or raise 404."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/cases/{case_id}/stats", response_model=CaseStats)
async def get_case_stats(
    case_id: int,
    db: Session = Depends(get_db),
) -> CaseStats:
    """
    Get comprehensive statistics for a case.

    Returns:
    - Total messages across all apps
    - Total contacts
    - Total media files
    - Total deleted messages
    - Total groups
    - Per-app stats (WhatsApp, Telegram)
    """
    get_case_or_404(db, case_id)
    service = get_dashboard_service(db)
    return service.get_case_stats(case_id)


@router.get("/cases/{case_id}/correlation-stats", response_model=CorrelationStats)
async def get_correlation_stats(
    case_id: int,
    db: Session = Depends(get_db),
) -> CorrelationStats:
    """
    Get correlation statistics for a case.

    Returns:
    - Total correlation edges
    - Message-contact links
    - Message-media links
    - Cross-app links
    """
    get_case_or_404(db, case_id)
    service = get_dashboard_service(db)
    return service.get_correlation_stats(case_id)


@router.get("/cases/{case_id}/timeline-stats", response_model=TimelineStats)
async def get_timeline_stats(
    case_id: int,
    db: Session = Depends(get_db),
) -> TimelineStats:
    """
    Get timeline event statistics for a case.

    Returns:
    - Total events
    - Events by type
    - Events by app
    - Date range
    """
    get_case_or_404(db, case_id)
    service = get_dashboard_service(db)
    return service.get_timeline_stats(case_id)


@router.get("/cases/{case_id}/overview", response_model=CaseOverview)
async def get_case_overview(
    case_id: int,
    db: Session = Depends(get_db),
) -> CaseOverview:
    """
    Get comprehensive case overview for dashboard.

    Returns all dashboard data including:
    - Case information
    - Statistics (messages, contacts, media, etc.)
    - Correlation statistics
    - Timeline statistics
    - Recent events
    - Available apps and date range
    """
    case = get_case_or_404(db, case_id)
    service = get_dashboard_service(db)
    return service.get_case_overview(
        case_id=case_id,
        case_name=case.name,
        case_status=case.status,
    )