"""
Unit and functional tests for ArtifactX Forensic CLI (spec 11_PIPELINE_AND_E2E.md §B13.3).

Verifies:
- python -m forensic.cli run --input ... works without database or network
- Output formatting and summary table presentation
- Writing result JSON to --out (DEC-011)
- --key-file support
- --key-hex environment variable resolution
- R5 rejection of direct secret hex on command line
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

from forensic.cli import run_cli


def test_cli_run_wa_summary_table(capsys):
    """Assert CLI runs over WhatsApp exhibits and prints summary table to stdout."""
    msgstore_p = "testdata/DS-01-dev/msgstore.db"
    wa_db_p = "testdata/DS-01-dev/wa.db"

    exit_code = run_cli(["run", "--input", msgstore_p, wa_db_p])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "ArtifactX Forensic Analysis Pipeline — Execution Summary" in captured.out
    assert "WhatsApp Messages:" in captured.out
    assert "Timeline Events:" in captured.out


def test_cli_run_out_file(tmp_path):
    """Assert CLI writes valid analysis result JSON to --out path (DEC-011)."""
    msgstore_p = "testdata/DS-01-dev/msgstore.db"
    out_file = tmp_path / "result.json"

    exit_code = run_cli(["run", "--input", msgstore_p, "--out", str(out_file)])
    assert exit_code == 0
    assert out_file.is_file()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["status"] == "COMPLETED"
    assert len(data["content_hash"]) == 64
    assert len(data["stages"]) > 0


def test_cli_run_with_key_file(tmp_path):
    """Assert CLI successfully decrypts and parses Crypt14 container with --key-file."""
    crypt14_p = "testdata/DS-02-dev/msgstore.db.crypt14"
    key_p = "testdata/DS-02-dev/keys/key"
    out_file = tmp_path / "crypt14_result.json"

    exit_code = run_cli([
        "run",
        "--input", crypt14_p,
        "--key-file", key_p,
        "--out", str(out_file),
    ])
    assert exit_code == 0

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["status"] == "COMPLETED"
    assert data["summary"]["counts"]["whatsapp_messages"] > 0


def test_cli_run_with_key_hex_env(monkeypatch, tmp_path):
    """Assert CLI resolves key from environment variable name (R5)."""
    crypt15_p = "testdata/DS-03-dev/msgstore.db.crypt15"
    key_hex_val = Path("testdata/DS-03-dev/keys/root_key.hex").read_text().strip()

    env_var_name = "TEST_WA_ROOT_KEY_HEX"
    monkeypatch.setenv(env_var_name, key_hex_val)

    out_file = tmp_path / "crypt15_result.json"
    exit_code = run_cli([
        "run",
        "--input", crypt15_p,
        "--key-hex", env_var_name,
        "--out", str(out_file),
    ])
    assert exit_code == 0

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["status"] == "COMPLETED"
    assert data["summary"]["counts"]["whatsapp_messages"] > 0


def test_cli_rejects_raw_hex_on_argv(capsys):
    """Assert CLI rejects raw 64-char hex on command line to prevent shell history leak (R5)."""
    raw_hex = "f" * 64
    exit_code = run_cli([
        "run",
        "--input", "testdata/DS-01-dev/msgstore.db",
        "--key-hex", raw_hex,
    ])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "master.md R5" in captured.err
    assert "prevents shell history leakage" in captured.err


def test_cli_missing_input_file(capsys):
    """Assert CLI fails cleanly when input file does not exist."""
    exit_code = run_cli(["run", "--input", "non_existent_file.db"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_subprocess_invocation():
    """Assert CLI runs via 'python -m forensic.cli' in a clean external subprocess."""
    cmd = [
        sys.executable,
        "-m", "forensic.cli",
        "run",
        "--input", "testdata/DS-01-dev/msgstore.db",
        "--json-only",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(".").resolve())
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "COMPLETED"
    assert data["content_hash"] is not None
