"""Unit tests for WhatsApp encrypted and negative fixture generator (B2).

Follows master.md R1, R5, R6, R7, R11, R14, R15, R20 and spec 02_GROUND_TRUTH_DATASETS.md §6:
- Generator determinism (R11)
- Reference round-trip decryption equality (B2.3)
- Key material isolated to keys/ with fictitious disclaimer (R5, R14)
- Negative fixtures set with expected typed error outcomes (B2.4)
- Tamper detection on encrypted fixtures
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.groundtruth.crypto.wa_encrypt import (
    generate_crypt14_dataset,
    generate_crypt15_dataset,
    generate_negative_dataset,
)
from tools.groundtruth.verify_dataset import verify_dataset


@pytest.fixture
def dummy_plaintext_dir(tmp_path: Path) -> Path:
    """Create a minimal valid plaintext SQLite database directory."""
    plain_dir = tmp_path / "plain_source"
    plain_dir.mkdir()
    db_path = plain_dir / "msgstore.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA user_version = 1")
    conn.execute("CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT NOT NULL, server TEXT NOT NULL)")
    conn.execute("CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER NOT NULL)")
    conn.execute("CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER NOT NULL, text_data TEXT)")
    conn.execute("INSERT INTO jid VALUES (1, '919876540001', 's.whatsapp.net')")
    conn.execute("INSERT INTO chat VALUES (1, 1)")
    conn.execute("INSERT INTO message VALUES (1, 1, 'Encrypted round-trip test message')")
    conn.commit()
    conn.close()

    return plain_dir


def test_crypt14_generation_and_roundtrip(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert DS-02 crypt14 fixture generates cleanly and passes reference decrypt round-trip (B2.2, B2.3)."""
    out_dir = tmp_path / "DS-02-test"
    manifest = generate_crypt14_dataset(
        plaintext_dir=dummy_plaintext_dir,
        output_dir=out_dir,
        dataset_id="DS-02",
        variant="dev",
        seed=101,
    )

    assert (out_dir / "msgstore.db.crypt14").is_file()
    assert (out_dir / "keys" / "key").is_file()
    assert (out_dir / "keys" / "README.md").is_file()

    # Check manifest fields
    assert manifest.dataset_id == "DS-02"
    assert manifest.encryption["format"] == "crypt14"
    assert manifest.encryption["roundtrip_verified"] is True
    assert "key_fingerprint" in manifest.encryption
    assert manifest.encryption["cipher"] == "AES-256-GCM"

    # Dataset verification must pass cleanly
    is_valid, errors = verify_dataset(out_dir)
    assert is_valid, f"verify_dataset failed: {errors}"


