"""
Physical deleted message and SQLite recovery service (spec B10, master.md R3, R4, R7, R8, R10, R11).

Orchestrates non-destructive physical recovery across evidence and archive members,
enforces cryptographic integrity (B5.3, R3), zero disk writes (R4), idempotent re-runs per evidence,
hash-chained audit logging (RECOVER_START/COMPLETE), and provenance logging (R8).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.models import (
    ActivityLog,
    Case,
    Evidence,
    EvidenceFile,
    RecoveredFinding,
    RecoveryRun,
)
from backend.schemas.recovery import RecoveryRunRequest
from backend.services.audit_service import AuditService
from backend.services.integrity_service import ensure_integrity
from forensic.recovery.orchestrator import RecoveryPipeline


def _clean_pg_text(val: Any) -> Any:
    """Sanitize strings containing null bytes for PostgreSQL/SQLite text columns."""
    if isinstance(val, str):
        return val.replace("\x00", "")
    elif isinstance(val, list):
        return [_clean_pg_text(x) for x in val]
    elif isinstance(val, dict):
        return {k: _clean_pg_text(v) for k, v in val.items()}
    return val


def clear_recovery_data(case_id: int, evidence_id: int, db: Session) -> int:
    """Remove existing recovered findings for an evidence item to guarantee idempotent re-run."""
    deleted_count = (
        db.query(RecoveredFinding)
        .filter(
            RecoveredFinding.case_id == case_id,
            RecoveredFinding.evidence_id == evidence_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted_count


def run_physical_recovery(
    case_id: int,
    db: Session,
    req: Optional[RecoveryRunRequest] = None,
) -> RecoveryRun:
    """
    Execute physical SQLite carving across case evidence (WAL, Freelist, and B-tree Slack).

    Zero disk access: reads evidence buffers from memory/BYTEA, verifies integrity,
    applies idempotent re-runs, and records hash-chained audit events.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Create run record
    now_utc = datetime.now(timezone.utc)
    run = RecoveryRun(
        case_id=case_id,
        status="RUNNING",
        started_at=now_utc,
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
            # 1. Enforce pre-analysis cryptographic integrity check (B5.3, R3)
            ensure_integrity(ev.id, db, action_context="physical_recovery")

            # 2. Append RECOVER_START audit log (no content) per B10
            AuditService.append(
                db=db,
                case_id=case_id,
                evidence_id=ev.id,
                action="RECOVER_START",
                details={
                    "evidence_id": ev.id,
                    "evidence_sha256": ev.sha256,
                    "action": "recovery_started",
                },
            )

            # 3. Idempotent re-run cleanup: clear existing findings for this evidence
            clear_recovery_data(case_id, ev.id, db)

            db_candidates = []

            # Check direct evidence content_bytes (e.g. uploaded .db or .sqlite)
            if ev.content_bytes and len(ev.content_bytes) >= 100:
                if ev.content_bytes.startswith(b"SQLite format 3\x00"):
                    hint = (req.source_app_hint if req else None) or (
                        "telegram" if "tg" in (ev.original_filename or "").lower() else "whatsapp"
                    )
                    db_candidates.append({
                        "name": ev.original_filename,
                        "bytes": ev.content_bytes,
                        "sha256": ev.sha256,
                        "file_id": None,
                        "app_hint": hint,
                    })

            # Check ZIP archive members in evidence_files
            extracted_files = (
                db.query(EvidenceFile)
                .filter(EvidenceFile.evidence_id == ev.id)
                .all()
            )

            files_by_path = {ef.relative_path: ef for ef in extracted_files}

            for ef in extracted_files:
                if not ef.content_bytes or len(ef.content_bytes) < 100:
                    continue
                if ef.content_bytes.startswith(b"SQLite format 3\x00"):
                    wal_bytes = None
                    wal_path = f"{ef.relative_path}-wal"
                    if wal_path in files_by_path and files_by_path[wal_path].content_bytes:
                        wal_bytes = files_by_path[wal_path].content_bytes

                    hint = (req.source_app_hint if req else None) or (
                        "telegram" if "tg" in (ef.relative_path or "").lower() else "whatsapp"
                    )
                    db_candidates.append({
                        "name": ef.relative_path,
                        "bytes": ef.content_bytes,
                        "wal_bytes": wal_bytes,
                        "sha256": ef.sha256,
                        "file_id": ef.id,
                        "app_hint": hint,
                    })

            # Run recovery pipeline on each database candidate
            ev_findings_count = 0
            ev_tier_counts: Dict[int, int] = {}
            ev_rejected_count = 0

            for cand in db_candidates:
                pipeline = RecoveryPipeline(
                    db_bytes=cand["bytes"],
                    wal_bytes=cand.get("wal_bytes"),
                    app_hint=cand["app_hint"],
                    evidence_id=str(ev.id),
                    evidence_sha256=cand["sha256"],
                )
                res = pipeline.run()

                total_wal_pages += res.wal_pages_analyzed
                total_freelist_pages += res.freelist_pages_analyzed
                total_slack_spans += res.slack_spans_analyzed
                ev_findings_count += res.total_findings_count
                ev_rejected_count += res.invalid_rejected_count
                for t, c in res.tier_counts.items():
                    ev_tier_counts[t] = ev_tier_counts.get(t, 0) + c

                for f in res.findings:
                    rf = f.recovered_fields
                    body_val = rf.get("body")
                    key_val = rf.get("key_id") or str(rf.get("mid") or "")
                    chat_val = str(rf.get("chat_id") or rf.get("uid") or "")
                    sender_val = str(rf.get("sender_id") or "")

                    finding_row = RecoveredFinding(
                        case_id=case_id,
                        run_id=run.id,
                        evidence_id=ev.id,
                        source_file_id=cand["file_id"],
                        source_app=_clean_pg_text(cand["app_hint"]),
                        method=_clean_pg_text(f.provenance.method),
                        page_number=f.page_no or 0,
                        byte_offset=f.byte_offset or 0,
                        raw_payload_hash=_clean_pg_text(f.raw_payload_hash),
                        raw_payload_preview=_clean_pg_text(f.raw_payload_preview),
                        message_id=_clean_pg_text(key_val),
                        chat_id=_clean_pg_text(chat_val),
                        sender_id=_clean_pg_text(sender_val),
                        body=_clean_pg_text(body_val),
                        timestamp=rf.get("timestamp"),
                        media_reference=_clean_pg_text(rf.get("media_reference")),
                        validation_status=_clean_pg_text(f.validation_status),
                        limitations=_clean_pg_text(list(f.limitations)),
                        provenance=_clean_pg_text(f.provenance.to_dict()),
                        # B10 additive fields
                        finding_id=_clean_pg_text(f.finding_id),
                        tier=f.tier,
                        kind=_clean_pg_text(f.kind),
                        strength=_clean_pg_text(f.strength),
                        confidence_score=f.confidence_score,
                        table_name=_clean_pg_text(f.table_name),
                        frame_index=f.frame_index,
                        recovered_fields=_clean_pg_text(f.recovered_fields),
                        view=_clean_pg_text(f.view),
                        evidence_sha256=_clean_pg_text(f.provenance.evidence_sha256),
                        candidate_original_text=_clean_pg_text(f.candidate_original_text),
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(finding_row)
                    total_findings += 1

            # 4. Append RECOVER_COMPLETE audit log (no content) per B10
            AuditService.append(
                db=db,
                case_id=case_id,
                evidence_id=ev.id,
                action="RECOVER_COMPLETE",
                details={
                    "evidence_id": ev.id,
                    "evidence_sha256": ev.sha256,
                    "total_findings": ev_findings_count,
                    "tier_counts": {str(t): c for t, c in ev_tier_counts.items()},
                    "invalid_rejected_count": ev_rejected_count,
                    "action": "recovery_completed",
                },
            )

        # Mark run completed
        end_utc = datetime.now(timezone.utc)
        run.status = "SUCCEEDED"
        run.completed_at = end_utc
        run.findings_count = total_findings
        run.wal_pages_analyzed = total_wal_pages
        run.freelist_pages_analyzed = total_freelist_pages
        run.slack_spans_analyzed = total_slack_spans

        # Log forensic activity
        act = ActivityLog(
            case_id=case_id,
            action="PHYSICAL_RECOVERY_RUN",
            description=(
                f"Physical SQLite recovery completed. Found {total_findings} findings "
                f"across {total_wal_pages} WAL pages, {total_freelist_pages} freelist pages, and {total_slack_spans} slack spans."
            ),
            timestamp=end_utc,
        )
        db.add(act)
        db.commit()
        db.refresh(run)
        return run

    except Exception as exc:
        db.rollback()
        run.status = "FAILED"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = str(exc)
        db.commit()
        db.refresh(run)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Physical recovery carving failed: {str(exc)}",
        )


def list_recovery_runs(case_id: int, db: Session) -> List[RecoveryRun]:
    """List all physical recovery execution records for a case."""
    return (
        db.query(RecoveryRun)
        .filter(RecoveryRun.case_id == case_id)
        .order_by(RecoveryRun.started_at.desc())
        .all()
    )


def list_recovered_findings(
    case_id: int,
    db: Session,
    run_id: Optional[int] = None,
    evidence_id: Optional[int] = None,
    source_app: Optional[str] = None,
    method: Optional[str] = None,
    validation_status: Optional[str] = None,
    tier: Optional[int] = None,
    strength: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[RecoveredFinding]:
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
    if tier is not None:
        q = q.filter(RecoveredFinding.tier == tier)
    if strength:
        q = q.filter(RecoveredFinding.strength == strength)
    if kind:
        q = q.filter(RecoveredFinding.kind == kind)

    return q.order_by(RecoveredFinding.id.desc()).offset(offset).limit(limit).all()


def get_recovered_finding(
    case_id: int,
    finding_id: int,
    db: Session,
) -> RecoveredFinding:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovered finding not found")
    return finding
