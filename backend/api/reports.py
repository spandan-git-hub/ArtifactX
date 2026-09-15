"""Report API endpoints."""

import os
import tempfile
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.report_service import ReportService
from backend.schemas.report import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    GeneratedReportResponse,
    ReportHistoryResponse,
    EvidenceSummary,
    TimelineSummary,
    DeletedMessageSummary,
)

router = APIRouter()


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """Dependency to get report service."""
    return ReportService(db)


@router.post("/cases/{case_id}/reports")
async def generate_court_report(
    case_id: int,
    request: ReportGenerateRequest = ReportGenerateRequest(),
    stream: bool = Query(True, description="Whether to stream PDF bytes directly or return metadata"),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    """
    Generate a court-ready PDF report for a case into memory.
    Streams PDF directly to browser (zero workspace disk storage).
    Tracks generated report metadata in database.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        result = service.generate_report_bytes(
            case_id=case_id,
            report_type=request.report_type.value if hasattr(request.report_type, "value") else str(request.report_type),
            include_evidence=request.include_evidence,
            include_timeline=request.include_timeline,
            include_deleted=request.include_deleted,
            include_correlations=request.include_correlations,
            include_custody_log=request.include_custody_log,
            lead_analyst=request.lead_analyst,
            agency=request.agency,
            case_notes=request.case_notes,
            sworn_declaration=request.sworn_declaration,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate court report: {str(e)}")

    if not stream:
        return ReportGenerateResponse(
            report_id=result["report_id"],
            case_id=case_id,
            report_type=request.report_type,
            status="completed",
            message=f"Report generated: {result['filename']}",
            filename=result["filename"],
            sha256=result["sha256"],
            total_pages=result["total_pages"],
            size_bytes=result["size_bytes"],
            created_at=result["generated_at"],
        )

    return StreamingResponse(
        BytesIO(result["pdf_bytes"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "X-Report-Id": result["report_id"],
            "X-Report-Hash": result["sha256"],
            "X-Total-Pages": str(result["total_pages"]),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Report-Id, X-Report-Hash, X-Total-Pages",
        },
    )


@router.get("/cases/{case_id}/reports/history")
async def get_report_history(
    case_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> ReportHistoryResponse:
    """
    Get in-app report history for a case, tracking generated report IDs,
    analysts, timestamps, total pages, file sizes, and SHA-256 signatures.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    reports = service.repo.get_report_history(case_id)
    return ReportHistoryResponse(
        case_id=case_id,
        total_reports=len(reports),
        reports=[GeneratedReportResponse.model_validate(r) for r in reports],
    )


@router.get("/cases/{case_id}/reports/{report_id}/download")
async def download_historical_report(
    case_id: int,
    report_id: str,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    """
    Download a past generated report by its report ID.
    Retrieves from temporary cache or reconstructs deterministically in memory.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cached = service.get_cached_or_regenerate_report(case_id, report_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Report record not found")

    return StreamingResponse(
        BytesIO(cached["pdf_bytes"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{cached["filename"]}"',
            "X-Report-Id": report_id,
            "X-Report-Hash": cached["sha256"],
            "Access-Control-Expose-Headers": "Content-Disposition, X-Report-Id, X-Report-Hash",
        },
    )


@router.get("/cases/{case_id}/reports/summary")
async def get_evidence_summary(
    case_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> EvidenceSummary:
    """Get evidence summary without generating a PDF."""
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
    """Get timeline summary without generating a PDF."""
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
    """Get deleted messages summary without generating a PDF."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    data = service.get_deleted_summary(case_id)
    return DeletedMessageSummary(**data)


@router.get("/reports/download/{case_id}/{filename}")
async def download_report_legacy(
    case_id: int,
    filename: str,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    """
    Legacy download endpoint supporting direct streaming from temp cache or regeneration.
    Zero files written to workspace.
    """
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(temp_path):
        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Re-generate in-memory
    result = service.generate_report_bytes(case_id=case_id)
    return StreamingResponse(
        BytesIO(result["pdf_bytes"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )