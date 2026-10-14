"""Ground-truth dataset CLI tool.

Usage:
  python -m tools.groundtruth.cli build --dataset DS-01 --variant dev --out testdata
  python -m tools.groundtruth.cli build --dataset DS-01 --variant holdout --out testdata
  python -m tools.groundtruth.cli verify --path testdata/DS-01-dev
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.groundtruth.crypto.wa_encrypt import (
    generate_crypt14_dataset,
    generate_crypt15_dataset,
    generate_negative_dataset,
)
from tools.groundtruth.verify_dataset import verify_dataset
from tools.groundtruth.wa.generator import generate_whatsapp_plain_dataset


def build_command(dataset: str, variant: str, out_dir: Path, seed: int | None = None) -> int:
    """Build a dataset."""
    out_dir = Path(out_dir)
    target_dir = out_dir / f"{dataset}-{variant}"
    print(f"Building {dataset} ({variant}) into {target_dir} ...")

    if dataset == "DS-01":
        manifest = generate_whatsapp_plain_dataset(
            output_dir=target_dir,
            dataset_id=dataset,
            variant=variant,
            seed=seed,
        )
        print(f"[OK] {dataset} ({variant}) successfully generated: {len(manifest.files)} files, {len(manifest.whatsapp['messages'])} messages.")
    elif dataset in ("DS-02", "DS-03", "DS-04"):
        plain_dir = out_dir / f"DS-01-{variant}"
        if not (plain_dir / "msgstore.db").is_file():
            print(f"Plaintext dependency DS-01-{variant} missing; generating it first...")
            generate_whatsapp_plain_dataset(
                output_dir=plain_dir,
                dataset_id="DS-01",
                variant=variant,
                seed=seed,
            )

        if dataset == "DS-02":
            manifest = generate_crypt14_dataset(
                plaintext_dir=plain_dir,
                output_dir=target_dir,
                dataset_id=dataset,
                variant=variant,
                seed=seed,
            )
            print(f"[OK] {dataset} ({variant}) successfully generated crypt14 fixture ({len(manifest.files)} files).")
        elif dataset == "DS-03":
            manifest = generate_crypt15_dataset(
                plaintext_dir=plain_dir,
                output_dir=target_dir,
                dataset_id=dataset,
                variant=variant,
                seed=seed,
            )
            print(f"[OK] {dataset} ({variant}) successfully generated crypt15 fixture ({len(manifest.files)} files).")
        elif dataset == "DS-04":
            manifest = generate_negative_dataset(
                plaintext_dir=plain_dir,
                output_dir=target_dir,
                dataset_id=dataset,
                variant=variant,
                seed=seed,
            )
            print(f"[OK] {dataset} ({variant}) successfully generated {len(manifest.files)} negative fixture files.")
    else:
        print(f"[FAIL] Unknown dataset ID: {dataset}. Currently supported: DS-01, DS-02, DS-03, DS-04")
        return 1

    # Self-verify immediately after build
    is_valid, errors = verify_dataset(target_dir)
    if not is_valid:
        print(f"[FAIL] Post-build verification failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"[OK] Post-build verification passed cleanly.")
    return 0



def verify_command(path: Path) -> int:
    """Verify an existing dataset directory."""
    path = Path(path)
    print(f"Verifying {path} ...")
    is_valid, errors = verify_dataset(path)
    if is_valid:
        print(f"[PASS] Dataset at {path} is valid.")
        return 0
    else:
        print(f"[FAIL] Dataset at {path} failed verification ({len(errors)} error(s)):")
        for err in errors:
            print(f"  - {err}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ArtifactX Ground-Truth Datasets CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Build sub-command
    build_parser = subparsers.add_parser("build", help="Build a ground-truth dataset")
    build_parser.add_argument("--dataset", required=True, choices=["DS-01", "DS-02", "DS-03", "DS-04"], help="Dataset ID (e.g. DS-01, DS-02)")
    build_parser.add_argument("--variant", required=True, choices=["dev", "holdout"], help="Variant: dev or holdout")
    build_parser.add_argument("--out", default="testdata", help="Output directory (default: testdata)")
    build_parser.add_argument("--seed", type=int, default=None, help="Explicit RNG seed (optional)")

    # Verify sub-command
    verify_parser = subparsers.add_parser("verify", help="Verify a dataset directory")
    verify_parser.add_argument("--path", required=True, help="Path to dataset directory (e.g. testdata/DS-01-dev)")

    args = parser.parse_args()

    if args.subcommand == "build":
        return build_command(args.dataset, args.variant, Path(args.out), args.seed)
    elif args.subcommand == "verify":
        return verify_command(Path(args.path))
    return 1


if __name__ == "__main__":
    sys.exit(main())
