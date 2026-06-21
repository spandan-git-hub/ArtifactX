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