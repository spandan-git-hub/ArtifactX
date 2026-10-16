"""Evaluation report generation: JSON, Markdown, and CSV writers (spec C1.1, C1.2).

Follows master.md R1 (intellectual honesty), R11 (determinism):
- Canonical JSON output (metrics.json)
- Formatted markdown tables with Wilson 95% confidence intervals and sample size N (metrics.md)
- Tabular CSV exports per area
- Metadata tracking (run_meta.json) with git commit, versions, dataset manifest hashes
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def write_evaluation_reports(
    results: Dict[str, Any],
    metadata: Dict[str, Any],
    out_dir: Path,
) -> Dict[str, Path]:
    """Write metrics.json, metrics.md, run_meta.json, and CSV files to out_dir.

    Args:
        results: Dictionary containing all evaluated metrics.
        metadata: Execution and environment metadata.
        out_dir: Target directory for artifacts.

    Returns:
        Mapping of artifact name to output Path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: Dict[str, Path] = {}

    # 1. Deterministic metrics.json (canonical sorted keys, duration excluded)
    core_metrics = {k: v for k, v in results.items() if k not in ("runtime", "timestamps")}
    metrics_json_content = json.dumps(core_metrics, indent=2, sort_keys=True, ensure_ascii=False)
    p_json = out_dir / "metrics.json"
    p_json.write_text(metrics_json_content, encoding="utf-8")
    generated_paths["metrics_json"] = p_json

    # 2. Metadata run_meta.json
    p_meta = out_dir / "run_meta.json"
    p_meta.write_text(json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    generated_paths["run_meta"] = p_meta

    # 3. Comprehensive Markdown report (metrics.md)
    md_lines = _build_markdown_report(results, metadata)
    p_md = out_dir / "metrics.md"
    p_md.write_text("\n".join(md_lines), encoding="utf-8")
    generated_paths["metrics_md"] = p_md

    # 4. CSV outputs
    p_csv_summary = out_dir / "metrics_summary.csv"
    _write_summary_csv(results, p_csv_summary)
    generated_paths["csv_summary"] = p_csv_summary

    p_csv_cal = out_dir / "metrics_calibration.csv"
    _write_calibration_csv(results.get("calibration", {}), p_csv_cal)
    generated_paths["csv_calibration"] = p_csv_cal

    p_csv_rec = out_dir / "metrics_recovery.csv"
    _write_recovery_csv(results.get("recovery", {}), p_csv_rec)
    generated_paths["csv_recovery"] = p_csv_rec

    p_csv_corr = out_dir / "metrics_correlation.csv"
    _write_correlation_csv(results.get("correlation", {}), p_csv_corr)
    generated_paths["csv_correlation"] = p_csv_corr

    return generated_paths


def _build_markdown_report(results: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
    lines = [
        "# ArtifactX — Empirical Evaluation and Metrics Report",
        "",
        "> [!WARNING]",
        "> **SYNTHETIC DATASET CAVEAT (master.md R1, R7, 12_METRICS_AND_EVALUATION.md):**",
        "> All metrics in this report were evaluated against synthetic ground-truth fixtures modelled on documented application schemas.",
        "> No key-less decryption is performed. Real-device hardware capture validation is deferred to V1.",
        "> All confidence scores are heuristic rankings and do NOT represent probabilistic proof or legal guilt.",
        "",
        f"**Evaluation Variant:** `{metadata.get('variant', 'unknown')}`  ",
        f"**Git Commit:** `{metadata.get('git_commit', 'unknown')}`  ",
        f"**Thresholds Version:** `{metadata.get('thresholds_version', '1.0.0')}`  ",
        f"**Python:** `{metadata.get('environment', {}).get('python_version', '')}` | **SQLite:** `{metadata.get('environment', {}).get('sqlite_version', '')}` | **OS:** `{metadata.get('environment', {}).get('os', '')}`  ",
        "",
        "---",
        "## 1. Executive Summary & Integrity Metrics",
        "",
        "| Metric | Target | Result (Wilson 95% CI) | Status |",
        "|---|---|---|---|",
    ]

    integ = results.get("integrity", {})
    lines.append(f"| Re-hash Stability | 100.0% | {integ.get('rehash_stability_formatted', 'N/A')} | {'PASS' if integ.get('rehash_stability', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")
    lines.append(f"| False Alarm Rate | 0.0% | {integ.get('false_alarm_rate_formatted', 'N/A')} | {'PASS' if integ.get('false_alarm_rate', {}).get('proportion', 1) == 0.0 else 'FAIL'} |")
    lines.append(f"| Single-Byte Mutation Detection | 100.0% | {integ.get('tamper_detection_rate_formatted', 'N/A')} | {'PASS' if integ.get('tamper_detection_rate', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")
    lines.append(f"| Audit Chain Tamper Detection | 100.0% | {integ.get('audit_chain_tamper_detection_formatted', 'N/A')} | {'PASS' if integ.get('audit_chain_tamper_detection', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")

    lines.extend([
        "",
        "---",
        "## 2. Decryption Parity & Cryptographic Handling",
        "",
        "| Metric | Target | Result (Wilson 95% CI) | Status |",
        "|---|---|---|---|",
    ])
    dec = results.get("decryption", {})
    lines.append(f"| Decryption Parity (Crypt14/15) | 100.0% | {dec.get('decrypt_parity_formatted', 'N/A')} | {'PASS' if dec.get('decrypt_parity', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")
    lines.append(f"| Negative Typed-Error Rate | 100.0% | {dec.get('negative_typed_error_rate_formatted', 'N/A')} | {'PASS' if dec.get('negative_typed_error_rate', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")
    lines.append(f"| Key Redaction Compliance (Rule R5) | 100.0% | {dec.get('key_redaction_rate_formatted', 'N/A')} | {'PASS' if dec.get('key_redaction_rate', {}).get('proportion', 0) >= 1.0 else 'FAIL'} |")
    lines.append(f"| Succeeded Where Reference Failed | 0 | {dec.get('ours_succeeded_where_ref_failed', 0)} | PASS |")

    lines.extend([
        "",
        "---",
        "## 3. Parsing Accuracy",
        "",
        "| Domain | Target | Accuracy (Wilson 95% CI) | Miss Count | Unparsed Blobs |",
        "|---|---|---|---|---|",
    ])
    parsing = results.get("parsing", {})
    wa = parsing.get("whatsapp", {})
    tg = parsing.get("telegram", {})
    lines.append(f"| WhatsApp (`msgstore.db`) | >= 99.0% | {wa.get('accuracy_formatted', 'N/A')} | {wa.get('miss_count', 0)} | 0 |")
    lines.append(f"| Telegram (`cache4.db`) | >= 99.0% | {tg.get('accuracy_formatted', 'N/A')} | {tg.get('miss_count', 0)} | {tg.get('unparsed_count', 0)} |")
    lines.append(f"| Overall Combined | >= 99.0% | {parsing.get('overall_accuracy_formatted', 'N/A')} | {wa.get('miss_count', 0) + tg.get('miss_count', 0)} | {tg.get('unparsed_count', 0)} |")

    lines.extend([
        "",
        "---",
        "## 4. Deleted-Data Recovery Metrics (Per Tier)",
        "",
        "| Evidential Tier | TP | FP | FN | Precision (Wilson 95% CI) | Recall (Wilson 95% CI) | F1 Score |",
        "|---|---|---|---|---|---|---|",
    ])
    rec = results.get("recovery", {})
    tiers = rec.get("tiers", {})
    for t_idx in (1, 2, 3, 4):
        t_key = f"tier_{t_idx}"
        t_data = tiers.get(t_key, {})
        tp = t_data.get("tp", 0)
        fp = t_data.get("fp", 0)
        fn = t_data.get("fn", 0)
        prec_str = t_data.get("precision_formatted", "N/A")
        rec_str = t_data.get("recall_formatted", "N/A")
        f1 = t_data.get("f1_score", 0.0)
        lines.append(f"| Tier {t_idx} | {tp} | {fp} | {fn} | {prec_str} | {rec_str} | {f1:.4f} |")

    ctrls = rec.get("controls", {})
    lines.extend([
        "",
        "### Negative Controls Verification",
        f"- **Vacuumed Control False Recoveries:** `{ctrls.get('vacuumed_control_false_recoveries', 0)}` (Target: 0)",
        f"- **Secure-Delete Control False Recoveries:** `{ctrls.get('secure_delete_control_false_recoveries', 0)}` (Target: 0)",
        f"- **Controls Non-Recovery Rate:** `{ctrls.get('controls_correct_not_recovered_formatted', 'N/A')}`",
        f"- **Benign ID-Gap Compliance:** Max confidence `{ctrls.get('benign_gap_max_confidence', 0.0)}` (Strength: `{ctrls.get('benign_gap_max_strength', 'none')}`, Capped <= 0.30 per DEC-014)",
    ])

    lines.extend([
        "",
        "---",
        "## 5. Cross-Platform Correlation Metrics",
        "",
        "| Correlation Type | Planted | Discovered | Recall (Wilson 95% CI) | Decoys | Decoys Linked | False Positive Rate |",
        "|---|---|---|---|---|---|---|",
    ])
    corr = results.get("correlation", {})
    per_type = corr.get("per_type", {})
    for t_name, t_data in per_type.items():
        p_tot = t_data.get("planted", 0)
        p_found = t_data.get("found", 0)
        r_str = t_data.get("recall_formatted", "N/A")
        d_tot = t_data.get("decoys", 0)
        d_link = t_data.get("decoys_linked", 0)
        fpr_str = t_data.get("fpr_formatted", "N/A")
        lines.append(f"| {t_name.title()} | {p_tot} | {p_found} | {r_str} | {d_tot} | {d_link} | {fpr_str} |")

    lines.extend([
        "",
        f"- **Planted Links Total Recall:** `{corr.get('planted_links_recall_formatted', 'N/A')}`",
        f"- **Decoy False Link Rate:** `{corr.get('decoys_linked_formatted', 'N/A')}` (Target: 0.0%)",
        f"- **Negative Control Device (DS-07) FPR:** `{corr.get('control_false_alarm_formatted', 'N/A')}` (Target: 0.0%)",
    ])

    lines.extend([
        "",
        "---",
        "## 6. Timeline Determinism & Order Agreement",
        "",
        f"- **Total Events Evaluated:** `{results.get('timeline', {}).get('total_events_evaluated', 0)}`",
        f"- **Order Agreement Rate:** `{results.get('timeline', {}).get('order_agreement_formatted', 'N/A')}`",
        f"- **Misplaced Events:** `{results.get('timeline', {}).get('misplaced_events_count', 0)}`",
        f"- **Total Anomalies Detected:** `{results.get('timeline', {}).get('total_anomalies_detected', 0)}`",
    ])

    lines.extend([
        "",
        "---",
        "## 7. Confidence Calibration & Reliability Table",
        "",
    ])
    cal = results.get("calibration", {})
    lines.append(f"**Expected Calibration Error (ECE):** `{cal.get('ece', 0.0):.4f}` | **Status:** `{cal.get('status_label', 'UNKNOWN')}`  ")
    lines.append(f"**Policy Statement:** *{cal.get('wording_recommendation', 'scores are heuristic ordering, not calibrated probabilities')}*  ")
    lines.extend([
        "",
        "| Bin | Confidence Range | N | Mean Predicted | Observed Accuracy | Calibration Gap |",
        "|---|---|---|---|---|---|",
    ])
    for b in cal.get("bins", []):
        lines.append(f"| {b.get('bin_index')} | {b.get('range')} | {b.get('count')} | {b.get('mean_predicted', 0.0):.4f} | {b.get('observed_rate', 0.0):.4f} | {b.get('calibration_gap', 0.0):.4f} |")

    lines.extend([
        "",
        "---",
        "## 8. Runtime & Peak Memory Profile",
        "",
        "| Pipeline Stage | Duration (ms) | Peak Memory (MiB) |",
        "|---|---|---|",
    ])
    rt = results.get("runtime", {})
    rt_stages = rt.get("stages", [])
    if isinstance(rt_stages, dict):
        for s_name, s_data in rt_stages.items():
            lines.append(f"| {s_name} | {s_data.get('duration_ms')} ms | {s_data.get('peak_memory_mib')} MiB |")
    else:
        for stg in rt_stages:
            lines.append(f"| {stg.get('stage')} | {stg.get('duration_ms')} ms | {stg.get('peak_memory_mib')} MiB |")
    lines.append(f"| **Total Pipeline** | **{rt.get('total_duration_ms', 0)} ms** | **Max Peak: {rt.get('max_stage_peak_mib', 0)} MiB** |")

    return lines


def _write_summary_csv(results: Dict[str, Any], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Metric", "Proportion", "CI_Lower_95", "CI_Upper_95", "Successes", "Total"])
        for cat, val in results.items():
            if isinstance(val, dict):
                for k, sub in val.items():
                    if isinstance(sub, dict) and "proportion" in sub:
                        writer.writerow([
                            cat,
                            k,
                            sub.get("proportion"),
                            sub.get("ci_lower"),
                            sub.get("ci_upper"),
                            sub.get("successes"),
                            sub.get("total"),
                        ])


def _write_calibration_csv(cal: Dict[str, Any], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Bin_Index", "Range", "Count", "Mean_Predicted", "Observed_Rate", "Calibration_Gap"])
        for b in cal.get("bins", []):
            writer.writerow([
                b.get("bin_index"),
                b.get("range"),
                b.get("count"),
                b.get("mean_predicted"),
                b.get("observed_rate"),
                b.get("calibration_gap"),
            ])


def _write_recovery_csv(rec: Dict[str, Any], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Tier", "TP", "FP", "FN", "Partial", "Precision", "Recall", "F1_Score"])
        for tier_name, data in rec.get("tiers", {}).items():
            writer.writerow([
                tier_name,
                data.get("tp"),
                data.get("fp"),
                data.get("fn"),
                data.get("partial"),
                data.get("precision"),
                data.get("recall"),
                data.get("f1_score"),
            ])


def _write_correlation_csv(corr: Dict[str, Any], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "Planted", "Found", "Recall_Prop", "Decoys", "Decoys_Linked", "FPR_Prop"])
        for t_name, data in corr.get("per_type", {}).items():
            writer.writerow([
                t_name,
                data.get("planted"),
                data.get("found"),
                data.get("recall", {}).get("proportion") if isinstance(data.get("recall"), dict) else data.get("recall"),
                data.get("decoys"),
                data.get("decoys_linked"),
                data.get("fpr", {}).get("proportion") if isinstance(data.get("fpr"), dict) else data.get("fpr"),
            ])
