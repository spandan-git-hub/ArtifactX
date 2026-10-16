"""
Pure forensic pipeline data models (spec 11_PIPELINE_AND_E2E.md §B13.1).

Strictly adheres to:
- master.md R4: Zero disk writes; pure in-memory data structures.
- master.md R5: Keys are radioactive. Secret bytes never stored in representations or results.
- master.md R8: Complete forensic provenance and typed findings strength.
- master.md R11: Total determinism; wall-clock fields excluded from cryptographic content hashes.
- master.md R18: Pure models with type hints and docstrings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.types import KeyMaterial


StageStatus = Literal["COMPLETED", "SKIPPED", "FAILED_HONEST", "ERROR"]
PipelineStatus = Literal["COMPLETED", "PARTIAL", "FAILED"]


@dataclass(frozen=True)
class EvidenceInput:
    """In-memory evidence exhibit input container (bytes in)."""

    evidence_id: str
    sha256: str
    name: str
    data: bytes
    role: Optional[Literal["primary", "wal", "shm", "wa_contacts", "media_zip", "key_file", "other"]] = None

    def __repr__(self) -> str:
        return (
            f"EvidenceInput(evidence_id={self.evidence_id!r}, sha256={self.sha256[:8]}..., "
            f"name={self.name!r}, size={len(self.data)}, role={self.role!r})"
        )


@dataclass(frozen=True)
class PipelineConfig:
    """Execution parameters and threshold configuration for the forensic pipeline."""

    thresholds_version: str = "1.0.0"
    timeline_cfg: Any = None
    recovery_cfg: Any = None
    max_unpacked_bytes: int = 256 * 1024 * 1024
    correlation_params: Dict[str, Any] = field(default_factory=dict)
    custom_keywords: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thresholds_version": self.thresholds_version,
            "max_unpacked_bytes": self.max_unpacked_bytes,
            "correlation_params": dict(self.correlation_params),
            "custom_keywords": list(self.custom_keywords),
        }


@dataclass(frozen=True)
class StageResult:
    """Structured result of an individual analysis stage."""

    stage: str
    status: StageStatus
    started_at: str
    duration_ms: float
    counts: Dict[str, int]
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]
    output_hash: str
    evidence_id: Optional[str] = None
    error_code: Optional[str] = None
    skip_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "counts": dict(self.counts),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "output_hash": self.output_hash,
            "evidence_id": self.evidence_id,
            "error_code": self.error_code,
            "skip_reason": self.skip_reason,
            "details": dict(self.details),
        }

    def canonical_content_bytes(self) -> bytes:
        """Deterministic serialization of stage payload, strictly excluding wall-clock and duration fields (R11)."""
        content_obj = {
            "stage": self.stage,
            "evidence_id": self.evidence_id,
            "status": self.status,
            "error_code": self.error_code,
            "skip_reason": self.skip_reason,
            "counts": dict(sorted(self.counts.items())),
            "warnings": sorted(self.warnings),
            "errors": sorted(self.errors),
            "details": self.details,
        }
        return json.dumps(content_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class PipelineResult:
    """Overall outcome of a deterministic pipeline execution run."""

    run_id: str
    status: PipelineStatus
    content_hash: str
    stages: Tuple[StageResult, ...]
    summary: Dict[str, Any]
    started_at: str
    completed_at: str
    duration_ms: float
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_data: bool = True) -> Dict[str, Any]:
        res = {
            "run_id": self.run_id,
            "status": self.status,
            "content_hash": self.content_hash,
            "stages": [s.to_dict() for s in self.stages],
            "summary": dict(self.summary),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }
        if include_data:
            safe_data: Dict[str, Any] = {}
            for k, v in self.data.items():
                if k == "decrypted_databases" and isinstance(v, dict):
                    safe_data[k] = {
                        eid: {
                            "size_bytes": len(raw),
                            "sha256": sha256_hex(raw),
                        }
                        if isinstance(raw, (bytes, bytearray))
                        else raw
                        for eid, raw in v.items()
                    }
                elif isinstance(v, dict):
                    safe_data[k] = {
                        sub_k: sub_v.to_dict() if hasattr(sub_v, "to_dict") else sub_v
                        for sub_k, sub_v in v.items()
                    }
                elif isinstance(v, (list, tuple)):
                    safe_data[k] = [
                        item.to_dict() if hasattr(item, "to_dict") else item for item in v
                    ]
                elif hasattr(v, "to_dict"):
                    safe_data[k] = v.to_dict()
                else:
                    safe_data[k] = v
            res["data"] = safe_data
        return res

    @property
    def correlation_findings(self) -> List[Any]:
        """Convenience property for correlation findings in result data."""
        return list(self.data.get("correlations", []))

    @property
    def timeline_events(self) -> List[Any]:
        """Convenience property for timeline events in result data."""
        t = self.data.get("timeline")
        return list(getattr(t, "events", [])) if t else []

    @property
    def recovered_records(self) -> List[Any]:
        """Convenience property for recovered records in result data."""
        rec = self.data.get("recovered", {})
        if isinstance(rec, dict):
            findings: List[Any] = []
            for r in rec.values():
                findings.extend(getattr(r, "findings", []))
            return findings
        return []
