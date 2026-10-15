"""Spatiotemporal Rendezvous and Geographic Co-occurrence Engine (B12.5).

Correlates EXIF GPS, live locations, and shared map coordinates across evidence sources.
Computes Haversine great-circle distance and temporal delta with configurable thresholds.

Follows master.md R8, R10, R11 and 10_CORRELATION.md §B12.5:
- Events with unknown timestamp (utc_ms is None) are strictly excluded.
- Distance threshold <= 250 meters (configurable).
- Time window threshold <= 7200 seconds (2 hours) using normalized UTC milliseconds.
- Decoys (distance > 250m, time > 2h, different geographic places) produce ZERO findings.
- Confidence score strictly < 1.0; strength <= moderate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

from forensic.correlation.models import CorrelationFinding, generate_deterministic_finding_id
from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS

EARTH_RADIUS_METERS: float = 6371000.0


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points on the earth in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


@dataclass
class LocationObservation:
    """Represents a discrete geospatial observation extracted from evidence."""
    observation_id: str
    source_type: str  # 'media_exif', 'wa_location', 'tg_location'
    source_id: str
    platform: str
    latitude: float
    longitude: float
    utc_ms: Optional[int]
    evidence_id: Optional[int] = None
    sender_id: Optional[str] = None
    accuracy_radius_meters: Optional[float] = None
    label: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    # Backwards compatibility alias for timestamp
    @property
    def timestamp(self) -> Optional[int]:
        return self.utc_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "platform": self.platform,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "utc_ms": self.utc_ms,
            "timestamp": self.utc_ms,
            "evidence_id": self.evidence_id,
            "sender_id": self.sender_id,
            "accuracy_radius_meters": self.accuracy_radius_meters,
            "label": self.label,
            "provenance": self.provenance,
        }


@dataclass
class RendezvousCandidate:
    """Candidate co-occurrence event meeting distance and temporal thresholds."""
    rendezvous_id: str
    observation_a: LocationObservation
    observation_b: LocationObservation
    distance_meters: float
    time_delta_seconds: int
    distance_threshold_meters: float
    time_threshold_seconds: int
    confidence_score: float
    match_certainty: float
    classification: str = "SPATIOTEMPORAL_RENDEZVOUS_CANDIDATE"
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rendezvous_id": self.rendezvous_id,
            "observation_a": self.observation_a.to_dict(),
            "observation_b": self.observation_b.to_dict(),
            "distance_meters": round(self.distance_meters, 2),
            "time_delta_seconds": self.time_delta_seconds,
            "distance_threshold_meters": self.distance_threshold_meters,
            "time_threshold_seconds": self.time_threshold_seconds,
            "confidence_score": round(self.confidence_score, 4),
            "match_certainty": round(self.match_certainty, 4),
            "classification": self.classification,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class SpatiotemporalRendezvousDetector:
    """
    Detector for geographical and temporal co-occurrence events.
    Enforces master.md R8, R10, R11 and 10_CORRELATION.md §B12.5.
    """

    def __init__(self, thresholds: CorrelationThresholds = DEFAULT_THRESHOLDS):
        self.thresholds = thresholds
        self.default_distance_threshold_meters = thresholds.rendezvous_max_distance_meters
        self.default_time_threshold_seconds = thresholds.rendezvous_max_time_seconds
        self.version = thresholds.version

    def detect_rendezvous(
        self,
        observations: List[LocationObservation],
        distance_threshold_meters: Optional[float] = None,
        time_threshold_seconds: Optional[int] = None,
    ) -> List[RendezvousCandidate]:
        """Detect rendezvous candidates between distinct evidence observations."""
        dist_limit = distance_threshold_meters if distance_threshold_meters is not None else self.default_distance_threshold_meters
        time_limit = time_threshold_seconds if time_threshold_seconds is not None else self.default_time_threshold_seconds

        candidates = []
        n = len(observations)

        for i in range(n):
            for j in range(i + 1, n):
                obs_a = observations[i]
                obs_b = observations[j]

                # R10: refuse events with unknown time rather than guessing
                if obs_a.utc_ms is None or obs_b.utc_ms is None:
                    continue

                # Don't pair observations from the exact same message/event
                if obs_a.platform == obs_b.platform and obs_a.source_id == obs_b.source_id:
                    continue

                dist_m = haversine_distance_meters(
                    obs_a.latitude, obs_a.longitude,
                    obs_b.latitude, obs_b.longitude,
                )
                if dist_m > dist_limit:
                    continue

                delta_sec = int(abs(obs_a.utc_ms - obs_b.utc_ms) / 1000.0)
                if delta_sec > time_limit:
                    continue

                # Compute match_certainty and confidence_score
                # match_certainty reflects physical co-location precision
                dist_factor = max(0.0, 1.0 - (dist_m / dist_limit))
                time_factor = max(0.0, 1.0 - (delta_sec / time_limit))
                match_cert = round(0.5 * (dist_factor + time_factor), 4)

                # Confidence in the inference (meeting / physical rendezvous) is strictly < 1.0
                conf = round(min(0.85, 0.60 + 0.25 * match_cert), 4)

                norm_val = f"geo_{obs_a.latitude:.4f},{obs_a.longitude:.4f}_delta_{int(dist_m)}m_{delta_sec}s"
                f_id = generate_deterministic_finding_id(
                    "spatiotemporal_rendezvous",
                    norm_val,
                    f"{obs_a.platform}:{obs_a.source_id}",
                    f"{obs_b.platform}:{obs_b.source_id}",
                    self.thresholds.version,
                )

                candidates.append(RendezvousCandidate(
                    rendezvous_id=f_id,
                    observation_a=obs_a,
                    observation_b=obs_b,
                    distance_meters=dist_m,
                    time_delta_seconds=delta_sec,
                    distance_threshold_meters=dist_limit,
                    time_threshold_seconds=time_limit,
                    confidence_score=conf,
                    match_certainty=match_cert,
                    classification="SPATIOTEMPORAL_RENDEZVOUS_CANDIDATE",
                    limitations=[
                        f"Spatiotemporal proximity: {dist_m:.1f}m (limit <= {dist_limit}m), {delta_sec}s apart (limit <= {time_limit}s).",
                        "Co-occurrence does not prove physical meeting or interaction (public space / ambient presence possible).",
                        "GPS coordinates subject to device hardware accuracy and multi-path reflection errors.",
                    ],
                    provenance={
                        "algorithm": "HaversineSpatiotemporal",
                        "distance_meters": round(dist_m, 2),
                        "time_delta_seconds": delta_sec,
                        "distance_limit": dist_limit,
                        "time_limit": time_limit,
                        "thresholds_version": self.thresholds.version,
                    },
                ))

        candidates.sort(key=lambda c: (c.distance_meters, c.time_delta_seconds))
        return candidates

    def detect_rendezvous_findings(
        self,
        observations: List[LocationObservation],
        distance_threshold_meters: Optional[float] = None,
        time_threshold_seconds: Optional[int] = None,
    ) -> List[CorrelationFinding]:
        """Returns CorrelationFinding instances from location observations."""
        candidates = self.detect_rendezvous(observations, distance_threshold_meters, time_threshold_seconds)
        findings = []

        for cand in candidates:
            obs_a = cand.observation_a
            obs_b = cand.observation_b
            norm_val = f"geo_{obs_a.latitude:.4f},{obs_a.longitude:.4f}_delta_{int(cand.distance_meters)}m_{cand.time_delta_seconds}s"

            findings.append(CorrelationFinding(
                finding_id=cand.rendezvous_id,
                kind="spatiotemporal_rendezvous",
                strength="moderate",
                match_certainty=cand.match_certainty,
                confidence_score=cand.confidence_score,
                normalized_value=norm_val,
                left_ref=obs_a.to_dict(),
                right_ref=obs_b.to_dict(),
                limitations=tuple(cand.limitations),
                provenance=cand.provenance,
                thresholds_version=self.thresholds.version,
                below_threshold=cand.confidence_score < self.thresholds.report_threshold_confidence,
            ))

        findings.sort(key=lambda f: f.sort_key())
        return findings
