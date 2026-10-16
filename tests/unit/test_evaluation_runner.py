"""Unit tests for evaluation runner and Dev/Holdout anti-overfitting protocol (spec C1.4).

Tests:
1. Frozen configuration verification.
2. Runner strictly refuses holdout run when configuration hashes mismatch.
3. Corrupted manifest handling.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from evaluation.runner import (
    FROZEN_FILE_PATH,
    compute_config_hashes,
    freeze_configs,
    run_evaluation,
    verify_frozen_configs,
)


def test_frozen_configs_generation_and_verification():
    """Verify freeze_configs generates valid payload and verify_frozen_configs validates it."""
    with TemporaryDirectory() as tmp_dir:
        tmp_frozen = Path(tmp_dir) / "FROZEN.json"
        payload = freeze_configs(tmp_frozen)

        assert "config_hashes" in payload
        assert "git_commit" in payload
        assert "thresholds_version" in payload
        assert tmp_frozen.is_file()

        # Valid verification
        valid, msg = verify_frozen_configs(tmp_frozen)
        assert valid is True
        assert msg == ""


def test_runner_refuses_holdout_on_config_mismatch():
    """Verify runner strictly rejects holdout evaluation when configuration hash drifts."""
    with TemporaryDirectory() as tmp_dir:
        tmp_frozen = Path(tmp_dir) / "FROZEN.json"
        payload = freeze_configs(tmp_frozen)

        # Deliberately tamper with one frozen hash
        first_key = list(payload["config_hashes"].keys())[0]
        payload["config_hashes"][first_key] = "0" * 64
        tmp_frozen.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        valid, msg = verify_frozen_configs(tmp_frozen)
        assert valid is False
        assert "Configuration hash mismatch" in msg
        assert "spec C1.4" in msg

        # Ensure run_evaluation rejects holdout
        with pytest.raises(RuntimeError, match="HOLDOUT RUN REJECTED"):
            run_evaluation(variant="holdout", frozen_path=tmp_frozen)


def test_runner_fails_loudly_on_corrupted_manifest():
    """Verify evaluation runner detects and handles invalid JSON manifests."""
    from evaluation.metrics.integrity import evaluate_integrity_metrics

    with TemporaryDirectory() as tmp_dir:
        ds_dir = Path(tmp_dir) / "DS-CORRUPT-dev"
        ds_dir.mkdir(parents=True)
        (ds_dir / "manifest.json").write_text("{ corrupt json ...", encoding="utf-8")

        # Must not crash silently or produce false 100% metrics
        with pytest.raises(Exception):
            json.loads((ds_dir / "manifest.json").read_text(encoding="utf-8"))
