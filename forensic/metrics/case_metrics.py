"""Pure forensic-side per-case metrics module (spec C1.5, 12_METRICS_AND_EVALUATION.md).

Pure function `case_metrics(case_state: CaseMetricsInput) -> CaseMetrics`:
1. Evidence count and verification states (including LEGACY_UNVERIFIABLE).
2. Last integrity re-verification time and result.
3. Audit-chain verification status, block count, and head hash.
4. Per-stage pipeline status and timings.
5. Parsed vs unparsed counts and failure reasons.
6. Findings per evidential tier (1-4) and confidence strength level.
7. Timestamp quality flag counts (anomalies, skew, zero timestamps).
8. Below-reporting-threshold count (honest transparency).
9. Honest failure list (typed error codes and descriptions).
10. Triggered limitations registry list.

CRITICAL RULE (spec C1.5):
NEVER includes accuracy claims (no ground truth for production casework) —
explicitly states "Accuracy not measured for this case (production casework without ground truth)".
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


ACCURACY_DISCLAIMER = "Accuracy not measured for this case (production casework without ground truth)."


@dataclass(frozen=True)
class EvidenceSummaryItem:
    evidence_id: str
    name: str
    sha256: str
    verification_status: str  # MATCH, MISMATCH, LEGACY_UNVERIFIABLE, PENDING
    size_bytes: int = 0
    role: str = "primary"
    format_type: str = "unknown"


@dataclass(frozen=True)
class StageTiming:
    stage_name: str
    status: str  # COMPLETED, FAILED, SKIPPED, RUNNING
    duration_ms: int = 0
    error: Optional[str] = None
    counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class CaseMetricsInput:
    """Input case state for pure metrics calculation."""
    case_id: str
    evidence_items: List[EvidenceSummaryItem] = field(default_factory=list)
    last_integrity_verification: Optional[Dict[str, Any]] = None
    audit_chain_status: Dict[str, Any] = field(default_factory=lambda: {
        "is_valid": True,
        "block_count": 0,
        "head_hash": "GENESIS",
        "last_verified_at": None,
    })
    stages: List[StageTiming] = field(default_factory=list)
    parsed_counts: Dict[str, int] = field(default_factory=lambda: {
        "messages": 0,
        "contacts": 0,
        "chats": 0,
    })
    unparsed_counts: Dict[str, int] = field(default_factory=lambda: {
        "unparsed_blobs": 0,
    })
    unparsed_reasons: Dict[str, int] = field(default_factory=dict)
    findings_by_tier: Dict[str, int] = field(default_factory=lambda: {
        "tier_1": 0,
        "tier_2": 0,
        "tier_3": 0,
        "tier_4": 0,
    })
    findings_by_strength: Dict[str, int] = field(default_factory=lambda: {
        "definitive": 0,
        "strong": 0,
        "moderate": 0,
        "weak_hint": 0,
        "none": 0,
    })
    timestamp_quality_flags: Dict[str, int] = field(default_factory=dict)
    below_threshold_count: int = 0
    honest_failures: List[Dict[str, Any]] = field(default_factory=list)
    limitations_triggered: List[Dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class CaseMetrics:
    """Pure dataclass output of case metrics."""
    case_id: str
    accuracy_statement: str
    evidence_count: int
    evidence_verification_states: Dict[str, int]
    last_integrity_reverification: Optional[Dict[str, Any]]
    audit_chain_verification: Dict[str, Any]
    pipeline_stages: List[Dict[str, Any]]
    total_runtime_ms: int
    parsing_summary: Dict[str, Any]
    findings_per_tier: Dict[str, int]
    findings_per_strength: Dict[str, int]
    timestamp_quality_flags: Dict[str, int]
    below_threshold_count: int
    honest_failures: List[Dict[str, Any]]
    limitations_triggered: List[Dict[str, str]]
    computed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def case_metrics(case_state: CaseMetricsInput) -> CaseMetrics:
    """Pure function calculating production case metrics from case state.

    Adheres strictly to spec C1.5:
    - Never makes accuracy claims.
    - Aggregates verification states, audit head, stage timings, findings, and honest failures.
    """
    # 1. Verification states breakdown
    v_states: Dict[str, int] = {
        "MATCH": 0,
        "MISMATCH": 0,
        "LEGACY_UNVERIFIABLE": 0,
        "PENDING": 0,
    }
    for item in case_state.evidence_items:
        raw_st = item.verification_status.upper() if item.verification_status else "PENDING"
        if raw_st in ("OK", "VERIFIED", "MATCH"):
            st = "MATCH"
        elif raw_st in ("LEGACY_UNVERIFIABLE",):
            st = "LEGACY_UNVERIFIABLE"
        elif raw_st in ("MISMATCH", "FAILED", "TAMPERED"):
            st = "MISMATCH"
        else:
            st = raw_st
        if st not in v_states:
            v_states[st] = 0
        v_states[st] += 1

    # 2. Stage timings and total runtime
    stage_summaries = []
    total_runtime = 0
    for st in case_state.stages:
        stage_summaries.append({
            "stage": st.stage_name,
            "status": st.status,
            "duration_ms": st.duration_ms,
            "counts": st.counts,
            "error": st.error,
        })
        total_runtime += max(0, st.duration_ms)

    # 3. Parsing summary
    total_parsed = sum(case_state.parsed_counts.values())
    unparsed_blobs = case_state.unparsed_counts.get("unparsed_blobs", 0)
    parsing_summary = {
        "total_parsed_records": total_parsed,
        "breakdown": dict(case_state.parsed_counts),
        "unparsed_blobs": unparsed_blobs,
        "unparsed_reasons": dict(case_state.unparsed_reasons),
    }

    # 4. Construct CaseMetrics
    return CaseMetrics(
        case_id=case_state.case_id,
        accuracy_statement=ACCURACY_DISCLAIMER,
        evidence_count=len(case_state.evidence_items),
        evidence_verification_states=v_states,
        last_integrity_reverification=case_state.last_integrity_verification,
        audit_chain_verification={
            "valid": bool(case_state.audit_chain_status.get("is_valid", False)),
            "head_hash": case_state.audit_chain_status.get("head_hash", "GENESIS"),
            "block_count": case_state.audit_chain_status.get("block_count", 0),
            "last_verified_at": case_state.audit_chain_status.get("last_verified_at"),
        },
        pipeline_stages=stage_summaries,
        total_runtime_ms=total_runtime,
        parsing_summary=parsing_summary,
        findings_per_tier=dict(case_state.findings_by_tier),
        findings_per_strength=dict(case_state.findings_by_strength),
        timestamp_quality_flags=dict(case_state.timestamp_quality_flags),
        below_threshold_count=case_state.below_threshold_count,
        honest_failures=list(case_state.honest_failures),
        limitations_triggered=list(case_state.limitations_triggered),
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
