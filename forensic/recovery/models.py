"""
Data structures and contracts for Deleted Data Recovery (B10, master.md R7, R8, R10).
All data structures are immutable frozen dataclasses conforming to FindingBase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from forensic.common.contracts import FindingBase, Provenance, Strength

ValidationStatus = Literal[
    "FULL_RECORD_VALID",
    "PARTIAL",
    "DUPLICATE_OF_LIVE",
    "DUPLICATE_OF_OTHER_TIER",
    "INVALID_REJECTED",
]


@dataclass(frozen=True)
class RecoveryFinding(FindingBase):
    """
    Forensic record for a recovered deleted message, edit, or indicator.
    Conforms to R8 finding contract: explicit tier, strength, limitations, and provenance.
    """
    tier: int = 1  # 1, 2, 3, 4
    kind: str = "deleted"  # revocation, edit, wal_resident, freelist, slack, id_gap
    validation_status: ValidationStatus = "FULL_RECORD_VALID"
    table_name: str = ""
    row_id: Optional[int] = None
    page_no: Optional[int] = None
    byte_offset: Optional[int] = None
    frame_index: Optional[int] = None
    view: str = "main_view"  # main_view, post_wal_view, wal_history
    recovered_fields: Dict[str, Any] = field(default_factory=dict)
    candidate_original_text: Optional[str] = None
    raw_payload_hash: str = ""
    raw_payload_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tier": self.tier,
            "kind": self.kind,
            "validation_status": self.validation_status,
            "table_name": self.table_name,
            "row_id": self.row_id,
            "page_no": self.page_no,
            "byte_offset": self.byte_offset,
            "frame_index": self.frame_index,
            "view": self.view,
            "recovered_fields": dict(self.recovered_fields),
            "candidate_original_text": self.candidate_original_text,
            "raw_payload_hash": self.raw_payload_hash,
            "raw_payload_preview": self.raw_payload_preview,
        })
        return d


@dataclass(frozen=True)
class RecoveryResult:
    """Consolidated recovery execution results across all four tiers."""
    findings: Tuple[RecoveryFinding, ...]
    total_findings_count: int
    tier_counts: Dict[int, int]
    validation_status_counts: Dict[str, int]
    invalid_rejected_count: int
    wal_pages_analyzed: int
    freelist_pages_analyzed: int
    slack_spans_analyzed: int
    warnings: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "total_findings_count": self.total_findings_count,
            "tier_counts": dict(self.tier_counts),
            "validation_status_counts": dict(self.validation_status_counts),
            "invalid_rejected_count": self.invalid_rejected_count,
            "wal_pages_analyzed": self.wal_pages_analyzed,
            "freelist_pages_analyzed": self.freelist_pages_analyzed,
            "slack_spans_analyzed": self.slack_spans_analyzed,
            "warnings": list(self.warnings),
        }
