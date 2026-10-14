"""
Integration and exhaustive unit tests for tamper detection (spec B5.6, R1, R3).
Verifies that single-bit and single-byte flips are detected with 100% precision.
"""

import hashlib
import random
import pytest
from sqlalchemy.orm import Session

from backend.models.models import Case, Evidence
from backend.services.integrity_service import ensure_integrity, EvidenceIntegrityError
from backend.utils.hashing import compute_multi_hashes_bytes


def test_tamper_detection_exhaustive_4k():
    """
    Exhaustively flip every single byte position in a 4 KiB (4096 bytes) fixture.
    Assert 100% (4096 / 4096) detection rate across SHA-256 and SHA-512.
    """
    # Deterministic 4 KiB pseudo-random payload
    rng = random.Random(0x4B5_4096)
    original = rng.randbytes(4096)
    original_hashes = compute_multi_hashes_bytes(original)
    orig_sha256 = original_hashes["sha256"]
    orig_sha512 = original_hashes["sha512"]
    orig_md5 = original_hashes["md5"]
    orig_sha1 = original_hashes["sha1"]

    detected_sha256 = 0
    detected_sha512 = 0
    detected_md5 = 0
    detected_sha1 = 0

    total_positions = len(original)  # 4096

    for pos in range(total_positions):
        tampered = bytearray(original)
        # Flip least significant bit of the byte at pos
        tampered[pos] ^= 0x01

        mutated_hashes = compute_multi_hashes_bytes(bytes(tampered))

        if mutated_hashes["sha256"] != orig_sha256:
            detected_sha256 += 1
        if mutated_hashes["sha512"] != orig_sha512:
            detected_sha512 += 1
        if mutated_hashes["md5"] != orig_md5:
            detected_md5 += 1
        if mutated_hashes["sha1"] != orig_sha1:
            detected_sha1 += 1

    assert detected_sha256 == total_positions, f"Expected {total_positions}, got {detected_sha256}"
    assert detected_sha512 == total_positions
    assert detected_md5 == total_positions
    assert detected_sha1 == total_positions

    detection_rate = (detected_sha256 / total_positions) * 100.0
    assert detection_rate == 100.0


def test_tamper_detection_large_fixture_500_positions():
    """
    Test >= 500 single-byte flips across a 64 KiB fixture including boundaries.
    Assert 100% detection rate.
    """
    rng = random.Random(0x4B5_65536)
    payload_size = 65536  # 64 KiB
    original = rng.randbytes(payload_size)
    orig_sha256 = hashlib.sha256(original).hexdigest()

    # Boundaries: index 0, 1, 2, -3, -2, -1
    boundary_positions = [0, 1, 2, payload_size - 3, payload_size - 2, payload_size - 1]
    # 500 random positions across the interior
    interior_positions = rng.sample(range(3, payload_size - 3), 500)
    test_positions = sorted(set(boundary_positions + interior_positions))
    assert len(test_positions) >= 500

    detected_count = 0
    for pos in test_positions:
        tampered = bytearray(original)
        # Flip high bit
        tampered[pos] ^= 0x80
        mutated_sha256 = hashlib.sha256(tampered).hexdigest()
        if mutated_sha256 != orig_sha256:
            detected_count += 1

    assert detected_count == len(test_positions)
    assert (detected_count / len(test_positions)) * 100.0 == 100.0


def test_ensure_integrity_service_catches_tampered_bytes(db_session: Session):
    """
    Verify ensure_integrity raises EvidenceIntegrityError on tampered bytes
    and updates integrity_state to HASH_MISMATCH.
    """
    case = Case(name="Tamper Test Case")
    db_session.add(case)
    db_session.commit()

    clean_bytes = b"AUTHENTIC_FORENSIC_EXHIBIT_STREAM"
    orig_sha256 = hashlib.sha256(clean_bytes).hexdigest()

    # Tampered byte in payload
    tampered_bytes = bytearray(clean_bytes)
    tampered_bytes[0] ^= 0x01

    ev = Evidence(
        case_id=case.id,
        original_filename="tampered.bin",
        storage_path="db://evidence/tampered.bin",
        content_bytes=bytes(tampered_bytes),
        sha256=orig_sha256,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()

    with pytest.raises(EvidenceIntegrityError) as exc_info:
        ensure_integrity(ev.id, db_session, action_context="tamper_verification")

    assert exc_info.value.evidence_id == ev.id
    assert exc_info.value.expected == orig_sha256

    db_session.refresh(ev)
    assert ev.integrity_state == "HASH_MISMATCH"
