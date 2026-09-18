"""
Spatiotemporal Rendezvous and Geographic Co-occurrence Engine.
Correlates EXIF GPS, live locations, and shared map coordinates across evidence sources.
Computes Haversine great-circle distance and temporal delta with configurable thresholds.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import math
import uuid


EARTH_RADIUS_METERS = 6371000.0


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in meters."""
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
    """Represents a discrete geospatial observation extracted from forensic evidence."""
    observation_id: str
    source_type: str  # 'media_exif', 'wa_location', 'tg_location'
    source_id: str
    platform: str
    latitude: float
    longitude: float
    timestamp: Optional[int]
    evidence_id: Optional[int] = None
    sender_id: Optional[str] = None
    accuracy_radius_meters: Optional[float] = None
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "platform": self.platform,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "timestamp": self.timestamp,
            "evidence_id": self.evidence_id,
            "sender_id": self.sender_id,
            "accuracy_radius_meters": self.accuracy_radius_meters,
            "label": self.label,
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
            "classification": self.classification,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class SpatiotemporalRendezvousDetector:
    """
    Detector for geographical and temporal co-occurrence events.
    Thresholds are fully configurable (default: <50 meters and <1800 seconds / 30 minutes).
    """

    def __init__(
        self,
        default_distance_threshold_meters: float = 50.0,
        default_time_threshold_seconds: int = 1800,
    ):
        self.default_distance_threshold_meters = default_distance_threshold_meters
        self.default_time_threshold_seconds = default_time_threshold_seconds
        self.version = "1.0.0"

    def detect_rendezvous(
        self,
        observations: List[LocationObservation],
        distance_threshold_meters: Optional[float] = None,
        time_threshold_seconds: Optional[int] = None,
    ) -> List[RendezvousCandidate]:
        """
        Scans pairs of location observations to find candidate co-occurrences.
        Only considers pairs from distinct platforms, accounts, or messages/media.
        """
        dist_limit = distance_threshold_meters if distance_threshold_meters is not None else self.default_distance_threshold_meters
        time_limit = time_threshold_seconds if time_threshold_seconds is not None else self.default_time_threshold_seconds

        candidates: List[RendezvousCandidate] = []
        n = len(observations)

        for i in range(n):
            for j in range(i + 1, n):
                obs_a = observations[i]
                obs_b = observations[j]

                # Avoid correlating the exact same record with itself
                if obs_a.source_id == obs_b.source_id and obs_a.source_type == obs_b.source_type:
                    continue

                # Check timestamp presence and delta
                if obs_a.timestamp is None or obs_b.timestamp is None:
                    continue

                time_delta = abs(obs_a.timestamp - obs_b.timestamp)
                if time_delta > time_limit:
                    continue

                dist = haversine_distance_meters(
                    obs_a.latitude, obs_a.longitude,
                    obs_b.latitude, obs_b.longitude
                )

                if dist <= dist_limit:
                    # Confidence calculation: weighted combination of spatial and temporal proximity
                    dist_ratio = dist / dist_limit if dist_limit > 0 else 0
                    time_ratio = time_delta / time_limit if time_limit > 0 else 0
                    confidence = max(0.60, 1.0 - (0.5 * dist_ratio + 0.5 * time_ratio) * 0.35)

                    candidate = RendezvousCandidate(
                        rendezvous_id=f"rendezvous_{uuid.uuid4().hex[:12]}",
                        observation_a=obs_a,
                        observation_b=obs_b,
                        distance_meters=dist,
                        time_delta_seconds=time_delta,
                        distance_threshold_meters=dist_limit,
                        time_threshold_seconds=time_limit,
                        confidence_score=confidence,
                        classification="SPATIOTEMPORAL_RENDEZVOUS_CANDIDATE",
                        limitations=[
                            f"Identified within {dist:.1f}m (threshold <= {dist_limit}m) and {time_delta}s (threshold <= {time_limit}s).",
                            "GPS accuracy error margins and clock-drift uncertainty apply.",
                            "Spatiotemporal proximity demonstrates co-location opportunity, not physical contact."
                        ],
                        provenance={
                            "algorithm": "HaversineGreatCircle",
                            "version": self.version,
                            "distance_threshold_meters": dist_limit,
                            "time_threshold_seconds": time_limit,
                        }
                    )
                    candidates.append(candidate)

        # Sort by distance first, then time delta
        candidates.sort(key=lambda c: (c.distance_meters, c.time_delta_seconds))
        return candidates
