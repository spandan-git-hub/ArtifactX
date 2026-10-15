"""Single thresholds configuration for cross-platform correlation (B12.1).

All correlation thresholds live in this file as a frozen dataclass with a version tag.
Tuned on dev only (master.md R1, DEC-013, 10_CORRELATION.md).
"""

from dataclasses import dataclass

THRESHOLDS_VERSION: str = "1.0.0"


@dataclass(frozen=True)
class CorrelationThresholds:
    """Configurable, frozen threshold parameter set for correlation engine."""
    version: str = THRESHOLDS_VERSION

    # Phone normalization & identity (B12.2)
    phone_default_region: str = "IN"

    # Perceptual media correlation (B12.4)
    dhash_max_hamming_distance: int = 4
    phash_max_hamming_distance: int = 8
    min_image_dimension: int = 16
    min_image_entropy: float = 1.0

    # Spatiotemporal rendezvous (B12.5)
    rendezvous_max_distance_meters: float = 250.0
    rendezvous_max_time_seconds: int = 7200  # 2 hours

    # Platform handover (B12.5)
    handover_max_time_seconds: int = 180  # 3 minutes

    # Headline reporting threshold (B12.6)
    report_threshold_confidence: float = 0.50


DEFAULT_THRESHOLDS = CorrelationThresholds()
