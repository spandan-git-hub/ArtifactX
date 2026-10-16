"""Pydantic schemas for Case Metrics endpoint (spec C1.5, 12_METRICS_AND_EVALUATION.md).

Never includes accuracy claims for production casework.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaseMetricsResponse(BaseModel):
    case_id: str = Field(..., description="Unique case identifier")
    accuracy_statement: str = Field(
        ...,
        description="Explicit policy disclaimer stating accuracy is not measured for ungrounded production casework",
    )
    evidence_count: int = Field(0, description="Total number of evidence items in this case")
    evidence_verification_states: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of evidence per verification state (MATCH, MISMATCH, LEGACY_UNVERIFIABLE, PENDING)",
    )
    last_integrity_reverification: Optional[Dict[str, Any]] = Field(
        None,
        description="Timestamp and result of most recent background or on-demand integrity re-verification",
    )
    audit_chain_verification: Dict[str, Any] = Field(
        default_factory=dict,
        description="Verification result of the SHA-256 audit log chain including block count and head hash",
    )
    pipeline_stages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Status, timings, and item counts per pipeline stage",
    )
    total_runtime_ms: int = Field(0, description="Summed wall-clock execution time across pipeline stages in ms")
    parsing_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Counts of parsed records (messages, contacts) vs unparsed blobs and reasons",
    )
    findings_per_tier: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of deleted-data recovery findings per evidential tier (tier_1 to tier_4)",
    )
    findings_per_strength: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of correlation findings per strength level (definitive to weak_hint)",
    )
    timestamp_quality_flags: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of detected timeline timestamp anomalies",
    )
    below_threshold_count: int = Field(
        0,
        description="Number of findings suppressed below reporting threshold (honest negative reporting)",
    )
    honest_failures: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Typed failure codes and explanations (e.g. ENCRYPTED_KEY_REQUIRED)",
    )
    limitations_triggered: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Technical and evidential limitations active for this case",
    )
    computed_at: str = Field(..., description="ISO 8601 UTC timestamp when metrics were computed")
