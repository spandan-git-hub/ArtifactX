"""Case management API endpoints."""

import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.config import UPLOADS_DIR
from backend.app.database import get_db
from backend.models.models import Case, CorrelationEdge, AnalysisLog, ErrorLog
from backend.schemas.case import CaseCreate, CaseRead, CaseUpdate
from backend.services.log_service import get_log_service
from backend.utils.file_storage import delete_file

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
            stack_trace=traceback.format_exc(),
            endpoint="/api/cases",
            method="POST"
        )
        raise


@router.get("", response_model=list[CaseRead])
def get_cases(db: Session = Depends(get_db)):
    return db.query(Case).all()


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/{case_id}", response_model=CaseRead)
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(case, key, value)

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
            stack_trace=traceback.format_exc(),
            endpoint=f"/api/cases/{case_id}",
            method="PUT"
        )
        raise


@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    try:
        case_row = db.query(Case.name).filter(Case.id == case_id).first()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")

        case_name = case_row[0]

        # Fetch evidence details as tuple rows (no ORM objects in session)
        evidence_rows = db.query(
            Evidence.id,
            Evidence.storage_path,
            Evidence.extracted_path
        ).filter(Evidence.case_id == case_id).all()

        evidence_ids = [r[0] for r in evidence_rows]

        # Delete evidence storage & extracted files from disk
        for ev_id, storage_path, extracted_path in evidence_rows:
            if storage_path:
                try:
                    p = Path(storage_path)
                    if not p.is_absolute():
                        p = UPLOADS_DIR / storage_path
                    delete_file(p)
                except Exception:
                    pass
            if extracted_path:
                try:
                    p = Path(extracted_path)
                    if not p.is_absolute():
                        p = UPLOADS_DIR / extracted_path
                    delete_file(p)
                except Exception:
                    pass

        # Delete generated report directory for this case
        reports_dir = Path("reports") / str(case_id)
        if reports_dir.exists():
            try:
                delete_file(reports_dir)
            except Exception:
                pass

        # Import models for bulk delete
        from backend.models.models import (
            Evidence, EvidenceFile, AnalysisResult,
            WhatsAppMessage, WhatsAppContact, WhatsAppGroup,
            TelegramMessage, TelegramContact, TelegramGroup,
            TimelineEvent, DeletedMessage, MediaItem,
            CorrelationEdge, ActivityLog, ErrorLog, AnalysisLog
        )

        # Bulk delete evidence-dependent tables
        if evidence_ids:
            db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(WhatsAppGroup).filter(WhatsAppGroup.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(TelegramMessage).filter(TelegramMessage.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(TelegramContact).filter(TelegramContact.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(TelegramGroup).filter(TelegramGroup.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(AnalysisResult).filter(AnalysisResult.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(EvidenceFile).filter(EvidenceFile.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)
            db.query(AnalysisLog).filter(AnalysisLog.evidence_id.in_(evidence_ids)).delete(synchronize_session=False)

        # Bulk delete case-dependent tables
        db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete(synchronize_session=False)
        db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).delete(synchronize_session=False)
        db.query(MediaItem).filter(MediaItem.case_id == case_id).delete(synchronize_session=False)
        db.query(CorrelationEdge).filter(CorrelationEdge.case_id == case_id).delete(synchronize_session=False)
        db.query(ActivityLog).filter(ActivityLog.case_id == case_id).delete(synchronize_session=False)
        db.query(ErrorLog).filter(ErrorLog.case_id == case_id).delete(synchronize_session=False)
        db.query(Evidence).filter(Evidence.case_id == case_id).delete(synchronize_session=False)

        # Delete case object
        db.query(Case).filter(Case.id == case_id).delete(synchronize_session=False)
        db.commit()
        return {"message": f"Case '{case_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="case_deletion_error",
            message=f"Error deleting case: {str(e)}",
            case_id=case_id,
            evidence_id=None,
            stack_trace=traceback.format_exc(),
            endpoint=f"/api/cases/{case_id}",
            method="DELETE"
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")
