"""
Forensic Recovery Metrics & Evaluation (spec B10.6, B10.7, master.md R1, R7, R8).

Computes:
- True Positives (TP), False Positives (FP), False Negatives (FN)
- Precision, Recall, F1 score per tier and overall vs manifest ground-truth
- Controls verification: vacuumed_control, secure_delete_control must NEVER be recovered
- Benign gap check: must not exceed weak_hint / confidence <= 0.30
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from forensic.recovery.models import RecoveryFinding


def evaluate_recovery(
    findings: List[RecoveryFinding],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate recovery findings against ground-truth manifest deletions and controls.

    Returns:
        Structured evaluation metrics dict with per-tier TP, FP, FN, precision, recall, F1,
        and controls verification status.
    """
    # Filter out DUPLICATE_OF_LIVE and DUPLICATE_OF_OTHER_TIER
    active_findings = [
        f for f in findings
        if f.validation_status in ("FULL_RECORD_VALID", "PARTIAL")
    ]

    manifest_deletions = manifest.get("deletions", [])
    if not manifest_deletions and "whatsapp" in manifest:
        manifest_deletions = manifest.get("whatsapp", {}).get("deletions", [])
    if not manifest_deletions and "telegram" in manifest:
        manifest_deletions = manifest.get("telegram", {}).get("deletions", [])

    manifest_controls = manifest.get("controls", [])

    results_per_case: Dict[str, Dict[str, Any]] = {}
    overall_tp = 0
    overall_fp = 0
    overall_fn = 0
    tier_stats: Dict[int, Dict[str, int]] = {
        1: {"tp": 0, "fp": 0, "fn": 0},
        2: {"tp": 0, "fp": 0, "fn": 0},
        3: {"tp": 0, "fp": 0, "fn": 0},
        4: {"tp": 0, "fp": 0, "fn": 0},
    }

    matched_finding_ids = set()

    for entry in manifest_deletions:
        case_id = entry.get("case_id", "unknown")
        expected_recoverable = entry.get("expected_recoverable", False)
        expected_tier_str = entry.get("expected_tier", "unrecoverable")
        marker = entry.get("marker")
        key_id = entry.get("original_key_id")
        row_id = entry.get("original_message_row_id") or entry.get("original_mid")
        method = entry.get("method")

        expected_tier = 0
        if "tier_1" in expected_tier_str:
            expected_tier = 1
        elif "tier_2" in expected_tier_str:
            expected_tier = 2
        elif "tier_3" in expected_tier_str:
            expected_tier = 3
        elif "tier_4" in expected_tier_str:
            expected_tier = 4

        # Search for a matching finding
        matched_finding: Optional[RecoveryFinding] = None

        for f in active_findings:
            if expected_tier != 0 and f.tier != expected_tier:
                continue

            f_rf = f.recovered_fields
            # Marker match in body, raw preview, or key_id
            marker_match = False
            if marker:
                marker_match = (
                    (f_rf.get("body") and marker in str(f_rf.get("body")))
                    or (f.raw_payload_preview and marker in f.raw_payload_preview)
                    or (f_rf.get("key_id") and marker == f_rf.get("key_id"))
                )

            # Key ID match
            key_match = False
            if key_id and f_rf.get("key_id"):
                key_match = str(f_rf["key_id"]) == str(key_id)

            # Row ID match (exact rowid or within gap range for Tier 4)
            row_match = False
            if row_id is not None:
                if f.row_id == row_id:
                    row_match = True
                elif f_rf.get("mid") == row_id or f_rf.get("row_id") == row_id:
                    row_match = True
                elif f_rf.get("message_row_id") == row_id:
                    row_match = True
                elif f.tier == 4 and "gap_start" in f_rf and "gap_end" in f_rf:
                    if f_rf["gap_start"] <= row_id <= f_rf["gap_end"]:
                        row_match = True

            if marker_match or key_match or row_match:
                matched_finding = f
                matched_finding_ids.add(f.finding_id)
                break

        if expected_recoverable:
            if matched_finding:
                overall_tp += 1
                if expected_tier in tier_stats:
                    tier_stats[expected_tier]["tp"] += 1
                results_per_case[case_id] = {
                    "status": "PASS",
                    "matched": True,
                    "expected_tier": expected_tier,
                    "actual_tier": matched_finding.tier,
                    "finding_id": matched_finding.finding_id,
                }
            else:
                overall_fn += 1
                if expected_tier in tier_stats:
                    tier_stats[expected_tier]["fn"] += 1
                results_per_case[case_id] = {
                    "status": "FAIL",
                    "matched": False,
                    "expected_tier": expected_tier,
                    "actual_tier": None,
                    "error": f"Expected recoverable case {case_id} was not found",
                }
        else:
            # Benign gap or unrecoverable control in deletions list
            if matched_finding:
                if expected_tier == 4:
                    # Benign gap is expected as Tier 4 weak hint
                    assert matched_finding.tier == 4
                    assert matched_finding.strength == "weak_hint"
                    assert matched_finding.confidence_score <= 0.30
                    overall_tp += 1
                    tier_stats[4]["tp"] += 1
                    results_per_case[case_id] = {
                        "status": "PASS",
                        "matched": True,
                        "expected_tier": 4,
                        "actual_tier": 4,
                        "benign_gap_verified": True,
                    }
                else:
                    overall_fp += 1
                    results_per_case[case_id] = {
                        "status": "FAIL",
                        "matched": True,
                        "expected_tier": "unrecoverable",
                        "actual_tier": matched_finding.tier,
                        "error": f"Unrecoverable case {case_id} was falsely recovered",
                    }
            else:
                results_per_case[case_id] = {
                    "status": "PASS",
                    "matched": False,
                    "expected_tier": "unrecoverable",
                    "actual_tier": None,
                    "correct_not_recovered": True,
                }

    # B10.6: Verify unrecoverable controls come back empty
    controls_verified = True
    control_violations: List[str] = []

    for ctrl in manifest_controls:
        c_type = ctrl.get("type", "")
        c_marker = ctrl.get("marker")

        if c_type in ("vacuumed_control", "secure_delete_control") and c_marker:
            for f in active_findings:
                if (
                    (f.recovered_fields.get("body") and c_marker in str(f.recovered_fields.get("body")))
                    or (f.raw_payload_preview and c_marker in f.raw_payload_preview)
                ):
                    controls_verified = False
                    control_violations.append(f"Control {c_type} marker {c_marker} found in finding {f.finding_id}")

    # Compute precision, recall, F1
    precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 1.0
    recall = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "overall": {
            "tp": overall_tp,
            "fp": overall_fp,
            "fn": overall_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "per_tier": {
            tier: {
                "tp": stats["tp"],
                "fp": stats["fp"],
                "fn": stats["fn"],
                "precision": round(stats["tp"] / (stats["tp"] + stats["fp"]), 4) if (stats["tp"] + stats["fp"]) > 0 else 1.0,
                "recall": round(stats["tp"] / (stats["tp"] + stats["fn"]), 4) if (stats["tp"] + stats["fn"]) > 0 else 1.0,
            }
            for tier, stats in tier_stats.items()
        },
        "cases": results_per_case,
        "controls_verified": controls_verified,
        "control_violations": control_violations,
    }
