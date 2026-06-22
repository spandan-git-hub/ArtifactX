"""Report API endpoints."""

import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.report_service import ReportService
from backend.schemas.report import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    EvidenceSummary,
    TimelineSummary,
    DeletedMessageSummary,
)

router = APIRouter()


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """Dependency to get report service."""
    return ReportService(db)


class InlineGenerateRequest(BaseModel):
    """Inline request for generate endpoint."""
    report_type: str = "full"
    include_evidence: bool = True
    include_timeline: bool = True
    include_deleted: bool = True
    include_correlations: bool = True


@router.post("/cases/{case_id}/reports")
async def generate_report(
    case_id: int,
    request: InlineGenerateRequest = InlineGenerateRequest(),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> ReportGenerateResponse:
    """
    Generate a PDF report for a case.

    Report types:
    - full: Complete report with all sections
    - evidence: Evidence summary only
    - timeline: Timeline analysis only
    - deleted: Deleted message analysis only
    - summary: Executive summary only

    Returns:
        Report ID and status
    """
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    result = service.generate_report(
        case_id=case_id,
        report_type=request.report_type,
        include_evidence=request.include_evidence,
        include_timeline=request.include_timeline,
        include_deleted=request.include_deleted,
        include_correlations=request.include_correlations,
    )

    if result.get("error"):
        return ReportGenerateResponse(
            report_id=result.get("report_id", ""),
            case_id=case_id,
            report_type=request.report_type,
            status="failed",
            message=result["error"],
            created_at=datetime.utcnow(),
        )

    return ReportGenerateResponse(
        report_id=result["report_id"],
        case_id=case_id,
        report_type=request.report_type,
        status="completed",
        message=f"Report generated: {result['filename']}",
        created_at=datetime.utcnow(),
    )


@router.get("/cases/{case_id}/reports/summary")
async def get_evidence_summary(
    case_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> EvidenceSummary:
    """
    Get evidence summary without generating a PDF.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    data = service.get_evidence_summary(case_id)
    return EvidenceSummary(**data)


@router.get("/cases/{case_id}/reports/timeline")
async def get_timeline_summary(
    case_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> TimelineSummary:
    """
    Get timeline summary without generating a PDF.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    data = service.get_timeline_summary(case_id)
    return TimelineSummary(**data)


@router.get("/cases/{case_id}/reports/deleted")
async def get_deleted_summary(
    case_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> DeletedMessageSummary:
    """
    Get deleted messages summary without generating a PDF.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    data = service.get_deleted_summary(case_id)
    return DeletedMessageSummary(**data)


@router.get("/reports/download/{case_id}/{filename}")
async def download_report(
    case_id: int,
    filename: str,
) -> FileResponse:
    """
    Download a generated report PDF.

    Parameters:
    - case_id: The case ID
    - filename: The report filename
    """
    filepath = os.path.join(os.getcwd(), "reports", str(case_id), filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/pdf",
    )