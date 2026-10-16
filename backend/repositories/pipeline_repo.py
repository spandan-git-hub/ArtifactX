"""
Pipeline repository for persisting pipeline execution runs and stage details (spec B13.2).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload, load_only

from backend.models.models import PipelineRun, PipelineStageRun


class PipelineRepository:
    """Data access layer for pipeline runs and per-stage records."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_run_for_case(self, case_id: int) -> Optional[PipelineRun]:
        """Check if an active (IN_PROGRESS) run is currently executing for this case."""
        return (
            self.db.query(PipelineRun)
            .filter(
                PipelineRun.case_id == case_id,
                PipelineRun.status == "IN_PROGRESS",
            )
            .first()
        )

    def create_run(
        self,
        run_id: str,
        case_id: int,
        config_json: Optional[Dict[str, Any]] = None,
    ) -> PipelineRun:
        """Create a new pipeline run record in IN_PROGRESS state."""
        run = PipelineRun(
            id=run_id,
            case_id=case_id,
            status="IN_PROGRESS",
            config_json=config_json or {},
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def record_stage_run(
        self,
        run_id: str,
        stage: str,
        status: str,
        evidence_id: Optional[str] = None,
        error_code: Optional[str] = None,
        skip_reason: Optional[str] = None,
        counts_json: Optional[Dict[str, Any]] = None,
        output_hash: Optional[str] = None,
        duration_ms: Optional[float] = None,
        errors_json: Optional[List[str]] = None,
    ) -> PipelineStageRun:
        """Record an individual stage execution result."""
        stage_run = PipelineStageRun(
            run_id=run_id,
            stage=stage,
            evidence_id=str(evidence_id) if evidence_id is not None else None,
            status=status,
            error_code=error_code,
            skip_reason=skip_reason,
            counts_json=counts_json or {},
            output_hash=output_hash,
            duration_ms=duration_ms,
            errors_json=errors_json or [],
        )
        self.db.add(stage_run)
        self.db.commit()
        self.db.refresh(stage_run)
        return stage_run

    def complete_run(
        self,
        run_id: str,
        status: str,
        content_hash: Optional[str] = None,
        summary_json: Optional[Dict[str, Any]] = None,
    ) -> Optional[PipelineRun]:
        """Mark a pipeline run as finished (COMPLETED, PARTIAL, or FAILED)."""
        run = self.db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return None
        run.status = status
        run.content_hash = content_hash
        run.summary_json = summary_json or {}
        run.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(run)
        return run

    def list_runs_by_case(
        self,
        case_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PipelineRun]:
        """List pipeline runs for a case without loading any heavy BYTEA columns (R19)."""
        return (
            self.db.query(PipelineRun)
            .filter(PipelineRun.case_id == case_id)
            .order_by(PipelineRun.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_run_with_stages(self, run_id: str) -> Optional[PipelineRun]:
        """Fetch pipeline run with all associated stage records."""
        return (
            self.db.query(PipelineRun)
            .options(joinedload(PipelineRun.stage_runs))
            .filter(PipelineRun.id == run_id)
            .first()
        )
