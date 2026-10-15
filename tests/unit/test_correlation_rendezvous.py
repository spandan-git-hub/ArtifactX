"""Unit tests for spatiotemporal rendezvous detection and boundary conditions (B12.5).

Follows master.md R8, R10, R11 and 10_CORRELATION.md §B12.5:
- Haversine distance tests.
- Boundary tests: 249m / 251m and 119min / 121min.
- Strict exclusion of events lacking valid normalized timestamp (utc_ms is None).
- Rejection of planted rendezvous decoys (distance exceeded, time exceeded, different cities).
"""

import pytest

from forensic.correlation.rendezvous import (
    haversine_distance_meters,
    LocationObservation,
    SpatiotemporalRendezvousDetector,
)
from forensic.correlation.thresholds import DEFAULT_THRESHOLDS


def test_haversine_distance_known_coordinates():
    """Verify Haversine formula against known coordinate pair (Gateway of India to Taj Mahal Palace, ~200m)."""
    # Gateway of India: 18.921984, 72.834654
    # Taj Mahal Palace Hotel: 18.921700, 72.833300
    dist = haversine_distance_meters(18.921984, 72.834654, 18.921700, 72.833300)
    assert 140.0 <= dist <= 160.0


def test_rendezvous_boundary_distance_249m_vs_251m():
    """Verify strict boundary at 250m: 249m matches, 251m is excluded."""
    detector = SpatiotemporalRendezvousDetector()
    lat0, lon0 = 18.921984, 72.834654
    ts = 1789826400000

    # ~1 deg lat is ~111,000 meters. 1 meter is ~1/111000 deg = 0.000009009 deg
    delta_249m = 249.0 / 111139.0
    delta_251m = 251.0 / 111139.0

    obs_base = LocationObservation("loc_0", "wa_location", "1", "whatsapp", lat0, lon0, ts)
    obs_249m = LocationObservation("loc_249", "tg_location", "2", "telegram", lat0 + delta_249m, lon0, ts)
    obs_251m = LocationObservation("loc_251", "tg_location", "3", "telegram", lat0 + delta_251m, lon0, ts)

    # Test 249m pair: within 250m
    cands_249 = detector.detect_rendezvous([obs_base, obs_249m])
    assert len(cands_249) == 1
    assert cands_249[0].distance_meters <= 250.0

    # Test 251m pair: exceeds 250m
    cands_251 = detector.detect_rendezvous([obs_base, obs_251m])
    assert len(cands_251) == 0


def test_rendezvous_boundary_time_119min_vs_121min():
    """Verify strict boundary at 120min (7200s): 119 min matches, 121 min is excluded."""
    detector = SpatiotemporalRendezvousDetector()
    lat0, lon0 = 18.921984, 72.834654
    ts0 = 1789826400000  # ms

    ts_119min = ts0 + (119 * 60 * 1000)
    ts_121min = ts0 + (121 * 60 * 1000)

    obs_base = LocationObservation("loc_0", "wa_location", "1", "whatsapp", lat0, lon0, ts0)
    obs_119m = LocationObservation("loc_119", "tg_location", "2", "telegram", lat0, lon0, ts_119min)
    obs_121m = LocationObservation("loc_121", "tg_location", "3", "telegram", lat0, lon0, ts_121min)

    cands_119 = detector.detect_rendezvous([obs_base, obs_119m])
    assert len(cands_119) == 1

    cands_121 = detector.detect_rendezvous([obs_base, obs_121m])
    assert len(cands_121) == 0


def test_rendezvous_excludes_unknown_timestamps():
    """Rule R10: observations lacking timestamps (utc_ms=None) must be excluded from rendezvous."""
    detector = SpatiotemporalRendezvousDetector()
    obs_valid = LocationObservation("loc_1", "wa_location", "1", "whatsapp", 18.921984, 72.834654, 1789826400000)
    obs_no_time = LocationObservation("loc_2", "tg_location", "2", "telegram", 18.921984, 72.834654, None)

    cands = detector.detect_rendezvous([obs_valid, obs_no_time])
    assert len(cands) == 0


def test_rendezvous_decoys_rejected():
    """Verify rejection of the 3 planted rendezvous decoys from DS-06."""
    detector = SpatiotemporalRendezvousDetector()
    base_ts = 1789826400000
    obs_wa = LocationObservation("loc_wa", "wa_location", "wa_1", "whatsapp", 18.921984, 72.834654, base_ts)

    # Decoy 1: distance 391m (>250m)
    decoy_dist = LocationObservation("decoy_dist", "tg_location", "tg_d1", "telegram", 18.925500, 72.834654, base_ts + 600000)
    assert len(detector.detect_rendezvous([obs_wa, decoy_dist])) == 0

    # Decoy 2: time 210 min (>120 min)
    decoy_time = LocationObservation("decoy_time", "tg_location", "tg_d2", "telegram", 18.921984, 72.834654, base_ts + (210 * 60 * 1000))
    assert len(detector.detect_rendezvous([obs_wa, decoy_time])) == 0

    # Decoy 3: different city (Delhi vs Mumbai, ~1150km)
    decoy_delhi = LocationObservation("decoy_delhi", "tg_location", "tg_d3", "telegram", 28.632743, 77.219597, base_ts)
    assert len(detector.detect_rendezvous([obs_wa, decoy_delhi])) == 0
