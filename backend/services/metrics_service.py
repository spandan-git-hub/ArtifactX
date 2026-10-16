"""Backend metrics service for production casework (spec C1.5, 12_METRICS_AND_EVALUATION.md).

Retrieves case state without loading BYTEA (Rule R19, spec C1.5) and delegates
to the pure forensic function `case_metrics`.
Explicitly disclaims accuracy measurements for ungrounded casework.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.models import (
    Case,
    CorrelationFinding,
    Evidence,
    PipelineRun,
    PipelineStageRun,
    RecoveredFinding,
    TelegramContact,
    TelegramMessage,
    TimelineEvent,
    WhatsAppContact,
    WhatsAppMessage,
)
from backend.services.audit_service import AuditService
from forensic.metrics.case_metrics import (
    CaseMetrics,
    CaseMetricsInput,
    EvidenceSummaryItem,
    StageTiming,
    case_metrics,
)


def get_case_metrics(db: Session, case_id: int) -> Optional[CaseMetrics]:
    """Calculate and return case metrics for an active case.

    Guarantees:
    - Never loads BYTEA columns (`content_bytes` deferred/omitted).
    - Never makes ungrounded accuracy claims.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return None

    # 1. Evidence items (deferred BYTEA - load metadata only)
    evidence_rows = (
        db.query(
            Evidence.id,
            Evidence.original_filename,
            Evidence.sha256,
            Evidence.integrity_state,
            Evidence.evidence_type,
            Evidence.detected_format,
            Evidence.evidence_role,
        )
        .filter(Evidence.case_id == case_id)
        .all()
    )

    evidence_items: List[EvidenceSummaryItem] = []
    for r in evidence_rows:
        evidence_items.append(
            EvidenceSummaryItem(
                evidence_id=str(r.id),
                name=r.original_filename,
                sha256=r.sha256,
                verification_status=r.integrity_state or "PENDING",
                role=r.evidence_role or "primary",
                format_type=r.detected_format or r.evidence_type or "unknown",
            )
        )

    # 2. Audit chain verification
    audit_res = AuditService.verify_audit_chain(db, case_id=case_id)
    audit_chain_status = {
        "is_valid": audit_res.ok,
        "block_count": audit_res.checked,
        "head_hash": audit_res.head_hash,
        "last_verified_at": None,
    }

    # 3. Pipeline runs & stage timings
    latest_run = (
        db.query(PipelineRun)
        .filter(PipelineRun.case_id == case_id)
        .order_by(PipelineRun.started_at.desc())
        .first()
    )

    stages: List[StageTiming] = []
    honest_failures: List[Dict[str, Any]] = []

    if latest_run:
        stage_records = (
            db.query(PipelineStageRun)
            .filter(PipelineStageRun.run_id == latest_run.id)
            .order_by(PipelineStageRun.id.asc())
            .all()
        )
        for st in stage_records:
            stages.append(
                StageTiming(
                    stage_name=st.stage,
                    status=st.status,
                    duration_ms=int(st.duration_ms) if st.duration_ms is not None else 0,
                    error=st.error_code or st.skip_reason,
                    counts=st.counts_json or {},
                )
            )
            if st.status == "FAILED" or st.error_code:
                honest_failures.append({
                    "stage": st.stage,
                    "evidence_id": st.evidence_id,
                    "error_code": st.error_code,
                    "reason": st.skip_reason,
                    "errors": st.errors_json or [],
                })

    # 4. Parsed records breakdown
    wa_msgs = db.query(func.count(WhatsAppMessage.id)).filter(WhatsAppMessage.case_id == case_id).scalar() or 0
    wa_contacts = db.query(func.count(WhatsAppContact.id)).filter(WhatsAppContact.case_id == case_id).scalar() or 0
    tg_msgs = db.query(func.count(TelegramMessage.id)).filter(TelegramMessage.case_id == case_id).scalar() or 0
    tg_contacts = db.query(func.count(TelegramContact.id)).filter(TelegramContact.case_id == case_id).scalar() or 0

    parsed_counts = {
        "whatsapp_messages": wa_msgs,
        "whatsapp_contacts": wa_contacts,
        "telegram_messages": tg_msgs,
        "telegram_contacts": tg_contacts,
    }

    # 5. Recovery findings per tier
    tier_rows = (
        db.query(RecoveredFinding.tier, func.count(RecoveredFinding.id))
        .filter(RecoveredFinding.case_id == case_id)
        .group_by(RecoveredFinding.tier)
        .all()
    )
    findings_by_tier = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0}
    for t_num, cnt in tier_rows:
        if t_num in (1, 2, 3, 4):
            findings_by_tier[f"tier_{t_num}"] = cnt

    # 6. Correlation findings per strength
    strength_rows = (
        db.query(CorrelationFinding.strength, func.count(CorrelationFinding.id))
        .filter(CorrelationFinding.case_id == case_id, CorrelationFinding.below_threshold == False)
        .group_by(CorrelationFinding.strength)
        .all()
    )
    findings_by_strength = {"definitive": 0, "strong": 0, "moderate": 0, "weak_hint": 0, "none": 0}
    for st_name, cnt in strength_rows:
        if st_name and st_name.lower() in findings_by_strength:
            findings_by_strength[st_name.lower()] = cnt

    below_thresh_count = (
        db.query(func.count(CorrelationFinding.id))
        .filter(CorrelationFinding.case_id == case_id, CorrelationFinding.below_threshold == True)
        .scalar()
        or 0
    )

    # 7. Timeline timestamp anomalies
    anomaly_count = (
        db.query(func.count(TimelineEvent.id))
        .filter(TimelineEvent.case_id == case_id, TimelineEvent.is_anomaly == True)
        .scalar()
        or 0
    )
    timestamp_quality_flags = {
        "anomalous_timestamps_detected": anomaly_count,
    }

    # 8. Limitations triggered
    limitations_triggered = [
        {
            "code": "LIM-HEURISTIC-ORDERING",
            "description": "Confidence scores represent heuristic ordering, not calibrated posterior probabilities.",
        },
        {
            "code": "LIM-NO-GROUND-TRUTH",
            "description": "Casework accuracy metrics are unmeasured without a ground-truth reference manifest.",
        },
    ]

    # Assemble CaseMetricsInput
    metrics_input = CaseMetricsInput(
        case_id=str(case.id),
        evidence_items=evidence_items,
        audit_chain_status=audit_chain_status,
        stages=stages,
        parsed_counts=parsed_counts,
        findings_by_tier=findings_by_tier,
        findings_by_strength=findings_by_strength,
        timestamp_quality_flags=timestamp_quality_flags,
        below_threshold_count=below_thresh_count,
        honest_failures=honest_failures,
        limitations_triggered=limitations_triggered,
    )

    return case_metrics(metrics_input)
