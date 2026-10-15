"""Shared forensic contracts and provenance data structures (spec B7.0, master.md R8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

Strength = Literal["deterministic", "strong", "moderate", "weak_hint"]


@dataclass(frozen=True)
class Provenance:
    """Forensic provenance metadata tracking evidence origin and extraction method."""
    evidence_id: str
    evidence_sha256: str
    source_table: str
    row_id: Optional[int]
    page_no: Optional[int] = None
    byte_offset: Optional[int] = None
    method: str = "sqlite_parse"
    tool_version: str = "1.0.0"
    derived_from_artifact_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_sha256": self.evidence_sha256,
            "source_table": self.source_table,
            "row_id": self.row_id,
            "page_no": self.page_no,
            "byte_offset": self.byte_offset,
            "method": self.method,
            "tool_version": self.tool_version,
            "derived_from_artifact_id": self.derived_from_artifact_id,
        }


@dataclass(frozen=True)
class FindingBase:
    """
    R8 Contract: Base dataclass for all forensic findings.
    
    Carries:
    - finding_id: deterministic sha256 hex[:32]
    - confidence_score: strictly < 1.0 for any inference (1.0 for deterministic)
    - strength: 'deterministic' | 'strong' | 'moderate' | 'weak_hint'
    - limitations: tuple of explicit limitations
    - provenance: Provenance object with evidence ID/hash, source table, offset/row
    """
    finding_id: str
    confidence_score: float
    strength: Strength
    limitations: Tuple[str, ...]
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "confidence_score": self.confidence_score,
            "strength": self.strength,
            "limitations": list(self.limitations),
            "provenance": self.provenance.to_dict(),
        }
