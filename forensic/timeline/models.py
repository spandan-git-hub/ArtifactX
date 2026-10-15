"""Forensic timeline data models and event structures (Rule R8, R10, R11)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from forensic.common.canonical import canonical_bytes, canonical_json

TimeUnit = Literal["s", "ms", "us", "exif_naive", "exif_offset", "gps_utc", "unknown"]
TzBasis = Literal["utc_source", "offset_given", "naive_unknown_tz", "not_applicable"]
TimelineApp = Literal["whatsapp", "telegram", "media", "system"]
TimelineStrength = Literal["deterministic", "strong", "moderate", "weak_hint"]

SOURCE_PRIORITY: Dict[str, int] = {
    "system": 0,
    "message": 10,
    "edit": 20,
    "revocation": 30,
    "location": 40,
    "call": 50,
    "media_exif": 60,
    "recovered_record": 70,
}


@dataclass(frozen=True)
class TimeValue:
    """R10 contract: raw source timestamp and normalized UTC timestamp always."""
    raw: int | str
    unit: TimeUnit
    utc_ms: Optional[int]
    tz_basis: TzBasis
    flags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        iso_str = None
        if self.utc_ms is not None:
            try:
                dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=self.utc_ms)
                iso_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            except (OverflowError, ValueError):
                iso_str = None

        return {
            "raw": self.raw,
            "unit": self.unit,
            "utc_ms": self.utc_ms,
            "tz_basis": self.tz_basis,
            "flags": list(self.flags),
            "iso_utc": iso_str,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Representation safe for canonical_json (no floats, ints/strings only)."""
        return {
            "flags": sorted(list(self.flags)),
            "raw": str(self.raw),
            "tz_basis": self.tz_basis,
            "unit": self.unit,
            "utc_ms": self.utc_ms if self.utc_ms is not None else 0,
            "has_utc": 1 if self.utc_ms is not None else 0,
        }


@dataclass(frozen=True)
class SourceRef:
    """Traceable provenance link to underlying evidence bytes and database row."""
    evidence_id: Optional[int]
    evidence_sha256: str
    source_table: str
    source_row_id: Optional[int | str] = None
    offset: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_sha256": self.evidence_sha256,
            "source_table": self.source_table,
            "source_row_id": self.source_row_id,
            "offset": self.offset,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id if self.evidence_id is not None else 0,
            "evidence_sha256": self.evidence_sha256,
            "offset": self.offset if self.offset is not None else -1,
            "source_row_id": str(self.source_row_id) if self.source_row_id is not None else "",
            "source_table": self.source_table,
        }


@dataclass(frozen=True)
class TimelineEvent:
    """
    R8 & R11 Canonical Timeline Event.
    
    Deterministic ID, total sort order key, full provenance references,
    quality-flagged timestamps, and explicit strength/limitations.
    """
    event_id: str
    kind: str
    app: TimelineApp
    time: TimeValue
    actor_ref: Optional[str]
    chat_ref: Optional[str]
    summary: str
    source_refs: Tuple[SourceRef, ...]
    confidence_score: float = 1.0
    strength: TimelineStrength = "deterministic"
    limitations: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def sort_key(self) -> Tuple[bool, int, int, str, int, str, str]:
        """
        Total ordering sort key per spec B11.2:
        (utc_ms is None, utc_ms, SOURCE_PRIORITY[kind], source_table, source_row_id/offset, event_id)
        
        Events with unknown timestamp (utc_ms=None) sort last deterministically.
        """
        has_no_time = self.time.utc_ms is None
        time_val = self.time.utc_ms if self.time.utc_ms is not None else 0
        priority = SOURCE_PRIORITY.get(self.kind, 99)

        table = ""
        row_num = 0
        row_str = ""
        if self.source_refs:
            ref = self.source_refs[0]
            table = ref.source_table
            if ref.source_row_id is not None:
                if isinstance(ref.source_row_id, int):
                    row_num = ref.source_row_id
                elif str(ref.source_row_id).isdigit():
                    row_num = int(ref.source_row_id)
                else:
                    row_str = str(ref.source_row_id)
            elif ref.offset is not None:
                row_num = ref.offset

        return (has_no_time, time_val, priority, table, row_num, row_str, self.event_id)

    def to_dict(self) -> Dict[str, Any]:
        """Full dictionary representation."""
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "app": self.app,
            "time": self.time.to_dict(),
            "actor_ref": self.actor_ref,
            "chat_ref": self.chat_ref,
            "summary": self.summary,
            "source_refs": [ref.to_dict() for ref in self.source_refs],
            "confidence_score": self.confidence_score,
            "strength": self.strength,
            "limitations": list(self.limitations),
            "metadata": self.metadata,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Deterministic representation safe for canonical_json (Rule R11):
        - No non-integer floats (confidence_score converted to basis points: 1.0 -> 10000)
        - Lexicographically sorted keys
        - Deterministic nested structures
        """
        confidence_bp = int(round(self.confidence_score * 10_000))
        return {
            "actor_ref": self.actor_ref or "",
            "app": self.app,
            "chat_ref": self.chat_ref or "",
            "confidence_basis_points": confidence_bp,
            "event_id": self.event_id,
            "kind": self.kind,
            "limitations": sorted(list(self.limitations)),
            "source_refs": [ref.to_canonical_dict() for ref in self.source_refs],
            "strength": self.strength,
            "summary": self.summary,
            "time": self.time.to_canonical_dict(),
        }


def compute_canonical_event_id(
    kind: str,
    evidence_sha256: str,
    source_table: str,
    row_or_offset: Any,
    raw_time: Any,
    key_facts: Dict[str, Any],
) -> str:
    """
    Compute 32-character deterministic event ID per spec B11.2:
    sha256(canonical(kind, evidence_sha256, source_table, row_id|offset, time.raw, key facts))[:32]
    """
    cleaned_facts: Dict[str, Any] = {}
    for k, v in sorted(key_facts.items()):
        if isinstance(v, (int, bool)):
            cleaned_facts[k] = v
        elif isinstance(v, float):
            cleaned_facts[k] = int(round(v * 10_000))
        else:
            cleaned_facts[k] = str(v) if v is not None else ""

    data = {
        "evidence_sha256": str(evidence_sha256),
        "key_facts": cleaned_facts,
        "kind": str(kind),
        "raw_time": str(raw_time),
        "row_or_offset": str(row_or_offset) if row_or_offset is not None else "",
        "source_table": str(source_table),
    }
    digest = hashlib.sha256(canonical_bytes(data)).hexdigest()
    return digest[:32]


def compute_timeline_hash(events: List[TimelineEvent]) -> str:
    """
    Compute 64-character SHA-256 hash across canonically ordered timeline events.
    Guarantees that identical event sequences yield identical content hashes (R11).
    """
    canonical_list = [event.to_canonical_dict() for event in events]
    return hashlib.sha256(canonical_bytes(canonical_list)).hexdigest()
