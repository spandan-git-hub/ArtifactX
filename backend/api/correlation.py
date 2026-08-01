"""Correlation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.services.correlation_service import correlation_service

router = APIRouter()


@router.post("/cases/{case_id}/correlate", status_code=status.HTTP_202_ACCEPTED)
async def correlate_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Trigger correlation for a case."""
    # Check if case exists
    from backend.models.models import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Run correlation
    edge_count = correlation_service.correlate_case(db, case_id)
    return {
        "message": "Correlation started",
        "case_id": case_id,
        "edges_created": edge_count
    }


@router.get("/cases/{case_id}/correlation", response_model=List[dict])
def get_case_correlation(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get correlation edges for a case."""
    # Check if case exists
    from backend.models.models import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    edges = correlation_service.get_edges_for_case(db, case_id)
    return edges


@router.get("/cases/{case_id}/correlation/entities", response_model=List[dict])
def get_entity_resolutions(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get resolved cross-app entity contact mappings for a case."""
    from backend.models.models import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_entity_resolutions(db, case_id)


@router.get("/cases/{case_id}/correlation/matrix", response_model=List[dict])
def get_message_matrix(
    case_id: int,
    window_seconds: int = 300,
    db: Session = Depends(get_db)
):
    """Get cross-app message correlation matrix for a case within a time window threshold."""
    from backend.models.models import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_cross_app_message_matrix(db, case_id, window_seconds)


@router.get("/cases/{case_id}/correlation/status", response_model=dict)
def get_correlation_status(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get accurate platform evidence presence status (has_whatsapp, has_telegram, evidence_count) for a case."""
    from backend.models.models import Case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.check_case_evidence_platforms(db, case_id)