"""
Integration tests for forensic recovery accuracy against ground-truth datasets (B10.6, B10.7, spec 08_DELETED_DATA_RECOVERY.md).

Tests:
1. DS-01-dev (WhatsApp): 100% manifest recovery across Tiers 1-4, controls verified empty.
2. DS-01-holdout (WhatsApp): 100% manifest recovery across Tiers 1-4, controls verified empty.
3. DS-05-dev (Telegram): 100% manifest recovery across Tiers 2-4, controls verified empty.
4. DS-05-holdout (Telegram): 100% manifest recovery across Tiers 2-4, controls verified empty.
5. Precision, recall, and F1 == 1.0 on recoverable deletions.
6. Negative controls (vacuumed_control, secure_delete_control) never recovered.
7. Tier 4 confidence score <= 0.30 and weak_hint.
"""

import json
from pathlib import Path
import pytest

from forensic.recovery.evaluation import evaluate_recovery
from forensic.recovery.orchestrator import RecoveryPipeline


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_dataset_recovery(dataset_name: str, app_hint: str, db_relpath: str, wal_relpath: str | None = None):
    ds_dir = REPO_ROOT / "testdata" / dataset_name
    manifest_path = ds_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    db_path = ds_dir / db_relpath
    with open(db_path, "rb") as f:
        db_bytes = f.read()

    wal_bytes = None
    if wal_relpath:
        wal_path = ds_dir / wal_relpath
        if wal_path.exists():
            with open(wal_path, "rb") as f:
                wal_bytes = f.read()

    pipeline = RecoveryPipeline(
        db_bytes=db_bytes,
        wal_bytes=wal_bytes,
        app_hint=app_hint,
        evidence_id=f"ev_{dataset_name}",
        evidence_sha256="test_sha",
    )
    res = pipeline.run()

    eval_result = evaluate_recovery(findings=res.findings, manifest=manifest)
    return res, eval_result, manifest


@pytest.mark.integration
def test_ds01_dev_recovery_accuracy():
    """Verify 100% recovery accuracy on DS-01-dev (WhatsApp)."""
    res, eval_res, manifest = _run_dataset_recovery(
        dataset_name="DS-01-dev",
        app_hint="whatsapp",
        db_relpath="msgstore.db",
        wal_relpath="msgstore.db-wal",
    )

    # 1. Controls must be empty
    assert eval_res["controls_verified"] is True
    assert len(eval_res["control_violations"]) == 0

    # 2. Perfect precision and recall on manifest deletions
    assert eval_res["overall"]["precision"] == 1.0
    assert eval_res["overall"]["recall"] == 1.0
    assert eval_res["overall"]["f1"] == 1.0

    # 3. Check every manifest deletion case
    for case_id, case_info in eval_res["cases"].items():
        assert case_info["status"] == "PASS", f"Case {case_id} failed: {case_info.get('error')}"

    # 4. Check Tier 4 confidence score cap
    tier4_findings = [f for f in res.findings if f.tier == 4]
    for f in tier4_findings:
        assert f.confidence_score <= 0.30
        assert f.strength == "weak_hint"

    # 5. Check DUPLICATE_OF_LIVE records exist and are retained
    dup_live = [f for f in res.findings if f.validation_status == "DUPLICATE_OF_LIVE"]
    assert len(dup_live) > 0


@pytest.mark.integration
def test_ds01_holdout_recovery_accuracy():
    """Verify 100% recovery accuracy on DS-01-holdout (WhatsApp)."""
    res, eval_res, manifest = _run_dataset_recovery(
        dataset_name="DS-01-holdout",
        app_hint="whatsapp",
        db_relpath="msgstore.db",
        wal_relpath="msgstore.db-wal",
    )

    assert eval_res["controls_verified"] is True
    assert len(eval_res["control_violations"]) == 0
    assert eval_res["overall"]["precision"] == 1.0
    assert eval_res["overall"]["recall"] == 1.0
    assert eval_res["overall"]["f1"] == 1.0


@pytest.mark.integration
def test_ds05_dev_recovery_accuracy():
    """Verify 100% recovery accuracy on DS-05-dev (Telegram)."""
    res, eval_res, manifest = _run_dataset_recovery(
        dataset_name="DS-05-dev",
        app_hint="telegram",
        db_relpath="cache4.db",
        wal_relpath="cache4.db-wal",
    )

    assert eval_res["controls_verified"] is True
    assert len(eval_res["control_violations"]) == 0
    assert eval_res["overall"]["precision"] == 1.0
    assert eval_res["overall"]["recall"] == 1.0
    assert eval_res["overall"]["f1"] == 1.0

    for case_id, case_info in eval_res["cases"].items():
        assert case_info["status"] == "PASS", f"Case {case_id} failed: {case_info.get('error')}"

    tier4_findings = [f for f in res.findings if f.tier == 4]
    for f in tier4_findings:
        assert f.confidence_score <= 0.30
        assert f.strength == "weak_hint"


@pytest.mark.integration
def test_ds05_holdout_recovery_accuracy():
    """Verify 100% recovery accuracy on DS-05-holdout (Telegram)."""
    res, eval_res, manifest = _run_dataset_recovery(
        dataset_name="DS-05-holdout",
        app_hint="telegram",
        db_relpath="cache4.db",
        wal_relpath="cache4.db-wal",
    )

    assert eval_res["controls_verified"] is True
    assert len(eval_res["control_violations"]) == 0
    assert eval_res["overall"]["precision"] == 1.0
    assert eval_res["overall"]["recall"] == 1.0
    assert eval_res["overall"]["f1"] == 1.0
