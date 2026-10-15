"""Unit tests for ground-truth dataset generator and verification.

Follows master.md R1, R6, R11, R13, and 02_GROUND_TRUTH_DATASETS.md §6.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from forensic.whatsapp import is_whatsapp_database
from tools.groundtruth.rng import DeterministicRNG
from tools.groundtruth.verify_dataset import verify_dataset
from tools.groundtruth.wa.generator import generate_whatsapp_plain_dataset


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory within allowed test paths."""
    out = tmp_path / "gt_test_output"
    out.mkdir()
    return out


def test_groundtruth_determinism(tmp_path):
    """Assert generator is 100% deterministic: same seed yields byte-identical file hashes (R11)."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    manifest1 = generate_whatsapp_plain_dataset(dir1, dataset_id="DS-01", variant="dev", seed=12345)
    manifest2 = generate_whatsapp_plain_dataset(dir2, dataset_id="DS-01", variant="dev", seed=12345)

    # Check that file list and hashes are identical
    files1 = {f.path: f.sha256 for f in manifest1.files}
    files2 = {f.path: f.sha256 for f in manifest2.files}
    assert files1 == files2, "Determinism failed: file hashes differ between identical seed runs"

    # Check manifest JSON determinism
    assert manifest1.to_json() == manifest2.to_json(), "Determinism failed: manifest JSON differs"


def test_groundtruth_variant_difference(tmp_path):
    """Assert dev and holdout variants with different seeds produce distinct datasets."""
    dir_dev = tmp_path / "dev"
    dir_holdout = tmp_path / "holdout"

    manifest_dev = generate_whatsapp_plain_dataset(dir_dev, dataset_id="DS-01", variant="dev", seed=20261014)
    manifest_holdout = generate_whatsapp_plain_dataset(dir_holdout, dataset_id="DS-01", variant="holdout", seed=987654321)

    assert manifest_dev.seed != manifest_holdout.seed
    db_hash_dev = next(f.sha256 for f in manifest_dev.files if f.path == "msgstore.db")
    db_hash_holdout = next(f.sha256 for f in manifest_holdout.files if f.path == "msgstore.db")
    assert db_hash_dev != db_hash_holdout, "Dev and holdout msgstore.db hashes must not match"


def test_fictitious_pii_compliance(tmp_path):
    """Assert all generated phone numbers and domains use reserved fictitious ranges (R6)."""
    target_dir = tmp_path / "pii_check"
    manifest = generate_whatsapp_plain_dataset(target_dir, dataset_id="DS-01", variant="dev", seed=42)

    # Check contacts
    for contact in manifest.whatsapp["contacts"]:
        phone = contact["phone_number"]
        # Must be in fake range +91 98765 4xxxx
        assert phone.startswith("+91987654"), f"Non-fictitious phone found: {phone}"

    # Check messages
    for msg in manifest.whatsapp["messages"]:
        body = msg.get("body") or ""
        if "http" in body:
            # URLs must use .test or reserved domains
            assert "example.test" in body or ".example" in body, f"Non-reserved domain found: {body}"


def test_manifest_schema_structure(tmp_path):
    """Assert manifest JSON structure matches schema requirements."""
    target_dir = tmp_path / "schema_check"
    manifest = generate_whatsapp_plain_dataset(target_dir, dataset_id="DS-01", variant="dev", seed=42)

    raw_manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    assert raw_manifest["dataset_id"] == "DS-01"
    assert raw_manifest["origin"] == "synthetic"
    assert "files" in raw_manifest
    assert "whatsapp" in raw_manifest
    assert "modelled_vs_observed" in raw_manifest

    # Check deletions metadata
    deletions = raw_manifest["whatsapp"]["deletions"]
    assert len(deletions) >= 5
    methods = {d["method"] for d in deletions}
    assert "freelist_deleted" in methods
    assert "slack_deleted" in methods
    assert "wal_resident" in methods
    assert "vacuumed_control" in methods
    assert "secure_delete_control" in methods


def test_verify_dataset_tamper_detection(tmp_path):
    """Assert verify_dataset fails when a single byte in msgstore.db is tampered with (R1)."""
    source_dir = tmp_path / "clean_ds"
    generate_whatsapp_plain_dataset(source_dir, dataset_id="DS-01", variant="dev", seed=777)

    # Initial verification passes
    is_valid, errors = verify_dataset(source_dir)
    assert is_valid is True
    assert len(errors) == 0

    # Tamper with 1 byte in msgstore.db
    db_file = source_dir / "msgstore.db"
    content = bytearray(db_file.read_bytes())
    content[150] ^= 0xFF  # Flip byte
    db_file.write_bytes(content)

    # Tampered verification fails
    is_valid_tampered, errors_tampered = verify_dataset(source_dir)
    assert is_valid_tampered is False
    assert any("SHA-256 mismatch for msgstore.db" in e for e in errors_tampered)


def test_is_whatsapp_database_detector_compatibility(tmp_path):
    """Assert the generated msgstore.db is recognized by forensic.whatsapp.detector."""
    ds_dir = tmp_path / "detector_check"
    generate_whatsapp_plain_dataset(ds_dir, dataset_id="DS-01", variant="dev", seed=888)

    db_path = ds_dir / "msgstore.db"
    assert is_whatsapp_database(db_path) is True


def test_self_verification_catches_missing_recoverable_marker(tmp_path, monkeypatch):
    """Assert generator self-verification fails if a claimed recoverable marker is absent (B1.5)."""
    import tools.groundtruth.wa.generator as gen_mod

    orig_find = gen_mod._find_byte_offsets

    def fake_find(data, pattern):
        if b"FREELIST_DELETED" in pattern:
            return []  # Simulate marker not found
        return orig_find(data, pattern)

    monkeypatch.setattr(gen_mod, "_find_byte_offsets", fake_find)

    target_dir = tmp_path / "fail_marker"
    with pytest.raises(RuntimeError, match="Freelists marker .* not found"):
        generate_whatsapp_plain_dataset(target_dir, dataset_id="DS-01", variant="dev", seed=999)


def test_self_verification_catches_control_leak(tmp_path, monkeypatch):
    """Assert generator self-verification fails if a control marker leaks into raw bytes (B1.5)."""
    import tools.groundtruth.wa.generator as gen_mod

    orig_find = gen_mod._find_byte_offsets

    def fake_find(data, pattern):
        if b"VACUUM_CTRL" in pattern:
            return [1024]  # Simulate control marker leaked into bytes
        return orig_find(data, pattern)

    monkeypatch.setattr(gen_mod, "_find_byte_offsets", fake_find)

    target_dir = tmp_path / "fail_ctrl"
    with pytest.raises(RuntimeError, match="Vacuumed control marker .* found in raw bytes"):
        generate_whatsapp_plain_dataset(target_dir, dataset_id="DS-01", variant="dev", seed=999)

