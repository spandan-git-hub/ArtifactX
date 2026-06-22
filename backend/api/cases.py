"""Case management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case
from backend.schemas.case import CaseCreate, CaseRead, CaseUpdate
from backend.services.log_service import get_log_service

router = APIRouter()


@router.post("", response_model=CaseRead)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    try:
        case = Case(**data.model_dump())
        db.add(case)
        db.commit()
        db.refresh(case)

        # Log activity
        log_service = get_log_service(db)
        log_service.log_activity(
            case_id=case.id,
            action="create_case",
            description=f"Case created: {case.name}"
        )

        return case
    except Exception as e:
        # Log error
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="case_creation_error",
            message=f"Error creating case: {str(e)}",
            case_id=None,  # Case not yet created
            evidence_id=None,
            stack_trace=str(e.__traceback__),
            endpoint="/api/cases",
            method="POST"
        )
        raise


@router.get("", response_model=list[CaseRead])
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).all()


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: int, db: Session = Depends(get_db)):
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except Exception as e:
        # Log error
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="case_retrieval_error",
            message=f"Error retrieving case: {str(e)}",
            case_id=case_id,
            evidence_id=None,
            stack_trace=str(e.__traceback__),
            endpoint=f"/api/cases/{case_id}",
            method="GET"
        )
        raise


@router.put("/{case_id}", response_model=CaseRead)
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(case, field, value)
        db.commit()
        db.refresh(case)

        # Log activity
        log_service = get_log_service(db)
        log_service.log_activity(
            case_id=case.id,
            action="update_case",
            description=f"Case updated: {case.name}"
        )

        return case
    except Exception as e:
        # Log error
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="case_update_error",
            message=f"Error updating case: {str(e)}",
            case_id=case_id,
            evidence_id=None,
            stack_trace=str(e.__traceback__),
            endpoint=f"/api/cases/{case_id}",
            method="PUT"
        )
        raise


@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Log activity before deletion
        log_service = get_log_service(db)
        log_service.log_activity(
            case_id=case.id,
            action="delete_case",
            description=f"Case deleted: {case.name}"
        )

        db.delete(case)
        db.commit()
        return {"message": "Case deleted"}
    except Exception as e:
        # Log error
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="case_deletion_error",
            message=f"Error deleting case: {str(e)}",
            case_id=case_id,
            evidence_id=None,
            stack_trace=str(e.__traceback__),
            endpoint=f"/api/cases/{case_id}",
            method="DELETE"
        )
        raise
