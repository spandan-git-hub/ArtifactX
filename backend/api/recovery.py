"""
Physical Deleted Message Recovery API.
Endpoints for executing SQLite physical carving (WAL, freelist, slack) and inspecting findings.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import (
    Case,
    Evidence,
    EvidenceFile,
    RecoveredFinding,
    RecoveryRun,
    ActivityLog,
)
from backend.schemas.recovery import (
    RecoveredFindingResponse,
    RecoveryRunRequest,
    RecoveryRunResponse,
)
from forensic.deleted.orchestrator import DeletedRecoveryEngine


router = APIRouter(prefix="/cases/{case_id}/recovery", tags=["recovery"])


def _clean_pg_text(val: Any) -> Any:
    if isinstance(val, str):
        return val.replace("\x00", "")
    elif isinstance(val, list):
        return [_clean_pg_text(x) for x in val]
    elif isinstance(val, dict):
        return {k: _clean_pg_text(v) for k, v in val.items()}
    return val


@router.post("/run", response_model=RecoveryRunResponse, status_code=status.HTTP_200_OK)
def trigger_recovery_run(
    case_id: int,
    req: Optional[RecoveryRunRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Execute physical SQLite carving across case evidence (WAL, Freelist, and B-tree Slack).
    Zero disk access: reads evidence buffers from PostgreSQL BYTEA and stores findings.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Create audit record for the run
    run = RecoveryRun(
        case_id=case_id,
        status="RUNNING",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Collect candidate database evidence items
        evidence_query = db.query(Evidence).filter(Evidence.case_id == case_id)
        if req and req.evidence_id:
            evidence_query = evidence_query.filter(Evidence.id == req.evidence_id)

        evidence_items = evidence_query.all()

        total_findings = 0
        total_wal_pages = 0
        total_freelist_pages = 0
        total_slack_spans = 0

        for ev in evidence_items:
            # 1. Check direct evidence content_bytes (e.g. uploaded .db or .sqlite)
            db_candidates = []
            if ev.content_bytes and len(ev.content_bytes) >= 100:
                if ev.content_bytes.startswith(b"SQLite format 3\x00"):
                    hint = (req.source_app_hint if req else None) or ("telegram" if "tg" in ev.original_filename.lower() else "whatsapp")
                    db_candidates.append({
                        "name": ev.original_filename,
                        "bytes": ev.content_bytes,
                        "sha256": ev.sha256,
                        "file_id": None,
                        "app_hint": hint,
                    })

            # 2. Check ZIP archive members in evidence_files
            extracted_files = (
                db.query(EvidenceFile)
                .filter(EvidenceFile.evidence_id == ev.id)
                .all()
            )

            # Map files by path to match potential -wal files
            files_by_path = {ef.relative_path: ef for ef in extracted_files}

            for ef in extracted_files:
                if not ef.content_bytes or len(ef.content_bytes) < 100:
                    continue
                if ef.content_bytes.startswith(b"SQLite format 3\x00"):
                    wal_bytes = None
                    wal_path = f"{ef.relative_path}-wal"
                    if wal_path in files_by_path and files_by_path[wal_path].content_bytes:
                        wal_bytes = files_by_path[wal_path].content_bytes

                    hint = (req.source_app_hint if req else None) or ("telegram" if "tg" in ef.relative_path.lower() else "whatsapp")
                    db_candidates.append({
                        "name": ef.relative_path,
                        "bytes": ef.content_bytes,
                        "wal_bytes": wal_bytes,
                        "sha256": ef.sha256,
                        "file_id": ef.id,
                        "app_hint": hint,
                    })

            # Run carving on each database candidate
            for cand in db_candidates:
                engine = DeletedRecoveryEngine(
                    db_bytes=cand["bytes"],
                    wal_bytes=cand.get("wal_bytes"),
                    source_app_hint=cand["app_hint"],
                    source_sha256=cand["sha256"],
                    evidence_id=ev.id,
                    case_id=case_id,
                )
                findings = engine.run()

                total_wal_pages += engine.wal_pages_analyzed
                total_freelist_pages += engine.freelist_pages_analyzed
                total_slack_spans += engine.slack_spans_analyzed

                for f in findings:
                    finding_row = RecoveredFinding(
                        case_id=case_id,
                        run_id=run.id,
                        evidence_id=ev.id,
                        source_file_id=cand["file_id"],
                        source_app=_clean_pg_text(f["source_app"]),
                        method=_clean_pg_text(f["method"]),
                        page_number=f["page_number"],
                        byte_offset=f["byte_offset"],
                        raw_payload_hash=_clean_pg_text(f["raw_payload_hash"]),
                        raw_payload_preview=_clean_pg_text(f["raw_payload_preview"]),
                        message_id=_clean_pg_text(f["message_id"]),
                        chat_id=_clean_pg_text(f["chat_id"]),
                        sender_id=_clean_pg_text(f["sender_id"]),
                        body=_clean_pg_text(f["body"]),
                        timestamp=f["timestamp"],
                        media_reference=_clean_pg_text(f["media_reference"]),
                        validation_status=_clean_pg_text(f["validation_status"]),
                        limitations=_clean_pg_text(f["limitations"]),
                        provenance=_clean_pg_text(f["provenance"]),
                        created_at=datetime.utcnow(),
                    )
                    db.add(finding_row)
                    total_findings += 1

        # Mark run completed
        run.status = "SUCCEEDED"
        run.completed_at = datetime.utcnow()
        run.findings_count = total_findings
        run.wal_pages_analyzed = total_wal_pages
        run.freelist_pages_analyzed = total_freelist_pages
        run.slack_spans_analyzed = total_slack_spans

        # Log forensic activity
        act = ActivityLog(
            case_id=case_id,
            action="PHYSICAL_RECOVERY_RUN",
            description=(
                f"Physical SQLite carving completed. Found {total_findings} recovered/candidate records "
                f"across {total_wal_pages} WAL pages, {total_freelist_pages} freelist pages, and {total_slack_spans} slack spans."
            ),
            timestamp=datetime.utcnow(),
        )
        db.add(act)
        db.commit()
        db.refresh(run)
        return run

    except Exception as exc:
        db.rollback()
        run.status = "FAILED"
        run.completed_at = datetime.utcnow()
        run.error_message = str(exc)
        db.commit()
        db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Physical recovery carving failed: {str(exc)}",
        )


@router.get("/runs", response_model=List[RecoveryRunResponse])
def list_recovery_runs(case_id: int, db: Session = Depends(get_db)):
    """List all physical recovery execution records for a case."""
    return (
        db.query(RecoveryRun)
        .filter(RecoveryRun.case_id == case_id)
        .order_by(RecoveryRun.started_at.desc())
        .all()
    )


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
    q = db.query(RecoveredFinding).filter(RecoveredFinding.case_id == case_id)

    if run_id is not None:
        q = q.filter(RecoveredFinding.run_id == run_id)
    if evidence_id is not None:
        q = q.filter(RecoveredFinding.evidence_id == evidence_id)
    if source_app:
        q = q.filter(RecoveredFinding.source_app == source_app)
    if method:
        q = q.filter(RecoveredFinding.method == method)
    if validation_status:
        q = q.filter(RecoveredFinding.validation_status == validation_status)

    return q.order_by(RecoveredFinding.id.desc()).offset(offset).limit(limit).all()


@router.get("/findings/{finding_id}", response_model=RecoveredFindingResponse)
def get_recovered_finding(
    case_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
):
    """Get single carved finding detail with raw hex dump and cryptographic provenance."""
    finding = (
        db.query(RecoveredFinding)
        .filter(
            RecoveredFinding.id == finding_id,
            RecoveredFinding.case_id == case_id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Recovered finding not found")
    return finding
