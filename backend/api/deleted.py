"""Deleted message detection API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.deleted_service import deleted_service
from backend.schemas.deleted import DeletedMessageRead
from backend.services.log_service import get_log_service

router = APIRouter()


@router.post("/cases/{case_id}/deleted/detect", status_code=status.HTTP_202_ACCEPTED)
async def detect_deletions(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Detect deleted messages for a case from WhatsApp and Telegram messages."""
    try:
        # Verify case exists
        case_obj = db.query(Case).filter(Case.id == case_id).first()
        if not case_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )

        # Log activity
        log_service = get_log_service(db)
        log_service.log_activity(
            case_id=case_id,
            action="deleted_detection_start",
            description=f"Deleted message detection started for case {case_id}"
        )

        count = deleted_service.detect_deletions_for_case(db, case_id)

        # Log activity completion
        log_service.log_activity(
            case_id=case_id,
            action="deleted_detection_complete",
            description=f"Deleted message detection completed for case {case_id} with {count} deletions detected"
        )

        return {"message": "Deleted message detection completed", "case_id": case_id, "deletions_detected": count}
    except Exception as e:
        # Log error
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="deleted_detection_error",
            message=f"Error during deleted message detection: {str(e)}",
            case_id=case_id,
            evidence_id=None,
            stack_trace=str(e.__traceback__),
            endpoint=f"/api/cases/{case_id}/deleted/detect",
            method="POST"
        )
        raise


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