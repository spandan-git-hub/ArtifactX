"""
Forensic Pipeline Orchestration API Controller (spec 11_PIPELINE_AND_E2E.md §B13.2).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.repositories.pipeline_repo import PipelineRepository
from backend.schemas.pipeline import (
    PipelineRunDetailResponse,
    PipelineRunRequest,
    PipelineRunSummaryResponse,
)
from backend.services.pipeline_service import ConcurrentPipelineRunError, PipelineService

case_pipeline_router = APIRouter(prefix="/cases/{case_id}/pipeline", tags=["pipeline"])
global_pipeline_router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@case_pipeline_router.post(
    "/run",
    response_model=PipelineRunDetailResponse,
    status_code=status.HTTP_200_OK,
)
def run_case_pipeline(
    case_id: int,
    req: Optional[PipelineRunRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Execute end-to-end analysis pipeline for a forensic case.

    Stages: integrity → detect → decrypt → parse → recover → timeline → correlate → summary.
    Enforces master.md R5: request bodies with keys are excluded from middleware capture.
    Returns 409 Conflict if another run is already IN_PROGRESS for this case.
    """
    svc = PipelineService(db)
    try:
        run = svc.execute_pipeline(case_id=case_id, req=req)
        return run
    except ConcurrentPipelineRunError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@case_pipeline_router.get(
    "/runs",
    response_model=List[PipelineRunSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_case_pipeline_runs(
    case_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List all pipeline runs for a case without loading heavy BYTEA columns (R19).
    """
    repo = PipelineRepository(db)
    return repo.list_runs_by_case(case_id=case_id, skip=skip, limit=limit)


@global_pipeline_router.get(
    "/runs/{run_id}",
    response_model=PipelineRunDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_pipeline_run_details(
    run_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed pipeline run information including all per-stage execution results and hashes.
    """
    repo = PipelineRepository(db)
    run = repo.get_run_with_stages(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{run_id}' not found",
        )
    return run
