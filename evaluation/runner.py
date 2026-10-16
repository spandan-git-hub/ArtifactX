"""ArtifactX Evaluation Runner (spec C1.1, C1.2, C1.3, C1.4).

CLI command:
python -m evaluation.runner --variant dev|holdout --datasets all --out evaluation_out/

Follows master.md:
- R1 (truth over appearance): Wilson intervals, ECE, honest negative controls.
- R4 (zero disk writes): evaluation outputs written only to designated --out directory.
- R6 (no synthetic data in app): evaluation imports forensic core, never vice versa.
- R11 (determinism): canonical JSON, frozen seeds, deterministic sorting.
- C1.4 (dev/holdout protocol): refuses holdout if configs differ from FROZEN.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.matching import match_correlation_item, match_recovery_item
from evaluation.metrics.calibration import compute_calibration
from evaluation.metrics.correlation import evaluate_correlation_metrics
from evaluation.metrics.decryption import evaluate_decryption_metrics
from evaluation.metrics.integrity import evaluate_integrity_metrics
from evaluation.metrics.parsing import evaluate_parsing_metrics
from evaluation.metrics.recovery import evaluate_recovery_metrics
from evaluation.metrics.runtime import RuntimeProfiler, get_environment_info
from evaluation.metrics.timeline import evaluate_timeline_metrics
from evaluation.report import write_evaluation_reports
from forensic.common.canonical import canonical_json
from forensic.common.hashing import sha256_hex
from forensic.correlation.thresholds import THRESHOLDS_VERSION
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput, PipelineConfig

FROZEN_CONFIG_FILES = [
    "forensic/correlation/thresholds.py",
    "forensic/timeline/config.py",
    "acceptance.yaml",
]

FROZEN_FILE_PATH = ROOT_DIR / "evaluation" / "FROZEN.json"


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT_DIR),
            stderr=subprocess.DEVNULL,
        )
        return out.decode("ascii").strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def compute_config_hashes() -> Dict[str, str]:
    hashes = {}
    for rel_path in FROZEN_CONFIG_FILES:
        p = ROOT_DIR / rel_path
        if p.is_file():
            hashes[rel_path] = sha256_hex(p.read_bytes())
        else:
            hashes[rel_path] = "MISSING"
    return hashes


def freeze_configs(out_path: Path = FROZEN_FILE_PATH) -> Dict[str, Any]:
    """Freeze current configuration hashes and git commit into FROZEN.json."""
    config_hashes = compute_config_hashes()
    frozen_payload = {
        "git_commit": get_git_commit(),
        "thresholds_version": THRESHOLDS_VERSION,
        "config_hashes": config_hashes,
        "frozen_rule": "Holdout runs require exact matching hashes per spec C1.4",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(frozen_payload, indent=2, sort_keys=True), encoding="utf-8")
    return frozen_payload


def verify_frozen_configs(frozen_path: Optional[Path] = None) -> Tuple[bool, str]:
    """Verify that current configuration hashes match FROZEN.json.

    Returns (is_valid, error_message).
    """
    target_path = frozen_path or FROZEN_FILE_PATH
    if not target_path.is_file():
        return False, f"Missing {target_path.name}. Holdout evaluation requires frozen configurations per spec C1.4."

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"Failed to parse {frozen_path.name}: {e}"

    recorded_hashes = data.get("config_hashes", {})
    current_hashes = compute_config_hashes()

    for rel_path, rec_hash in recorded_hashes.items():
        curr_hash = current_hashes.get(rel_path)
        if curr_hash != rec_hash:
            return False, (
                f"Configuration hash mismatch for {rel_path}!\n"
                f"  Frozen:  {rec_hash}\n"
                f"  Current: {curr_hash}\n"
                f"Per spec C1.4, holdout runs are strictly rejected on configuration drift."
            )

    return True, ""


def collect_calibration_samples(dataset_dirs: List[Path]) -> List[Tuple[float, bool]]:
    """Collect (confidence_score, ground_truth_label) across datasets."""
    samples: List[Tuple[float, bool]] = []

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Build pipeline inputs
        evidence_inputs = []
        for f_entry in manifest.get("files", []):
            f_path = ds_dir / f_entry["path"]
            if f_path.is_file() and ("msgstore.db" in f_path.name or "cache4.db" in f_path.name or f_path.suffix in (".jpg", ".png")):
                evidence_inputs.append(
                    EvidenceInput(
                        evidence_id=f"{ds_dir.name}_{f_path.name}",
                        sha256=f_entry["sha256"],
                        name=f_path.name,
                        data=f_path.read_bytes(),
                        role="primary" if "msgstore" in f_path.name or "cache4" in f_path.name else "supplementary",
                    )
                )

        if not evidence_inputs:
            continue

        pipe_res = run_pipeline(evidence_inputs)

        # 1. Recovery findings
        manifest_deletions = manifest.get("deletions")
        if not manifest_deletions and manifest.get("whatsapp"):
            manifest_deletions = (manifest.get("whatsapp") or {}).get("deletions", [])
        if not manifest_deletions and manifest.get("telegram"):
            manifest_deletions = (manifest.get("telegram") or {}).get("deletions", [])
        manifest_deletions = manifest_deletions or []

        for rf in pipe_res.recovered_records:
            is_tp = False
            for del_item in manifest_deletions:
                exact, partial = match_recovery_item(rf, del_item)
                if exact or partial:
                    is_tp = True
                    break
            samples.append((rf.confidence_score, is_tp))

        # 2. Correlation findings
        shared_entities = manifest.get("shared_entities", [])
        for cf in pipe_res.correlation_findings:
            is_tp = any(match_correlation_item(cf, se) for se in shared_entities)
            samples.append((cf.confidence_score, is_tp))

    return samples


def run_evaluation(
    variant: str = "dev",
    datasets: str = "all",
    out_dir: Optional[Path] = None,
    freeze_on_dev: bool = False,
    frozen_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run full evaluation suite across datasets for a variant."""
    if variant == "holdout":
        valid, msg = verify_frozen_configs(frozen_path=frozen_path)
        if not valid:
            raise RuntimeError(f"HOLDOUT RUN REJECTED (spec C1.4): {msg}")

    # Discover datasets
    all_ds_dirs = sorted([
        d for d in (ROOT_DIR / "testdata").iterdir()
        if d.is_dir() and d.name.endswith(f"-{variant}")
    ])
    if not all_ds_dirs:
        raise ValueError(f"No datasets found for variant '{variant}' in {ROOT_DIR / 'testdata'}")

    profiler = RuntimeProfiler()
    env_info = get_environment_info()

    # 1. Integrity metrics
    with profiler.measure("integrity"):
        integrity_metrics = evaluate_integrity_metrics(all_ds_dirs)

    # 2. Decryption metrics
    with profiler.measure("decryption"):
        decryption_metrics = evaluate_decryption_metrics(all_ds_dirs)

    # 3. Parsing metrics
    with profiler.measure("parsing"):
        parsing_metrics = evaluate_parsing_metrics(all_ds_dirs)

    # 4. Recovery metrics
    with profiler.measure("recovery"):
        recovery_metrics = evaluate_recovery_metrics(all_ds_dirs)

    # 5. Correlation metrics
    with profiler.measure("correlation"):
        correlation_metrics = evaluate_correlation_metrics(all_ds_dirs)

    # 6. Timeline metrics
    with profiler.measure("timeline"):
        timeline_metrics = evaluate_timeline_metrics(all_ds_dirs)

    # 7. Confidence calibration
    with profiler.measure("calibration"):
        cal_samples = collect_calibration_samples(all_ds_dirs)
        calibration_result = compute_calibration(cal_samples)

    # Collect dataset manifest hashes
    ds_manifest_hashes = {}
    for d in all_ds_dirs:
        m_file = d / "manifest.json"
        if m_file.is_file():
            ds_manifest_hashes[d.name] = sha256_hex(m_file.read_bytes())

    metadata = {
        "variant": variant,
        "git_commit": get_git_commit(),
        "thresholds_version": THRESHOLDS_VERSION,
        "dataset_manifest_hashes": ds_manifest_hashes,
        "environment": env_info.to_dict(),
    }

    results = {
        "integrity": integrity_metrics,
        "decryption": decryption_metrics,
        "parsing": parsing_metrics,
        "recovery": recovery_metrics,
        "correlation": correlation_metrics,
        "timeline": timeline_metrics,
        "calibration": calibration_result.to_dict(),
        "runtime": profiler.to_dict(),
    }

    if out_dir:
        write_evaluation_reports(results, metadata, out_dir)

    if variant == "dev" and freeze_on_dev:
        freeze_configs()

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="ArtifactX Evaluation Runner (C1.1)")
    parser.add_argument("--variant", choices=["dev", "holdout"], default="dev", help="Dataset variant to evaluate")
    parser.add_argument("--datasets", default="all", help="Dataset filter ('all' or specific IDs)")
    parser.add_argument("--out", default="evaluation_out", help="Output directory for reports and metrics")
    parser.add_argument("--freeze", action="store_true", help="Freeze configurations into evaluation/FROZEN.json before running")
    parser.add_argument("--freeze-only", action="store_true", help="Freeze configurations into evaluation/FROZEN.json and exit")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT_DIR / out_path

    if args.freeze or args.freeze_only:
        frozen = freeze_configs()
        print(f"Configurations frozen into {FROZEN_FILE_PATH.relative_to(ROOT_DIR)}:")
        for k, v in frozen["config_hashes"].items():
            print(f"  {k}: {v[:16]}...")
        if args.freeze_only:
            return 0

    print(f"Starting ArtifactX evaluation on variant: {args.variant}...")
    try:
        run_evaluation(variant=args.variant, datasets=args.datasets, out_dir=out_path)
        print(f"Evaluation completed successfully. Reports generated in {out_path.relative_to(ROOT_DIR)}.")
        return 0
    except Exception as e:
        print(f"Evaluation FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
