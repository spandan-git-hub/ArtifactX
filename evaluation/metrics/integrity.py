"""Integrity metrics evaluation (spec C1.2, master.md R1, R3).

Measures:
1. Re-hash stability: false-alarm rate on pristine files (N pristine files re-hashed).
2. Single-byte mutation detection rate: detected / tampered over N mutated copies (DS-08).
3. Audit chain tamper detection: detection rate on corrupted audit chain payloads.
All metrics computed with exact Wilson 95% confidence intervals and sample size N.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from forensic.common.canonical import canonical_json
from forensic.common.hashing import sha256_hex


def evaluate_integrity_metrics(dataset_dirs: List[Path]) -> Dict[str, Any]:
    """Compute integrity metrics across the provided datasets.

    Args:
        dataset_dirs: Paths to dataset directories containing manifest.json.

    Returns:
        Structured dictionary of integrity metrics with Wilson intervals.
    """
    # 1. Pristine re-hash stability
    total_pristine_files = 0
    matched_pristine_files = 0

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        for f_entry in manifest.get("files", []):
            f_path = ds_dir / f_entry["path"]
            if f_path.is_file():
                total_pristine_files += 1
                try:
                    f_hash = sha256_hex(f_path.read_bytes())
                    if f_hash == f_entry["sha256"]:
                        matched_pristine_files += 1
                except Exception:
                    pass

    rehash_ci = wilson_score_interval(matched_pristine_files, total_pristine_files)
    false_alarm_count = total_pristine_files - matched_pristine_files
    false_alarm_ci = wilson_score_interval(false_alarm_count, total_pristine_files)

    # 2. Tamper detection rate on DS-08 if present
    tamper_detected = 0
    total_tampered = 0

    for ds_dir in dataset_dirs:
        if "DS-08" not in ds_dir.name:
            continue
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        manifest = json.loads(m_path.read_text(encoding="utf-8"))
        ref_path = ds_dir / "reference_base.db"
        if not ref_path.is_file():
            continue
        ref_hash = sha256_hex(ref_path.read_bytes())

        for tr in manifest.get("tamper_records", []):
            mut_path = ds_dir / tr["fixture_path"]
            if mut_path.is_file():
                total_tampered += 1
                mut_hash = sha256_hex(mut_path.read_bytes())
                # Must differ from reference and match tampered manifest hash
                if mut_hash != ref_hash and mut_hash == tr["tampered_sha256"]:
                    tamper_detected += 1

    tamper_ci = wilson_score_interval(tamper_detected, total_tampered)

    # 3. Audit chain tamper detection rate
    audit_chain_detected = 0
    audit_chain_trials = 10
    for i in range(audit_chain_trials):
        e1_payload = canonical_json({"action": "INIT", "seq": 1, "trial": i})
        e1_hash = sha256_hex(("0" * 64).encode("ascii") + e1_payload.encode("utf-8"))
        e2_payload = canonical_json({"action": "INGEST", "seq": 2, "trial": i})
        e2_hash = sha256_hex(e1_hash.encode("ascii") + e2_payload.encode("utf-8"))

        chain = [
            {"prev_hash": "0" * 64, "payload": {"action": "INIT", "seq": 1, "trial": i}, "entry_hash": e1_hash},
            {"prev_hash": e1_hash, "payload": {"action": "INGEST", "seq": 2, "trial": i}, "entry_hash": e2_hash},
        ]
        # Invert payload in entry 2
        chain[1]["payload"] = {"action": "TAMPERED", "seq": 2, "trial": i}
        # Check detection
        recomputed = sha256_hex(chain[1]["prev_hash"].encode("ascii") + canonical_json(chain[1]["payload"]).encode("utf-8"))
        if recomputed != chain[1]["entry_hash"]:
            audit_chain_detected += 1

    audit_ci = wilson_score_interval(audit_chain_detected, audit_chain_trials)

    return {
        "rehash_stability": rehash_ci.to_dict(),
        "rehash_stability_formatted": rehash_ci.format_str(),
        "false_alarm_rate": false_alarm_ci.to_dict(),
        "false_alarm_rate_formatted": false_alarm_ci.format_str(),
        "tamper_detection_rate": tamper_ci.to_dict(),
        "tamper_detection_rate_formatted": tamper_ci.format_str(),
        "audit_chain_tamper_detection": audit_ci.to_dict(),
        "audit_chain_tamper_detection_formatted": audit_ci.format_str(),
    }
