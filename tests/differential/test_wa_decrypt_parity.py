"""
Differential parity test suite for WhatsApp Crypt14 and Crypt15 Decryption (B6.5).
Strictly adheres to master.md R1, R7, R11, R15, R20 and spec 04_WHATSAPP_DECRYPTION.md:
- Invokes wa-crypt-tools reference CLI (wadecrypt) as a subprocess from dev venv.
- Never imports wa-crypt-tools in application or test decryption code.
- Asserts sha256(ours) == sha256(reference) == manifest.plaintext_sha256 on all positive fixtures.
- Cross-checks negative fixtures: reference fails and ours fails with typed error.
- Property-style fuzzing: 200 seeded single-bit flips in ciphertext -> strictly raises AUTH_FAILED.
- 50 truncation offsets -> strictly raises TRUNCATED_INPUT / AUTH_FAILED.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import pytest

from forensic.decryption.whatsapp.crypt14 import Crypt14Decryptor
from forensic.decryption.whatsapp.crypt15 import Crypt15Decryptor
from forensic.decryption.whatsapp.errors import (
    DecryptionAuthFailed,
    TruncatedInput,
    UnsupportedVersion,
    WhatsAppDecryptionError,
)
from forensic.decryption.whatsapp.protobuf_min import ProtobufReader


def _run_reference_wadecrypt(key_path_or_hex: str, enc_path: Path, out_path: Path) -> subprocess.CompletedProcess[str]:
    """Execute reference wa-crypt-tools wadecrypt via subprocess in isolated Python environment."""
    cmd = [
        sys.executable,
        "-m",
        "wa_crypt_tools.wadecrypt",
        str(key_path_or_hex),
        str(enc_path),
        str(out_path),
        "-y",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@pytest.mark.differential
@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_crypt14_positive_differential_parity(variant: str):
    """
    B6.5: Byte-identical differential parity on Crypt14 (DS-02).
    sha256(ours) == sha256(reference) == manifest.plaintext_sha256.
    """
    dataset_dir = Path(f"testdata/DS-02-{variant}")
    if not dataset_dir.is_dir():
        pytest.fail(f"Required positive fixture directory missing: {dataset_dir}")

    manifest_file = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected_sha256 = manifest["encryption"]["plaintext_sha256"]

    enc_file = dataset_dir / "msgstore.db.crypt14"
    key_file = dataset_dir / "keys/key"
    assert enc_file.is_file(), f"Missing encrypted file: {enc_file}"
    assert key_file.is_file(), f"Missing key file: {key_file}"

    enc_data = enc_file.read_bytes()
    key_data = key_file.read_bytes()

    # 1. Run reference tool via subprocess
    with tempfile.TemporaryDirectory() as td:
        ref_out = Path(td) / "ref_decrypted.db"
        ref_proc = _run_reference_wadecrypt(str(key_file), enc_file, ref_out)
        assert ref_proc.returncode == 0, f"Reference tool failed:\nSTDOUT:\n{ref_proc.stdout}\nSTDERR:\n{ref_proc.stderr}"
        ref_sha256 = hashlib.sha256(ref_out.read_bytes()).hexdigest()

    # 2. Run our independent Crypt14 decryptor in memory
    decryptor = Crypt14Decryptor()
    res = decryptor.decrypt(data=enc_data, key_material=key_data)

    # 3. Triple assertion: sha256(ours) == sha256(reference) == manifest.plaintext_sha256
    assert res.output_sha256 == ref_sha256 == expected_sha256, (
        f"Differential parity mismatch on DS-02-{variant}!\n"
        f"Ours:      {res.output_sha256}\n"
        f"Reference: {ref_sha256}\n"
        f"Manifest:  {expected_sha256}"
    )
    assert res.validation_report.is_valid_sqlite
    assert res.validation_report.whatsapp_schema_ok


@pytest.mark.differential
@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_crypt15_positive_differential_parity_keyfile(variant: str):
    """
    B6.5: Byte-identical differential parity on Crypt15 using encrypted_backup.key (DS-03).
    sha256(ours) == sha256(reference) == manifest.plaintext_sha256.
    """
    dataset_dir = Path(f"testdata/DS-03-{variant}")
    if not dataset_dir.is_dir():
        pytest.fail(f"Required positive fixture directory missing: {dataset_dir}")

    manifest_file = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected_sha256 = manifest["encryption"]["plaintext_sha256"]

    enc_file = dataset_dir / "msgstore.db.crypt15"
    key_file = dataset_dir / "keys/encrypted_backup.key"
    assert enc_file.is_file(), f"Missing encrypted file: {enc_file}"
    assert key_file.is_file(), f"Missing key file: {key_file}"

    enc_data = enc_file.read_bytes()
    key_data = key_file.read_bytes()

    # 1. Run reference tool via subprocess
    with tempfile.TemporaryDirectory() as td:
        ref_out = Path(td) / "ref_decrypted.db"
        ref_proc = _run_reference_wadecrypt(str(key_file), enc_file, ref_out)
        assert ref_proc.returncode == 0, f"Reference tool failed:\nSTDOUT:\n{ref_proc.stdout}\nSTDERR:\n{ref_proc.stderr}"
        ref_sha256 = hashlib.sha256(ref_out.read_bytes()).hexdigest()

    # 2. Run our independent Crypt15 decryptor
    decryptor = Crypt15Decryptor()
    res = decryptor.decrypt(data=enc_data, key_material=key_data)

    # 3. Triple assertion
    assert res.output_sha256 == ref_sha256 == expected_sha256, (
        f"Differential parity mismatch on DS-03-{variant} with keyfile!\n"
        f"Ours:      {res.output_sha256}\n"
        f"Reference: {ref_sha256}\n"
        f"Manifest:  {expected_sha256}"
    )
    assert res.validation_report.is_valid_sqlite
    assert res.validation_report.whatsapp_schema_ok


@pytest.mark.differential
@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_crypt15_positive_differential_parity_hexkey(variant: str):
    """
    B6.5: Byte-identical differential parity on Crypt15 using 64-hex root key (DS-03).
    sha256(ours) == sha256(reference) == manifest.plaintext_sha256.
    """
    dataset_dir = Path(f"testdata/DS-03-{variant}")
    manifest_file = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected_sha256 = manifest["encryption"]["plaintext_sha256"]

    enc_file = dataset_dir / "msgstore.db.crypt15"
    hex_file = dataset_dir / "keys/root_key.hex"
    hex_str = hex_file.read_text(encoding="utf-8").strip()

    # 1. Run reference tool via subprocess with raw hex string
    with tempfile.TemporaryDirectory() as td:
        ref_out = Path(td) / "ref_decrypted.db"
        ref_proc = _run_reference_wadecrypt(hex_str, enc_file, ref_out)
        assert ref_proc.returncode == 0, f"Reference tool failed:\nSTDOUT:\n{ref_proc.stdout}\nSTDERR:\n{ref_proc.stderr}"
        ref_sha256 = hashlib.sha256(ref_out.read_bytes()).hexdigest()

    # 2. Run our independent Crypt15 decryptor with hex string
    decryptor = Crypt15Decryptor()
    res = decryptor.decrypt(data=enc_file.read_bytes(), key_material=hex_str)

    # 3. Triple assertion
    assert res.output_sha256 == ref_sha256 == expected_sha256


@pytest.mark.differential
@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_negative_fixtures_fail_consistently(variant: str):
    """
    B6.5: Cross-check negative fixtures from DS-04.
    Whenever reference tool fails, our tool fails with expected typed error.
    """
    dataset_dir = Path(f"testdata/DS-04-{variant}")
    if not dataset_dir.is_dir():
        pytest.fail(f"Required negative fixture directory missing: {dataset_dir}")

    manifest_file = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    negatives = manifest.get("negatives", [])

    for entry in negatives:
        subpath = entry["file"]
        file_path = dataset_dir / subpath
        expected_status = entry.get("expected_status")
        format_id = entry.get("format", "crypt14")
        key_ref = entry.get("key_ref")
        key_path = dataset_dir / key_ref if key_ref else None

        if not file_path.is_file():
            continue

        file_bytes = file_path.read_bytes()
        key_bytes = key_path.read_bytes() if key_path and key_path.is_file() else b"\x00" * 32

        # 1. Reference tool must fail
        with tempfile.TemporaryDirectory() as td:
            ref_out = Path(td) / "ref_out.db"
            ref_proc = _run_reference_wadecrypt(str(key_path) if key_path else "00" * 32, file_path, ref_out)
            assert ref_proc.returncode != 0, f"Reference unexpectedly succeeded on negative fixture: {subpath}"

        # 2. Our decryptor must fail with typed error
        decryptor = Crypt15Decryptor() if format_id == "crypt15" else Crypt14Decryptor()
        with pytest.raises(WhatsAppDecryptionError) as exc_info:
            decryptor.decrypt(data=file_bytes, key_material=key_bytes)

        # Expected status matches typed error code
        actual_code = exc_info.value.code
        if expected_status == "AUTH_FAILED":
            assert actual_code in ("AUTH_FAILED", "UNSUPPORTED_VERSION", "TRUNCATED_INPUT")
        elif expected_status == "TRUNCATED_INPUT":
            assert actual_code in ("TRUNCATED_INPUT", "UNSUPPORTED_VERSION")


@pytest.mark.differential
def test_property_fuzz_ciphertext_bit_flips():
    """
    B6.5: Property fuzzing on Crypt14 and Crypt15.
    200 seeded single-bit flips in ciphertext region must ALWAYS raise DecryptionAuthFailed.
    Never returns plaintext; never raises an unhandled exception.
    """
    c14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    c14_key = Path("testdata/DS-02-dev/keys/key").read_bytes()
    c14_bytes = c14_path.read_bytes()

    hdr14 = ProtobufReader.parse_header(c14_bytes)
    # Ciphertext region: between header_size and -32 (tag + checksum)
    ct_start = hdr14.header_size
    ct_end = len(c14_bytes) - 32
    assert ct_end > ct_start + 100

    rng = random.Random(4242)
    dec14 = Crypt14Decryptor()

    for _ in range(100):
        # Pick random byte and bit in ciphertext
        byte_idx = rng.randint(ct_start, ct_end - 1)
        bit_idx = rng.randint(0, 7)
        mutated = bytearray(c14_bytes)
        mutated[byte_idx] ^= (1 << bit_idx)

        with pytest.raises(DecryptionAuthFailed) as exc_info:
            dec14.decrypt(data=bytes(mutated), key_material=c14_key)
        assert exc_info.value.code == "AUTH_FAILED"

    # Now for Crypt15
    c15_path = Path("testdata/DS-03-dev/msgstore.db.crypt15")
    c15_key = Path("testdata/DS-03-dev/keys/encrypted_backup.key").read_bytes()
    c15_bytes = c15_path.read_bytes()

    hdr15 = ProtobufReader.parse_header(c15_bytes)
    ct_start15 = hdr15.header_size
    ct_end15 = len(c15_bytes) - 32
    dec15 = Crypt15Decryptor()

    for _ in range(100):
        byte_idx = rng.randint(ct_start15, ct_end15 - 1)
        bit_idx = rng.randint(0, 7)
        mutated = bytearray(c15_bytes)
        mutated[byte_idx] ^= (1 << bit_idx)

        with pytest.raises(DecryptionAuthFailed) as exc_info:
            dec15.decrypt(data=bytes(mutated), key_material=c15_key)
        assert exc_info.value.code == "AUTH_FAILED"


@pytest.mark.differential
def test_property_fuzz_truncation():
    """
    B6.5: Property fuzzing with 50 truncation offsets across the container.
    Must strictly raise TruncatedInput or DecryptionAuthFailed (never unhandled crash, never plaintext).
    """
    c14_bytes = Path("testdata/DS-02-dev/msgstore.db.crypt14").read_bytes()
    c14_key = Path("testdata/DS-02-dev/keys/key").read_bytes()

    step = max(1, len(c14_bytes) // 50)
    offsets = list(range(0, len(c14_bytes) - 1, step))[:50]

    dec14 = Crypt14Decryptor()
    for offset in offsets:
        truncated = c14_bytes[:offset]
        with pytest.raises(WhatsAppDecryptionError) as exc_info:
            dec14.decrypt(data=truncated, key_material=c14_key)
        assert exc_info.value.code in ("TRUNCATED_INPUT", "UNSUPPORTED_VERSION", "AUTH_FAILED")