def test_crypt15_generation_and_roundtrip(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert DS-03 crypt15 fixture generates cleanly and round-trips with both key file and 64-hex (B2.2, B2.3)."""
    out_dir = tmp_path / "DS-03-test"
    manifest = generate_crypt15_dataset(
        plaintext_dir=dummy_plaintext_dir,
        output_dir=out_dir,
        dataset_id="DS-03",
        variant="dev",
        seed=202,
    )

    assert (out_dir / "msgstore.db.crypt15").is_file()
    assert (out_dir / "keys" / "encrypted_backup.key").is_file()
    assert (out_dir / "keys" / "root_key.hex").is_file()
    assert (out_dir / "keys" / "README.md").is_file()

    # Check 64-hex key formatting
    hex_content = (out_dir / "keys" / "root_key.hex").read_text(encoding="utf-8").strip()
    assert len(hex_content) == 64
    bytes.fromhex(hex_content)  # Must be valid hexadecimal

    # Check manifest fields
    assert manifest.dataset_id == "DS-03"
    assert manifest.encryption["format"] == "crypt15"
    assert manifest.encryption["roundtrip_verified"] is True
    assert manifest.encryption["kdf"] == "HKDF-SHA256"

    # Dataset verification must pass cleanly
    is_valid, errors = verify_dataset(out_dir)
    assert is_valid, f"verify_dataset failed: {errors}"


def test_negative_fixtures_generation(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert DS-04 generates all required negative fixtures and error codes (B2.4)."""
    out_dir = tmp_path / "DS-04-test"
    manifest = generate_negative_dataset(
        plaintext_dir=dummy_plaintext_dir,
        output_dir=out_dir,
        dataset_id="DS-04",
        variant="dev",
        seed=303,
    )

    expected_files = [
        "msgstore.db.crypt15",
        "truncated_header.crypt15",
        "truncated_body.crypt15",
        "truncated_trailer.crypt15",
        "bit_flipped.crypt15",
        "random_1mb.crypt15",
        "empty.crypt15",
        "plaintext_sqlite.crypt15",
    ]
    for fname in expected_files:
        assert (out_dir / fname).is_file(), f"Expected negative fixture missing: {fname}"

    # Keys directory checks
    assert (out_dir / "keys" / "wrong_key.hex").is_file()
    assert (out_dir / "keys" / "wrong_backup.key").is_file()
    assert (out_dir / "keys" / "primary_backup.key").is_file()

    # Check manifest error codes
    expected_outcomes = manifest.encryption["expected_outcomes"]
    outcomes_by_fix = {item["fixture"]: item["expected_outcome"] for item in expected_outcomes}

    assert outcomes_by_fix["msgstore.db.crypt15"] == "AUTH_FAILED"
    assert outcomes_by_fix["truncated_header.crypt15"] == "TRUNCATED_INPUT"
    assert outcomes_by_fix["truncated_body.crypt15"] == "TRUNCATED_INPUT"
    assert outcomes_by_fix["truncated_trailer.crypt15"] == "TRUNCATED_INPUT"
    assert outcomes_by_fix["bit_flipped.crypt15"] == "AUTH_FAILED"
    assert outcomes_by_fix["random_1mb.crypt15"] == "UNSUPPORTED_VERSION"
    assert outcomes_by_fix["empty.crypt15"] == "TRUNCATED_INPUT"
    assert outcomes_by_fix["plaintext_sqlite.crypt15"] == "NOT_ENCRYPTED"

    # Dataset verification must pass cleanly
    is_valid, errors = verify_dataset(out_dir)
    assert is_valid, f"verify_dataset failed: {errors}"


def test_generator_determinism(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert encrypt generator is 100% deterministic with identical seed (R11)."""
    dir1 = tmp_path / "det1"
    dir2 = tmp_path / "det2"

    m1 = generate_crypt15_dataset(dummy_plaintext_dir, dir1, seed=404)
    m2 = generate_crypt15_dataset(dummy_plaintext_dir, dir2, seed=404)

    files1 = {f.path: f.sha256 for f in m1.files}
    files2 = {f.path: f.sha256 for f in m2.files}
    assert files1 == files2, "Crypt15 files differ between identical seed runs"
    assert m1.to_json() == m2.to_json()


def test_reference_decrypt_with_wrong_key_fails(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert reference decryptor fails with non-zero exit code when given a wrong key (AUTH_FAILED)."""
    out_dir = tmp_path / "wrong_key_test"
    generate_negative_dataset(dummy_plaintext_dir, out_dir, seed=505)

    enc_file = out_dir / "msgstore.db.crypt15"
    wrong_key = (out_dir / "keys" / "wrong_key.hex").read_text(encoding="utf-8").strip()
    out_dec = tmp_path / "should_fail.db"

    res = subprocess.run(
        [sys.executable, "-m", "wa_crypt_tools.wadecrypt", wrong_key, str(enc_file), str(out_dec), "-y"],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, "Reference decryptor must fail when provided wrong key"


def test_verify_dataset_detects_tampering(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert verify_dataset fails when an encrypted fixture is modified (tamper detection)."""
    out_dir = tmp_path / "tamper_test"
    generate_crypt15_dataset(dummy_plaintext_dir, out_dir, seed=606)

    # Corrupt one byte of encrypted file
    enc_file = out_dir / "msgstore.db.crypt15"
    content = bytearray(enc_file.read_bytes())
    content[50] ^= 0xFF
    enc_file.write_bytes(bytes(content))

    is_valid, errors = verify_dataset(out_dir)
    assert not is_valid, "verify_dataset must detect corrupted encrypted file"
    assert any("SHA-256 mismatch" in e for e in errors)


def test_verify_dataset_enforces_key_disclaimer(dummy_plaintext_dir: Path, tmp_path: Path):
    """Assert verify_dataset enforces fictitious test keys README requirement (R5, R14)."""
    out_dir = tmp_path / "disclaimer_test"
    generate_crypt14_dataset(dummy_plaintext_dir, out_dir, seed=707)

    readme_path = out_dir / "keys" / "README.md"
    readme_path.write_text("Unsanctioned text without disclaimer", encoding="utf-8")

    is_valid, errors = verify_dataset(out_dir)
    assert not is_valid, "verify_dataset must fail when README is missing fictitious disclaimer"
    assert any("fictitious disclaimer" in e for e in errors)
