"""Unit tests for cross-app, control, and tamper datasets (B4).

Follows master.md R1, R6, R11, R13, R20 and 02_GROUND_TRUTH_DATASETS.md §5:
- Validates acceptance.yaml targets using yaml.safe_load.
- Tests crypto validators (BTC Base58Check, EVM EIP-55, IBAN Mod-97).
- Tests URL normalization, perceptual dHash similarity, and GPS rendezvous.
- Validates DS-06 cross-app planted shared entities and decoys.
- Validates DS-07 control dataset (0 shared entities).
- Validates DS-08 tamper dataset (100% single-byte mutation detection).
- Tests tamper detection in verify_dataset.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from tools.groundtruth.crossapp import (
    compute_image_dhash,
    dhash_hamming_distance,
    generate_control_dataset,
    generate_crossapp_dataset,
    generate_tamper_dataset,
    haversine_distance_m,
    normalize_url,
)
from tools.groundtruth.crypto.bitcoin_address import (
    base58check_validate,
    generate_btc_decoy_address,
    generate_deterministic_btc_address,
)
from tools.groundtruth.crypto.evm_address import (
    generate_deterministic_evm_address,
    generate_evm_decoy_address,
    validate_evm_address,
)
from tools.groundtruth.crypto.iban import (
    generate_deterministic_iban,
    generate_iban_decoy,
    validate_iban,
)
from tools.groundtruth.manifest import DatasetManifest
from tools.groundtruth.rng import DeterministicRNG
from tools.groundtruth.verify_dataset import verify_dataset


def test_acceptance_yaml_loads_and_has_required_sections():
    """Verify acceptance.yaml loads with yaml.safe_load and contains all required targets."""
    yaml_path = Path("acceptance.yaml")
    assert yaml_path.is_file(), "acceptance.yaml must exist at repository root"

    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    required_sections = ["integrity", "decryption", "parsing", "recovery", "correlation", "reproducibility", "traceability"]
    for sec in required_sections:
        assert sec in config, f"Missing section '{sec}' in acceptance.yaml"

    # Verify key empirical thresholds
    assert config["integrity"]["tamper_detection_rate"] == 1.0
    assert config["decryption"]["decrypt_parity"] == 1.0
    assert config["parsing"]["parse_accuracy_min"] >= 0.99
    assert config["correlation"]["planted_links_recall_min"] == 1.0
    assert config["correlation"]["decoys_linked_max"] == 0.0
    assert config["correlation"]["control_fpr_max"] == 0.0
    assert config["recovery"]["id_gap_confidence_max"] <= 0.30


def test_crypto_validators_and_decoys():
    """Verify BTC, EVM, and IBAN deterministic generation, validation, and decoy rejection."""
    rng = DeterministicRNG(445566)

    # 1. Bitcoin Base58Check
    btc_valid = generate_deterministic_btc_address(rng)
    is_val, norm = base58check_validate(btc_valid)
    assert is_val, f"BTC address invalid: {btc_valid}"
    assert norm == btc_valid

    btc_decoy = generate_btc_decoy_address(btc_valid)
    is_decoy_val, rsn = base58check_validate(btc_decoy)
    assert not is_decoy_val, f"BTC decoy unexpectedly valid: {btc_decoy}"

    # 2. Ethereum EIP-55
    evm_valid = generate_deterministic_evm_address(rng)
    is_val, norm = validate_evm_address(evm_valid)
    assert is_val, f"EVM address invalid: {evm_valid}"

    evm_decoy = generate_evm_decoy_address(evm_valid)
    is_decoy_val, rsn = validate_evm_address(evm_decoy)
    assert not is_decoy_val, f"EVM decoy unexpectedly valid: {evm_decoy}"

    # 3. ISO 7064 Mod-97 IBAN
    iban_valid = generate_deterministic_iban(rng, country_code="DE")
    is_val, norm = validate_iban(iban_valid)
    assert is_val, f"IBAN invalid: {iban_valid}"

    iban_decoy = generate_iban_decoy(iban_valid)
    is_decoy_val, rsn = validate_iban(iban_decoy)
    assert not is_decoy_val, f"IBAN decoy unexpectedly valid: {iban_decoy}"


def test_url_normalization_contract():
    """Verify URL normalization strips tracking params, www., and default ports while keeping path."""
    raw1 = "https://www.example.test:443/case-files/archive-2026?utm_source=wa&utm_medium=chat"
    raw2 = "https://example.test/case-files/archive-2026?utm_campaign=audit&fbclid=XYZ123"
    assert normalize_url(raw1) == "https://example.test/case-files/archive-2026"
    assert normalize_url(raw2) == "https://example.test/case-files/archive-2026"
    assert normalize_url(raw1) == normalize_url(raw2)

    # Different paths must NOT normalize to same URL (decoy test)
    path_decoy = "https://example.test/case-files/other-path"
    assert normalize_url(raw1) != normalize_url(path_decoy)


def test_haversine_and_gps_rendezvous():
    """Verify Haversine calculation and rendezvous boundary threshold."""
    # Gateway of India reference
    lat1, lon1 = 18.921984, 72.834654
    # ~115 meters away
    lat2, lon2 = 18.922850, 72.835250
    dist = haversine_distance_m(lat1, lon1, lat2, lon2)
    assert 100.0 <= dist <= 130.0, f"Expected ~115m, got {dist}"

    # Distance exceeded decoy (~391m away)
    lat_far, lon_far = 18.925500, 72.834654
    dist_far = haversine_distance_m(lat1, lon1, lat_far, lon_far)
    assert dist_far > 250.0, f"Expected > 250m, got {dist_far}"


def test_ds06_manifest_and_planted_entities():
    """Verify DS-06-dev dataset has all 7 planted shared entities and 9 decoys."""
    ds06_path = Path("testdata/DS-06-dev")
    assert ds06_path.is_dir(), "DS-06-dev directory missing"

    manifest = DatasetManifest.load(ds06_path / "manifest.json")
    assert manifest.dataset_id == "DS-06"
    assert manifest.variant == "dev"

    shared_types = {se["type"] for se in manifest.shared_entities}
    expected_types = {"phone", "btc_address", "evm_address", "iban", "url", "image_near_duplicate", "gps_rendezvous"}
    assert expected_types <= shared_types

    # Every shared entity must have occurrences in both whatsapp and telegram
    for se in manifest.shared_entities:
        assert se["expected_link"] is True
        apps = {o["app"] for o in se["occurrences"]}
        assert {"whatsapp", "telegram"} <= apps

    # Verify decoys
    assert len(manifest.decoys) >= 7
    for dec in manifest.decoys:
        assert dec["expected_link"] is False
        assert "decoy_reason" in dec


def test_ds07_control_dataset_properties():
    """Verify DS-07 control dataset has 0 shared entities and passes verification."""
    ds07_path = Path("testdata/DS-07-dev")
    assert ds07_path.is_dir(), "DS-07-dev directory missing"

    manifest = DatasetManifest.load(ds07_path / "manifest.json")
    assert manifest.dataset_id == "DS-07"
    assert len(manifest.shared_entities) == 0
    assert len(manifest.decoys) == 0

    valid, errors = verify_dataset(ds07_path)
    assert valid, f"DS-07 verification failed: {errors}"


def test_ds08_tamper_dataset_properties():
    """Verify DS-08 tamper dataset has recorded single-byte mutations and valid records."""
    ds08_path = Path("testdata/DS-08-dev")
    assert ds08_path.is_dir(), "DS-08-dev directory missing"

    manifest = DatasetManifest.load(ds08_path / "manifest.json")
    assert manifest.dataset_id == "DS-08"
    assert manifest.tamper_records is not None
    assert len(manifest.tamper_records) >= 20

    base_file = ds08_path / "reference_base.db"
    assert base_file.is_file()
    base_bytes = base_file.read_bytes()

    for tr in manifest.tamper_records:
        fix_path = ds08_path / tr["fixture_path"]
        assert fix_path.is_file()
        mut_bytes = fix_path.read_bytes()

        assert len(mut_bytes) == len(base_bytes)
        offset = tr["flip_offset"]
        assert base_bytes[offset] == tr["original_byte"]
        assert mut_bytes[offset] == tr["flipped_byte"]
        assert hashlib.sha256(mut_bytes).hexdigest() == tr["tampered_sha256"]

    valid, errors = verify_dataset(ds08_path)
    assert valid, f"DS-08 verification failed: {errors}"


def test_dev_and_holdout_variants_have_different_seeds_and_entities():
    """Verify dev and holdout variants have different seeds and distinct hashes (R11, DEC-013)."""
    for ds_id in ("DS-06", "DS-07", "DS-08"):
        dev_m = DatasetManifest.load(Path(f"testdata/{ds_id}-dev/manifest.json"))
        holdout_m = DatasetManifest.load(Path(f"testdata/{ds_id}-holdout/manifest.json"))

        assert dev_m.seed != holdout_m.seed, f"{ds_id} dev and holdout seeds must differ"
        assert dev_m.variant == "dev"
        assert holdout_m.variant == "holdout"

        dev_files = {f.path: f.sha256 for f in dev_m.files}
        holdout_files = {f.path: f.sha256 for f in holdout_m.files}

        # Primary database hashes must differ
        common_paths = set(dev_files.keys()) & set(holdout_files.keys())
        for cp in common_paths:
            if cp in ("msgstore.db", "cache4.db", "reference_base.db"):
                assert dev_files[cp] != holdout_files[cp], f"Hash collision between dev and holdout on {cp}"


def test_verify_dataset_tamper_detection(tmp_path: Path):
    """Verify that verify_dataset detects tampering when a single byte is flipped."""
    src_dir = Path("testdata/DS-06-dev")
    target_dir = tmp_path / "DS-06-tampered"
    shutil.copytree(src_dir, target_dir)

    # 1. Untampered copy passes
    valid, errors = verify_dataset(target_dir)
    assert valid, f"Untampered copy unexpectedly failed: {errors}"

    # 2. Mutate one byte in msgstore.db
    target_db = target_dir / "msgstore.db"
    raw = bytearray(target_db.read_bytes())
    raw[100] ^= 0x55
    target_db.write_bytes(bytes(raw))

    # Must fail verification with SHA-256 mismatch
    valid_tampered, errors_tampered = verify_dataset(target_dir)
    assert not valid_tampered, "verify_dataset failed to detect byte mutation in msgstore.db"
    assert any("SHA-256 mismatch for msgstore.db" in e for e in errors_tampered)


def test_crossapp_generator_determinism(tmp_path: Path):
    """Verify cross-app generator determinism: same seed produces identical files and hashes (R11)."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    m1 = generate_crossapp_dataset(output_dir=dir1, dataset_id="DS-06", variant="dev", seed=778899)
    m2 = generate_crossapp_dataset(output_dir=dir2, dataset_id="DS-06", variant="dev", seed=778899)

    files1 = {f.path: f.sha256 for f in m1.files}
    files2 = {f.path: f.sha256 for f in m2.files}
    assert files1 == files2, "Non-deterministic output detected across identical seeds"
