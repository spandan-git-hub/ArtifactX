"""Deleted message detection API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.deleted_service import deleted_service
from backend.schemas.deleted import DeletedMessageRead

router = APIRouter()


@router.post("/cases/{case_id}/deleted/detect", status_code=status.HTTP_202_ACCEPTED)
async def detect_deletions(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Detect deleted messages for a case from WhatsApp and Telegram messages."""
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    count = deleted_service.detect_deletions_for_case(db, case_id)
    return {"message": "Deleted message detection completed", "case_id": case_id, "deletions_detected": count}


@router.get("/cases/{case_id}/deleted", response_model=List[DeletedMessageRead])
def get_deleted_messages(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get deleted messages for a case."""
    # Check if case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    deletions = deleted_service.get_deleted_messages_for_case(db, case_id)
    return deletions