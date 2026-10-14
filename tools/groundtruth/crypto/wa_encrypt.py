"""WhatsApp encrypted fixture generator (B2).

Follows master.md R5, R6, R7, R11, R14, R15, R20 and spec 02_GROUND_TRUTH_DATASETS.md:
- Uses wa-crypt-tools (pinned v0.2.0, commit b16a805) via subprocess to generate:
  - DS-02: WhatsApp modern msgstore.db encrypted as crypt14 + key file
  - DS-03: WhatsApp modern msgstore.db encrypted as crypt15 + 64-hex key + encrypted_backup.key
  - DS-04: Negative fixtures (wrong key, truncated, bit-flipped, random bytes, empty, plaintext)
- Validates round-trip decrypt against reference tool, asserting SHA-256 equals original plaintext.
- Never stores key material in manifest.json; test keys reside under keys/ with README.
- Purely deterministic; derived strictly from DeterministicRNG(seed).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.groundtruth.manifest import DatasetFileInfo, DatasetManifest
from tools.groundtruth.rng import DeterministicRNG


def _compute_sha256(path: Path) -> Tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _fingerprint(key_bytes: bytes) -> str:
    """Return first 8 hex characters of SHA-256 of key bytes (master.md R5)."""
    return hashlib.sha256(key_bytes).hexdigest()[:8]


def _run_tool_command(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    """Execute a wa_crypt_tools CLI command using the virtualenv python interpreter."""
    full_cmd = [sys.executable, "-m", *cmd]
    res = subprocess.run(
        full_cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(full_cmd)} failed with returncode {res.returncode}:\n"
            f"STDOUT:\n{res.stdout}\n"
            f"STDERR:\n{res.stderr}"
        )
    return res


def _collect_file_infos(target_dir: Path) -> List[DatasetFileInfo]:
    """Collect all files inside target_dir recursively (excluding manifest.json)."""
    files: List[DatasetFileInfo] = []
    for root, _, filenames in os.walk(str(target_dir)):
        for fname in sorted(filenames):
            if fname == "manifest.json":
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(target_dir).as_posix()
            sha, sz = _compute_sha256(fpath)
            files.append(DatasetFileInfo(path=rel, sha256=sha, size=sz))
    files.sort(key=lambda x: x.path)
    return files


def generate_crypt14_dataset(
    plaintext_dir: Path,
    output_dir: Path,
    dataset_id: str = "DS-02",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate DS-02: WhatsApp modern msgstore.db encrypted in crypt14 format."""
    plaintext_dir = Path(plaintext_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plain_db = plaintext_dir / "msgstore.db"
    if not plain_db.is_file():
        raise FileNotFoundError(f"Plaintext database missing: {plain_db}")
    plain_sha256, plain_size = _compute_sha256(plain_db)

    # 1. Initialize RNG
    actual_seed = seed if seed is not None else (42 if variant == "dev" else 1337)
    rng = DeterministicRNG(actual_seed)

    # 2. Derive deterministic keys and parameters
    key_bytes = rng.random_bytes(32)
    key_hex = key_bytes.hex()
    server_salt = rng.random_bytes(32).hex()
    google_id = rng.random_bytes(16).hex()
    iv_hex = rng.random_bytes(16).hex()

    # 3. Create keys directory and key file
    keys_dir = output_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    key_file = keys_dir / "key"

    readme_file = keys_dir / "README.md"
    readme_file.write_text(
        "# Test Keys (Fictitious)\n\n"
        "This directory contains fictitious test keys generated strictly for synthetic evaluation "
        "in ArtifactX (master.md R5, R14). These keys do not belong to real devices or users.\n",
        encoding="utf-8",
    )

    _run_tool_command(
        [
            "wa_crypt_tools.wacreatekey",
            "-c14",
            "-o",
            str(key_file),
            "--hex",
            key_hex,
            "-ss",
            server_salt,
            "-gi",
            google_id,
            "-y",
        ]
    )

    # 4. Encrypt plaintext database into crypt14 format
    encrypted_file = output_dir / "msgstore.db.crypt14"
    _run_tool_command(
        [
            "wa_crypt_tools.waencrypt",
            "--type",
            "14",
            "--iv",
            iv_hex,
            str(key_file),
            str(plain_db),
            str(encrypted_file),
            "-y",
        ]
    )

    # 5. Round-trip verification against reference tool (B2.3)
    with tempfile.TemporaryDirectory() as td:
        decrypted_test = Path(td) / "decrypted_test.db"
        _run_tool_command(
            [
                "wa_crypt_tools.wadecrypt",
                str(key_file),
                str(encrypted_file),
                str(decrypted_test),
                "-y",
            ]
        )
        dec_sha, _ = _compute_sha256(decrypted_test)
        if dec_sha != plain_sha256:
            raise RuntimeError(
                f"Reference round-trip SHA-256 mismatch for crypt14! "
                f"Expected {plain_sha256}, got {dec_sha}"
            )

    # 6. Build and save manifest
    file_infos = _collect_file_infos(output_dir)
    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=actual_seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "wa_crypt_tools": "0.2.0 (b16a805)",
            "python": sys.version.split()[0],
        },
        files=file_infos,
        whatsapp={},
        encryption={
            "format": "crypt14",
            "key_ref": "keys/key",
            "plaintext_sha256": plain_sha256,
            "roundtrip_verified": True,
            "cipher": "AES-256-GCM",
            "iv_hex": iv_hex,
            "key_fingerprint": _fingerprint(key_bytes),
        },
        modelled_vs_observed={
            "container": "modelled per wa-crypt-tools 0.2.0 specification",
            "cipher": "AES-256-GCM",
            "trailer": "MD5 checksum over container bytes",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest


def generate_crypt15_dataset(
    plaintext_dir: Path,
    output_dir: Path,
    dataset_id: str = "DS-03",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate DS-03: WhatsApp modern msgstore.db encrypted in crypt15 format."""
    plaintext_dir = Path(plaintext_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plain_db = plaintext_dir / "msgstore.db"
    if not plain_db.is_file():
        raise FileNotFoundError(f"Plaintext database missing: {plain_db}")
    plain_sha256, plain_size = _compute_sha256(plain_db)

    # 1. Initialize RNG
    actual_seed = seed if seed is not None else (42 if variant == "dev" else 1337)
    rng = DeterministicRNG(actual_seed)

    # 2. Derive deterministic 32-byte root key and IV
    root_key_bytes = rng.random_bytes(32)
    root_key_hex = root_key_bytes.hex()
    iv_hex = rng.random_bytes(16).hex()

    # 3. Create keys directory, hex key file, and binary encrypted_backup.key
    keys_dir = output_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    readme_file = keys_dir / "README.md"
    readme_file.write_text(
        "# Test Keys (Fictitious)\n\n"
        "This directory contains fictitious test keys generated strictly for synthetic evaluation "
        "in ArtifactX (master.md R5, R14). These keys do not belong to real devices or users.\n",
        encoding="utf-8",
    )

    hex_key_file = keys_dir / "root_key.hex"
    hex_key_file.write_text(root_key_hex + "\n", encoding="utf-8")

    key_file = keys_dir / "encrypted_backup.key"
    _run_tool_command(
        [
            "wa_crypt_tools.wacreatekey",
            "-o",
            str(key_file),
            "--hex",
            root_key_hex,
            "-y",
        ]
    )

    # 4. Encrypt plaintext database into crypt15 format
    encrypted_file = output_dir / "msgstore.db.crypt15"
    _run_tool_command(
        [
            "wa_crypt_tools.waencrypt",
            "--type",
            "15",
            "--iv",
            iv_hex,
            str(key_file),
            str(plain_db),
            str(encrypted_file),
            "-y",
        ]
    )

    # 5. Round-trip verification against reference tool (B2.3)
    # Check both encrypted_backup.key file and direct 64-hex string!
    with tempfile.TemporaryDirectory() as td:
        dec_file_test = Path(td) / "dec_file.db"
        _run_tool_command(
            [
                "wa_crypt_tools.wadecrypt",
                str(key_file),
                str(encrypted_file),
                str(dec_file_test),
                "-y",
            ]
        )
        dec_file_sha, _ = _compute_sha256(dec_file_test)
        if dec_file_sha != plain_sha256:
            raise RuntimeError(
                f"Reference round-trip SHA-256 mismatch with key file! "
                f"Expected {plain_sha256}, got {dec_file_sha}"
            )

        dec_hex_test = Path(td) / "dec_hex.db"
        _run_tool_command(
            [
                "wa_crypt_tools.wadecrypt",
                root_key_hex,
                str(encrypted_file),
                str(dec_hex_test),
                "-y",
            ]
        )
        dec_hex_sha, _ = _compute_sha256(dec_hex_test)
        if dec_hex_sha != plain_sha256:
            raise RuntimeError(
                f"Reference round-trip SHA-256 mismatch with 64-hex key! "
                f"Expected {plain_sha256}, got {dec_hex_sha}"
            )

    # 6. Build and save manifest
    file_infos = _collect_file_infos(output_dir)
    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=actual_seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "wa_crypt_tools": "0.2.0 (b16a805)",
            "python": sys.version.split()[0],
        },
        files=file_infos,
        whatsapp={},
        encryption={
            "format": "crypt15",
            "key_ref": "keys/encrypted_backup.key",
            "hex_key_ref": "keys/root_key.hex",
            "plaintext_sha256": plain_sha256,
            "roundtrip_verified": True,
            "cipher": "AES-256-GCM",
            "kdf": "HKDF-SHA256",
            "iv_hex": iv_hex,
            "key_fingerprint": _fingerprint(root_key_bytes),
        },
        modelled_vs_observed={
            "container": "modelled per wa-crypt-tools 0.2.0 specification",
            "cipher": "AES-256-GCM",
            "kdf": "HKDF-SHA256 with info='backup encryption'",
            "trailer": "MD5 checksum over container bytes",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest


def generate_negative_dataset(
    plaintext_dir: Path,
    output_dir: Path,
    dataset_id: str = "DS-04",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate DS-04: Negative and honest-failure fixtures (B2.4)."""
    plaintext_dir = Path(plaintext_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plain_db = plaintext_dir / "msgstore.db"
    if not plain_db.is_file():
        raise FileNotFoundError(f"Plaintext database missing: {plain_db}")

    actual_seed = seed if seed is not None else (42 if variant == "dev" else 1337)
    rng = DeterministicRNG(actual_seed)

    # 1. Generate keys: primary root key and a separate "wrong" root key
    primary_key_bytes = rng.random_bytes(32)
    primary_key_hex = primary_key_bytes.hex()
    wrong_key_bytes = rng.random_bytes(32)
    wrong_key_hex = wrong_key_bytes.hex()
    iv_hex = rng.random_bytes(16).hex()

    keys_dir = output_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    readme_file = keys_dir / "README.md"
    readme_file.write_text(
        "# Test Keys (Fictitious Negative Fixtures)\n\n"
        "This directory contains fictitious test keys generated strictly for synthetic negative-testing "
        "in ArtifactX (master.md R5, R14). None belong to real devices or users.\n",
        encoding="utf-8",
    )

    primary_key_file = keys_dir / "primary_backup.key"
    _run_tool_command(
        [
            "wa_crypt_tools.wacreatekey",
            "-o",
            str(primary_key_file),
            "--hex",
            primary_key_hex,
            "-y",
        ]
    )
    (keys_dir / "primary_key.hex").write_text(primary_key_hex + "\n", encoding="utf-8")

    wrong_key_file = keys_dir / "wrong_backup.key"
    _run_tool_command(
        [
            "wa_crypt_tools.wacreatekey",
            "-o",
            str(wrong_key_file),
            "--hex",
            wrong_key_hex,
            "-y",
        ]
    )
    (keys_dir / "wrong_key.hex").write_text(wrong_key_hex + "\n", encoding="utf-8")

    # 2. Build valid crypt15 base file to create corrupted/truncated versions from
    valid_crypt15 = output_dir / "msgstore.db.crypt15"
    _run_tool_command(
        [
            "wa_crypt_tools.waencrypt",
            "--type",
            "15",
            "--iv",
            iv_hex,
            str(primary_key_file),
            str(plain_db),
            str(valid_crypt15),
            "-y",
        ]
    )
    valid_bytes = valid_crypt15.read_bytes()

    # 3. Create negative fixtures:
    # (a) Truncated inside header prefix (e.g. 12 bytes)
    trunc_header_file = output_dir / "truncated_header.crypt15"
    trunc_header_file.write_bytes(valid_bytes[:12])

    # (b) Truncated inside ciphertext body (half length)
    trunc_body_file = output_dir / "truncated_body.crypt15"
    trunc_body_file.write_bytes(valid_bytes[: len(valid_bytes) // 2])

    # (c) Truncated trailer (strip trailing 16 bytes MD5)
    trunc_trailer_file = output_dir / "truncated_trailer.crypt15"
    trunc_trailer_file.write_bytes(valid_bytes[:-16])

    # (d) Bit-flipped ciphertext (flip bit at offset 128)
    bit_flipped_file = output_dir / "bit_flipped.crypt15"
    flipped_bytes = bytearray(valid_bytes)
    flip_pos = min(128, len(flipped_bytes) - 20)
    flipped_bytes[flip_pos] ^= 0x01
    bit_flipped_file.write_bytes(bytes(flipped_bytes))

    # (e) Random 1 MiB file named .crypt15
    random_file = output_dir / "random_1mb.crypt15"
    random_bytes = rng.random_bytes(1024 * 1024)
    random_file.write_bytes(random_bytes)

    # (f) Empty 0-byte file named .crypt15
    empty_file = output_dir / "empty.crypt15"
    empty_file.write_bytes(b"")

    # (g) Plaintext SQLite database named with .crypt15 extension
    plaintext_masquerade = output_dir / "plaintext_sqlite.crypt15"
    plaintext_masquerade.write_bytes(plain_db.read_bytes())

    # 4. Prepare expected typed outcomes list per 04_WHATSAPP_DECRYPTION.md §2
    expected_outcomes = [
        {
            "fixture": "msgstore.db.crypt15",
            "key_ref": "keys/wrong_key.hex",
            "expected_outcome": "AUTH_FAILED",
            "description": "Valid crypt15 encrypted backup decrypted with a mismatched valid 64-hex key",
        },
        {
            "fixture": "msgstore.db.crypt15",
            "key_ref": "keys/wrong_backup.key",
            "expected_outcome": "AUTH_FAILED",
            "description": "Valid crypt15 encrypted backup decrypted with a mismatched encrypted_backup.key file",
        },
        {
            "fixture": "truncated_header.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "TRUNCATED_INPUT",
            "description": "File truncated inside the protobuf BackupPrefix header (12 bytes)",
        },
        {
            "fixture": "truncated_body.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "TRUNCATED_INPUT",
            "description": "File truncated halfway through the AES-GCM ciphertext payload",
        },
        {
            "fixture": "truncated_trailer.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "TRUNCATED_INPUT",
            "description": "File truncated by stripping the trailing 16-byte MD5 checksum",
        },
        {
            "fixture": "bit_flipped.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "AUTH_FAILED",
            "description": "Crypt15 file with 1-bit flip in ciphertext payload causing GCM tag authentication failure",
        },
        {
            "fixture": "random_1mb.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "UNSUPPORTED_VERSION",
            "description": "1 MiB pseudo-random byte stream with invalid header/version named .crypt15",
        },
        {
            "fixture": "empty.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "TRUNCATED_INPUT",
            "description": "0-byte empty file named .crypt15",
        },
        {
            "fixture": "plaintext_sqlite.crypt15",
            "key_ref": "keys/primary_backup.key",
            "expected_outcome": "NOT_ENCRYPTED",
            "description": "Valid unencrypted SQLite database masquerading with a .crypt15 extension",
        },
    ]

    # 5. Build and save manifest
    file_infos = _collect_file_infos(output_dir)
    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=actual_seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "wa_crypt_tools": "0.2.0 (b16a805)",
            "python": sys.version.split()[0],
        },
        files=file_infos,
        whatsapp={},
        encryption={
            "format": "crypt15_negatives",
            "primary_key_fingerprint": _fingerprint(primary_key_bytes),
            "wrong_key_fingerprint": _fingerprint(wrong_key_bytes),
            "expected_outcomes": expected_outcomes,
        },
        modelled_vs_observed={
            "negatives": "synthetic error and corruption conditions modeled per 04_WHATSAPP_DECRYPTION.md §2",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest
