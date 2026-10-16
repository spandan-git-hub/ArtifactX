"""Unit tests for evaluation metrics calculations (spec C1, 12_METRICS_AND_EVALUATION.md).

Tests:
1. Exact Wilson score interval formula and edge cases.
2. Calibration reliability table, ECE, MCE, and heuristic ordering policy.
3. Matching algorithms: message identity, recovery item matching, correlation matching.
4. Determinism of evaluation report writers (JSON, MD, CSV).
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from evaluation.matching import match_correlation_item, match_message_record, match_recovery_item
from evaluation.metrics.calibration import CalibrationBin, CalibrationResult, compute_calibration
from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from evaluation.report import write_evaluation_reports


def test_wilson_score_interval_known_values():
    """Verify Wilson 95% score interval matches exact statistical formula."""
    # 0 out of 0 -> [0.0, 0.0]
    ci_0 = wilson_score_interval(0, 0)
    assert ci_0.proportion == 0.0
    assert ci_0.ci_lower == 0.0
    assert ci_0.ci_upper == 0.0
    assert ci_0.total == 0

    # 10 out of 10 successes -> proportion 1.0, lower > 0.69
    ci_10 = wilson_score_interval(10, 10)
    assert ci_10.proportion == 1.0
    assert ci_10.ci_upper == pytest.approx(1.0, abs=1e-5)
    assert 0.69 <= ci_10.ci_lower <= 0.73

    # 0 out of 10 successes -> proportion 0.0, upper ~ 0.278
    ci_none = wilson_score_interval(0, 10)
    assert ci_none.proportion == 0.0
    assert ci_none.ci_lower == 0.0
    assert 0.25 <= ci_none.ci_upper <= 0.29

    # 50 out of 100 successes -> proportion 0.5, symmetric around 0.5
    ci_half = wilson_score_interval(50, 100)
    assert ci_half.proportion == 0.5
    assert 0.40 <= ci_half.ci_lower <= 0.41
    assert 0.59 <= ci_half.ci_upper <= 0.60
    assert abs((0.5 - ci_half.ci_lower) - (ci_half.ci_upper - 0.5)) < 1e-4

    # String format check
    fmt = ci_10.format_str()
    assert "100.0% (N=10, 95% CI [" in fmt


def test_confidence_calibration_ece_and_heuristic_status():
    """Test 10-bin calibration reliability table, ECE, and honest policy labelling."""
    # Empty samples
    cal_empty = compute_calibration([])
    assert cal_empty.total_samples == 0
    assert cal_empty.status_label in ("UNVERIFIED", "INSUFFICIENT_DATA")

    # Perfect calibration synthetic vector
    # 10 samples predicted at 0.9, all 10 true
    # 10 samples predicted at 0.1, all 10 false (observed 0.0)
    samples = [(0.95, True)] * 10 + [(0.05, False)] * 10
    cal_perf = compute_calibration(samples)
    assert cal_perf.total_samples == 20
    assert len(cal_perf.bins) == 10
    # Expected Calibration Error should be very small
    assert cal_perf.ece <= 0.10

    # Uncalibrated / Heuristic ordering synthetic vector
    # High confidence (0.95) but 0% accuracy
    bad_samples = [(0.95, False)] * 20
    cal_bad = compute_calibration(bad_samples)
    assert cal_bad.is_calibrated is False
    assert cal_bad.status_label == "HEURISTIC_ORDERING"
    assert "heuristic ordering" in cal_bad.wording_recommendation
    assert cal_bad.ece > 0.50


def test_matching_message_identity():
    """Test record-identity matching on WhatsApp and Telegram messages."""
    class DummyMsg:
        def __init__(self, mid, text, sender, ts):
            self.message_id = mid
            self.row_id = mid
            self.mid = mid
            self.body = text
            self.text = text
            self.sender_jid = sender
            self.from_id = sender
            self.timestamp = ts
            self.ts_utc_ms = ts
            self.date_utc_ms = ts

    # WA message matching
    wa_msg = DummyMsg("101", "Confidential meeting", "919876543210@s.whatsapp.net", 1789826400000)
    manifest_wa = {
        "row_id": 101,
        "text": "Confidential meeting",
        "sender": "919876543210@s.whatsapp.net",
        "timestamp_ms": 1789826400000,
    }
    res = match_message_record(wa_msg, manifest_wa, is_whatsapp=True)
    assert res["all_match"] is True

    # Mutated text
    manifest_mutated = dict(manifest_wa, text="Different text")
    res_mut = match_message_record(wa_msg, manifest_mutated, is_whatsapp=True)
    assert res_mut["body"] is False
    assert res_mut["all_match"] is False


def test_matching_recovery_item():
    """Test deleted-data recovery item exact and partial matching."""
    class DummyFinding:
        def __init__(self, tier, val_status, key_id, row_id, body):
            self.tier = tier
            self.validation_status = val_status
            self.key_id = key_id
            self.row_id = row_id
            self.recovered_fields = {"key_id": key_id, "row_id": row_id, "body": body}
            self.raw_payload_preview = body

    del_manifest = {
        "marker": "SECRET_PLAN",
        "original_key_id": "ABC123XYZ",
        "original_message_row_id": 42,
        "expected_tier": "tier_2_wal",
    }

    # Exact valid match
    f_exact = DummyFinding(2, "FULL_RECORD_VALID", "ABC123XYZ", 42, "Here is SECRET_PLAN")
    exact, partial = match_recovery_item(f_exact, del_manifest)
    assert exact is True
    assert partial is False

    # Partial match
    f_partial = DummyFinding(2, "PARTIAL", "ABC123XYZ", 42, "Here is SECRET_PLAN")
    exact_p, partial_p = match_recovery_item(f_partial, del_manifest)
    assert exact_p is False
    assert partial_p is True

    # Wrong tier
    f_wrong_tier = DummyFinding(3, "FULL_RECORD_VALID", "ABC123XYZ", 42, "Here is SECRET_PLAN")
    exact_w, partial_w = match_recovery_item(f_wrong_tier, del_manifest)
    assert exact_w is False
    assert partial_w is False


def test_evaluation_reports_deterministic_generation():
    """Test evaluation report generator writes JSON, Markdown, and CSVs deterministically."""
    results = {
        "integrity": {"rehash_stability": {"proportion": 1.0, "total": 10, "ci_lower": 0.7, "ci_upper": 1.0}},
        "decryption": {"decryption_parity": {"proportion": 1.0, "total": 2, "ci_lower": 0.34, "ci_upper": 1.0}},
        "parsing": {
            "whatsapp": {"accuracy": {"proportion": 1.0, "total": 100, "ci_lower": 0.96, "ci_upper": 1.0}, "misses": 0, "unparsed_blobs": 0},
            "telegram": {"accuracy": {"proportion": 1.0, "total": 100, "ci_lower": 0.96, "ci_upper": 1.0}, "misses": 0, "unparsed_blobs": 0},
            "combined": {"accuracy": {"proportion": 1.0, "total": 200, "ci_lower": 0.98, "ci_upper": 1.0}, "misses": 0, "unparsed_blobs": 0},
        },
        "recovery": {
            "per_tier": {
                1: {"tp": 1, "fp": 0, "fn": 0, "precision": {"proportion": 1.0, "total": 1, "ci_lower": 0.2, "ci_upper": 1.0}, "recall": {"proportion": 1.0, "total": 1, "ci_lower": 0.2, "ci_upper": 1.0}, "f1": 1.0},
            },
            "controls": {"vacuumed_false_recoveries": 0, "secure_delete_false_recoveries": 0, "non_recovery_rate": {"proportion": 1.0, "total": 2, "ci_lower": 0.34, "ci_upper": 1.0}},
            "benign_gap_compliance": {"max_confidence": 0.0, "max_strength": "none"},
        },
        "correlation": {
            "planted_links_recall": {"proportion": 1.0, "total": 7, "ci_lower": 0.64, "ci_upper": 1.0},
            "decoys_linked_rate": {"proportion": 0.0, "total": 9, "ci_lower": 0.0, "ci_upper": 0.29},
            "control_false_alarm_rate": {"proportion": 0.0, "total": 10, "ci_lower": 0.0, "ci_upper": 0.27},
            "per_type": {},
        },
        "timeline": {
            "total_events": 100,
            "order_agreement": {"proportion": 1.0, "total": 100, "ci_lower": 0.96, "ci_upper": 1.0},
            "misplaced_events": 0,
            "anomalies_detected": 0,
        },
        "calibration": {
            "ece": 0.02,
            "is_calibrated": True,
            "status_label": "CALIBRATED",
            "wording_recommendation": "scores are calibrated probabilities",
            "bins": [],
            "total_samples": 20,
        },
        "runtime": {
            "stages": {"parse": {"duration_ms": 12.3, "peak_memory_mib": 4.5}},
            "total_wall_ms": 15.0,
        },
    }

    metadata = {
        "variant": "dev",
        "git_commit": "abcdef123456",
        "thresholds_version": "1.0.0",
        "environment": {"python_version": "3.14.6", "sqlite_version": "3.53.1", "os": "Windows"},
    }

    with TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir)
        write_evaluation_reports(results, metadata, out_path)

        # Check all required files are written
        assert (out_path / "metrics.json").is_file()
        assert (out_path / "metrics.md").is_file()
        assert (out_path / "metrics_summary.csv").is_file()
        assert (out_path / "metrics_recovery.csv").is_file()
        assert (out_path / "metrics_correlation.csv").is_file()
        assert (out_path / "metrics_calibration.csv").is_file()
        assert (out_path / "run_meta.json").is_file()

        # Check synthetic dataset caveat in Markdown
        md_text = (out_path / "metrics.md").read_text(encoding="utf-8")
        assert "SYNTHETIC DATASET CAVEAT" in md_text
        assert "No key-less decryption is performed" in md_text
