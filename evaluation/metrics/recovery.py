"""Recovery metrics evaluation per tier and method (spec C1.2, master.md R1, R7, R8).

Measures:
1. Precision, Recall, and F1 score per tier (Tier 1 explicit, Tier 2 WAL, Tier 3 carving, Tier 4 gaps).
2. Separate tracking of partial matches.
3. Negative controls verification:
   - vacuumed_control: correct_not_recovered vs false_recovery.
   - secure_delete_control: correct_not_recovered vs false_recovery.
4. Benign gap control verification:
   - maximum strength reported must not exceed 'weak_hint' (confidence <= 0.30, DEC-014).
5. Exact Wilson 95% confidence intervals on recall and precision proportions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.matching import match_recovery_item
from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from forensic.recovery.orchestrator import RecoveryPipeline


def evaluate_recovery_metrics(dataset_dirs: List[Path]) -> Dict[str, Any]:
    """Compute recovery P/R/F1 per tier and verify controls across datasets."""
    tier_stats: Dict[int, Dict[str, int]] = {
        1: {"tp": 0, "fp": 0, "fn": 0, "partial": 0},
        2: {"tp": 0, "fp": 0, "fn": 0, "partial": 0},
        3: {"tp": 0, "fp": 0, "fn": 0, "partial": 0},
        4: {"tp": 0, "fp": 0, "fn": 0, "partial": 0},
    }

    vacuumed_control_recovered = 0
    secure_delete_control_recovered = 0
    benign_gap_max_strength = "none"
    benign_gap_max_conf = 0.0

    total_controls_tested = 0
    correct_controls_not_recovered = 0

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        manifest_deletions = manifest.get("deletions")
        if not manifest_deletions and manifest.get("whatsapp"):
            manifest_deletions = (manifest.get("whatsapp") or {}).get("deletions", [])
        if not manifest_deletions and manifest.get("telegram"):
            manifest_deletions = (manifest.get("telegram") or {}).get("deletions", [])
        manifest_deletions = manifest_deletions or []

        manifest_controls = manifest.get("controls") or []

        # Run recovery on WhatsApp if present
        wa_db = ds_dir / "msgstore.db"
        tg_db = ds_dir / "cache4.db"

        findings = []
        if wa_db.is_file():
            wa_wal = ds_dir / "msgstore.db-wal"
            wal_bytes = wa_wal.read_bytes() if wa_wal.is_file() else None
            pipeline = RecoveryPipeline(
                db_bytes=wa_db.read_bytes(),
                wal_bytes=wal_bytes,
                app_hint="whatsapp",
                evidence_id=f"{ds_dir.name}_wa",
            )
            findings.extend(pipeline.run().findings)

        if tg_db.is_file():
            tg_wal = ds_dir / "cache4.db-wal"
            wal_bytes = tg_wal.read_bytes() if tg_wal.is_file() else None
            pipeline = RecoveryPipeline(
                db_bytes=tg_db.read_bytes(),
                wal_bytes=wal_bytes,
                app_hint="telegram",
                evidence_id=f"{ds_dir.name}_tg",
            )
            findings.extend(pipeline.run().findings)

        # Filter out DUPLICATE_OF_LIVE
        active_findings = [
            f for f in findings
            if f.validation_status in ("FULL_RECORD_VALID", "PARTIAL")
        ]

        # Match manifest deletions
        matched_finding_ids = set()
        for del_item in manifest_deletions:
            exp_tier_str = del_item.get("expected_tier", "")
            tier_num = 1 if "tier_1" in exp_tier_str else (2 if "tier_2" in exp_tier_str else (3 if "tier_3" in exp_tier_str else (4 if "tier_4" in exp_tier_str else 0)))
            if tier_num == 0:
                continue

            found_exact = False
            found_partial = False
            for f in active_findings:
                if id(f) in matched_finding_ids:
                    continue
                exact, partial = match_recovery_item(f, del_item)
                if exact:
                    found_exact = True
                    matched_finding_ids.add(id(f))
                    break
                elif partial:
                    found_partial = True
                    matched_finding_ids.add(id(f))
                    break

            if found_exact:
                tier_stats[tier_num]["tp"] += 1
            elif found_partial:
                tier_stats[tier_num]["partial"] += 1
                tier_stats[tier_num]["tp"] += 1
            else:
                tier_stats[tier_num]["fn"] += 1

        # Any active findings not matched to manifest are FP
        for f in active_findings:
            if id(f) not in matched_finding_ids:
                t = f.tier if f.tier in tier_stats else 3
                tier_stats[t]["fp"] += 1

        # Check negative controls
        for ctrl in manifest_controls:
            ctrl_type = ctrl.get("type")
            marker = ctrl.get("marker", "")

            if ctrl_type == "vacuumed_control":
                total_controls_tested += 1
                is_recovered = any(marker in str(f.recovered_fields.get("body", "")) or marker in f.raw_payload_preview for f in findings)
                if is_recovered:
                    vacuumed_control_recovered += 1
                else:
                    correct_controls_not_recovered += 1

            elif ctrl_type == "secure_delete_control":
                total_controls_tested += 1
                is_recovered = any(marker in str(f.recovered_fields.get("body", "")) or marker in f.raw_payload_preview for f in findings)
                if is_recovered:
                    secure_delete_control_recovered += 1
                else:
                    correct_controls_not_recovered += 1

            elif ctrl_type == "benign_gap":
                for f in findings:
                    if f.tier == 4:
                        if f.confidence_score > benign_gap_max_conf:
                            benign_gap_max_conf = f.confidence_score
                        benign_gap_max_strength = f.strength

    # Calculate P/R/F1 per tier
    tier_results = {}
    for t_idx, s in tier_stats.items():
        tp = s["tp"]
        fp = s["fp"]
        fn = s["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        prec_ci = wilson_score_interval(tp, tp + fp) if (tp + fp) > 0 else wilson_score_interval(0, 0)
        rec_ci = wilson_score_interval(tp, tp + fn) if (tp + fn) > 0 else wilson_score_interval(0, 0)

        tier_results[f"tier_{t_idx}"] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "partial": s["partial"],
            "precision": round(prec, 4),
            "precision_formatted": prec_ci.format_str() if (tp + fp) > 0 else "N/A",
            "recall": round(rec, 4),
            "recall_formatted": rec_ci.format_str() if (tp + fn) > 0 else "N/A",
            "f1_score": round(f1, 4),
        }

    control_ci = wilson_score_interval(correct_controls_not_recovered, total_controls_tested)

    return {
        "tiers": tier_results,
        "controls": {
            "vacuumed_control_false_recoveries": vacuumed_control_recovered,
            "secure_delete_control_false_recoveries": secure_delete_control_recovered,
            "controls_correct_not_recovered_rate": control_ci.to_dict(),
            "controls_correct_not_recovered_formatted": control_ci.format_str(),
            "benign_gap_max_confidence": round(benign_gap_max_conf, 4),
            "benign_gap_max_strength": benign_gap_max_strength,
            "benign_gap_compliant": benign_gap_max_conf <= 0.30 and benign_gap_max_strength in ("weak_hint", "none"),
        },
    }
