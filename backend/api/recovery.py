"""
Physical Deleted Message Recovery API.

Thin API controller delegating physical carving and inspection to recovery_service per B8.5.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.schemas.recovery import (
    RecoveredFindingResponse,
    RecoveryRunRequest,
    RecoveryRunResponse,
)
from backend.services import recovery_service

router = APIRouter(prefix="/cases/{case_id}/recovery", tags=["recovery"])


@router.post("/run", response_model=RecoveryRunResponse, status_code=status.HTTP_200_OK)
def trigger_recovery_run(
    case_id: int,
    req: Optional[RecoveryRunRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Execute physical SQLite carving across case evidence (WAL, Freelist, and B-tree Slack).
    Zero disk access: reads evidence buffers from memory/BYTEA and stores findings.
    """
    return recovery_service.run_physical_recovery(case_id=case_id, db=db, req=req)


@router.get("/runs", response_model=List[RecoveryRunResponse])
def list_recovery_runs(case_id: int, db: Session = Depends(get_db)):
    """List all physical recovery execution records for a case."""
    return recovery_service.list_recovery_runs(case_id=case_id, db=db)


@router.get("/findings", response_model=List[RecoveredFindingResponse])
def list_recovered_findings(
    case_id: int,
    run_id: Optional[int] = None,
    evidence_id: Optional[int] = None,
    source_app: Optional[str] = None,
    method: Optional[str] = None,
    validation_status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve physically carved deleted messages and candidate records with provenance."""
    return recovery_service.list_recovered_findings(
        case_id=case_id,
        db=db,
        run_id=run_id,
        evidence_id=evidence_id,
        source_app=source_app,
        method=method,
        validation_status=validation_status,
        limit=limit,
        offset=offset,
    )


@router.get("/findings/{finding_id}", response_model=RecoveredFindingResponse)
def get_recovered_finding(
    case_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
):
    """Get single carved finding detail with raw hex dump and cryptographic provenance."""
    return recovery_service.get_recovered_finding(case_id=case_id, finding_id=finding_id, db=db)
