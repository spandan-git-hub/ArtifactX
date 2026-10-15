"""Correlation finding data models and deterministic finding ID generation (B12.6).

Follows master.md R8, R10, R11 and 10_CORRELATION.md §0, §B12.6:
- Confidence score is strictly < 1.0 for all inferences.
- match_certainty is separated from confidence_score.
- Every finding includes strength, limitations, left_ref, right_ref, provenance, ambiguity.
- Total deterministic sort key for output consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple


def generate_deterministic_finding_id(
    kind: str,
    normalized_value: str,
    left_key: str,
    right_key: str,
    thresholds_version: str = "1.0.0",
) -> str:
    """Generate a deterministic 24-hex finding ID based on canonical attributes."""
    # Ensure left_key and right_key order is canonical
    k1, k2 = sorted([left_key, right_key])
    content = f"{kind}|{normalized_value}|{k1}|{k2}|{thresholds_version}".encode("utf-8")
    return "corr_" + hashlib.sha256(content).hexdigest()[:20]


@dataclass(frozen=True)
class CorrelationFinding:
    """
    Immutable forensic correlation finding across exhibits.
    Conforms to 10_CORRELATION.md §0 and §B12.6.
    """
    finding_id: str
    kind: str  # phone_identity, crypto_btc, crypto_evm, banking_iban, canonical_url, media_dhash, media_sha256, platform_handover, spatiotemporal_rendezvous, reuse_within_app
    strength: str  # deterministic, strong, moderate, weak_hint
    match_certainty: float  # [0.0, 1.0]
    confidence_score: float  # Strictly < 1.0
    normalized_value: str
    left_ref: Dict[str, Any]
    right_ref: Dict[str, Any]
    limitations: Tuple[str, ...] = ()
    provenance: Dict[str, Any] = field(default_factory=dict)
    ambiguity: Tuple[str, ...] = ()
    thresholds_version: str = "1.0.0"
    below_threshold: bool = False

    def __post_init__(self):
        # Enforce Rule R8 / B12.6 invariant: confidence_score strictly < 1.0
        if self.confidence_score >= 1.0:
            raise ValueError(
                f"Rule R8 violation: confidence_score must be strictly < 1.0 for all inferences, "
                f"got {self.confidence_score} for {self.kind}:{self.finding_id}"
            )
        if not (0.0 <= self.match_certainty <= 1.0):
            raise ValueError(
                f"match_certainty must be in [0.0, 1.0], got {self.match_certainty}"
            )

    def sort_key(self) -> Tuple[str, str, str, str, str]:
        """Total deterministic sort key per 10_CORRELATION.md §B12.6."""
        left_str = json.dumps(self.left_ref, sort_keys=True)
        right_str = json.dumps(self.right_ref, sort_keys=True)
        return (self.kind, self.normalized_value, left_str, right_str, self.finding_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_uuid": self.finding_id,  # Backwards compatibility
            "kind": self.kind,
            "finding_type": self.kind,  # Backwards compatibility
            "strength": self.strength,
            "match_certainty": round(self.match_certainty, 4),
            "confidence_score": round(self.confidence_score, 4),
            "normalized_value": self.normalized_value,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "limitations": list(self.limitations),
            "provenance": self.provenance,
            "ambiguity": list(self.ambiguity),
            "thresholds_version": self.thresholds_version,
            "below_threshold": self.below_threshold,
        }
