"""
ArtifactX Forensic CLI Tool (spec 11_PIPELINE_AND_E2E.md §B13.3).

Standalone command-line interface for running the forensic analysis pipeline
without Neon database or FastAPI framework dependencies.

Syntax:
    python -m forensic.cli run --input <path>... [--key-file <path> | --key-hex <env_var_name>] [--config <path>] [--out <result.json>]

Adheres strictly to:
- master.md R4: Zero disk writes for evidence or derived artifacts.
- master.md R5: Keys are radioactive. Keys accepted via env var name or file path, never argv string.
- master.md R7: Honest failure isolation and typed error states.
- master.md R11: Total determinism; wall-clock excluded from content hash.
- master.md R18: Standard library + pure forensic core only; no DB/network.
- DEC-011 / spec B13.3: Result JSON file writing is confined strictly to write_cli_output().
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence
import yaml

from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput, PipelineConfig, PipelineResult


def write_cli_output(out_path: Path, content: str) -> None:
    """
    Confined output writer for CLI analysis result export (DEC-011, spec B13.3).
    The written file contains ONLY analysis results/findings, NEVER evidence or derived evidence.
    """
    # guard:allow-disk-write: CLI output file export per DEC-011 and B13.3 (analysis result only, never evidence)
    out_path.write_text(content, encoding="utf-8")


def format_summary_table(res: PipelineResult) -> str:
    """Format a clean, structured forensic summary report table."""
    lines = [
        "=" * 70,
        " ArtifactX Forensic Analysis Pipeline — Execution Summary",
        "=" * 70,
        f" Pipeline Run ID:  {res.run_id}",
        f" Status:           {res.status}",
        f" Content Hash:     {res.content_hash}",
        f" Total Duration:   {res.duration_ms:.2f} ms",
        f" Exhibits Count:   {res.summary.get('total_inputs', 0)}",
        "-" * 70,
        " STAGE EXECUTION RESULTS:",
    ]

    for s in res.stages:
        ev_str = f" [ev: {s.evidence_id}]" if s.evidence_id else ""
        err_str = f" ({s.error_code})" if s.error_code else ""
        lines.append(f"   {s.stage:<12} | {s.status:<14} | {s.duration_ms:8.2f} ms{ev_str}{err_str}")

    counts = res.summary.get("counts", {})
    lines.extend([
        "-" * 70,
        " FINDINGS & ARTIFACT METRICS:",
        f"   WhatsApp Messages:      {counts.get('whatsapp_messages', 0)}",
        f"   Telegram Messages:      {counts.get('telegram_messages', 0)}",
        f"   Recovered Findings:     {counts.get('recovered_findings', 0)}",
        f"   Timeline Events:        {counts.get('timeline_events', 0)}",
        f"   Correlation Findings:   {counts.get('correlation_findings', 0)}",
        "=" * 70,
    ])
    return "\n".join(lines)


def run_cli(args: Sequence[str]) -> int:
    """CLI entrypoint evaluating parsed arguments."""
    parser = argparse.ArgumentParser(
        prog="python -m forensic.cli",
        description="ArtifactX Forensic Analysis Pipeline CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    run_parser = subparsers.add_parser("run", help="Run forensic pipeline on exhibit files")
    run_parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more evidence exhibit file paths (read-only)",
    )
    run_parser.add_argument(
        "--key-file",
        type=str,
        default=None,
        help="Path to binary key file (e.g. WhatsApp crypt14/crypt15 key)",
    )
    run_parser.add_argument(
        "--key-hex",
        type=str,
        default=None,
        help="Name of environment variable containing 64-char key hex string (master.md R5)",
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Optional path to pipeline YAML configuration file",
    )
    run_parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write full JSON results output",
    )
    run_parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output raw JSON to stdout instead of human-readable summary table",
    )

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parsed = parser.parse_args(args)
    if not parsed.command:
        parser.print_help()
        return 1

    if parsed.command == "run":
        # 1. Validate and load inputs read-only
        evidence_inputs: List[EvidenceInput] = []
        for idx, input_str in enumerate(parsed.input):
            input_path = Path(input_str)
            if not input_path.is_file():
                sys.stderr.write(f"Error: Evidence file not found: {input_str}\n")
                return 1

            raw_bytes = input_path.read_bytes()
            fn = input_path.name
            role = "primary"
            fn_lower = fn.lower()
            if fn_lower.endswith("-wal"):
                role = "wal"
            elif fn_lower.endswith("-shm"):
                role = "shm"
            elif "wa.db" in fn_lower or "contacts.db" in fn_lower:
                role = "wa_contacts"
            elif fn_lower.endswith(".zip"):
                role = "media_zip"

            evidence_inputs.append(
                EvidenceInput(
                    evidence_id=str(idx + 1),
                    sha256=sha256_hex(raw_bytes),
                    name=fn,
                    data=raw_bytes,
                    role=role,
                )
            )

        # 2. Extract key material with R5 protection
        key_materials: List[KeyMaterial] = []
        if parsed.key_file:
            kf_path = Path(parsed.key_file)
            if not kf_path.is_file():
                sys.stderr.write(f"Error: Key file not found: {parsed.key_file}\n")
                return 1
            key_bytes = kf_path.read_bytes()
            k_type = "crypt14" if len(key_bytes) == 158 else "crypt15"
            key_materials.append(
                KeyMaterial(
                    key_file_bytes=key_bytes,
                    key_type=k_type,
                )
            )

        if parsed.key_hex:
            # Rule R5: key_hex is the NAME of the environment variable, not the secret itself
            env_var_name = parsed.key_hex.strip()
            if len(env_var_name) == 64 and all(c in "0123456789abcdefABCDEF" for c in env_var_name) and env_var_name not in os.environ:
                sys.stderr.write(
                    "Error (master.md R5): --key-hex accepts the NAME of an environment variable, "
                    "not raw secret hex directly on the command line (prevents shell history leakage).\n"
                )
                return 1

            secret_hex = os.environ.get(env_var_name)
            if not secret_hex:
                sys.stderr.write(f"Error: Environment variable '{env_var_name}' not set or empty.\n")
                return 1

            key_materials.append(
                KeyMaterial(
                    key_hex=secret_hex.strip(),
                    key_type="crypt15",
                )
            )

        # 3. Load optional config YAML
        config = PipelineConfig()
        if parsed.config:
            cfg_path = Path(parsed.config)
            if not cfg_path.is_file():
                sys.stderr.write(f"Error: Config file not found: {parsed.config}\n")
                return 1
            try:
                raw_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                config = PipelineConfig(
                    thresholds_version=raw_cfg.get("thresholds_version", "1.0.0"),
                    correlation_params=raw_cfg.get("correlation_params", {}),
                    custom_keywords=tuple(raw_cfg.get("custom_keywords", ())),
                )
            except Exception as e:
                sys.stderr.write(f"Error parsing YAML config: {e}\n")
                return 1

        # 4. Execute pure forensic pipeline
        result = run_pipeline(
            inputs=evidence_inputs,
            keys=key_materials,
            cfg=config,
        )

        # 5. Output presentation
        json_output = json.dumps(result.to_dict(include_data=True), indent=2, ensure_ascii=False)

        if parsed.out:
            out_file = Path(parsed.out)
            write_cli_output(out_file, json_output)

        if parsed.json_only:
            if not parsed.out:
                print(json_output)
        else:
            print(format_summary_table(result))
            if parsed.out:
                print(f"\n[Result JSON saved to: {parsed.out}]")

        return 0 if result.status in ("COMPLETED", "PARTIAL") else 1

    return 0


def main() -> None:
    """Main CLI entrypoint."""
    sys.exit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
