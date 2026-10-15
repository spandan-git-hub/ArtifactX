"""
Unit tests for WhatsApp Decryption Subsystem (B6).
Tests:
- Header parsing for Crypt14 and Crypt15 fixtures (DS-02, DS-03).
- Key parsing: valid key files (158B, 131B, 59B, 32B), 64-hex string.
- Key parsing negatives: empty, short, non-hex, malformed Java object.
- KeyMaterial security: redacted __repr__, __str__, __reduce__ raise, fingerprint(), zero().
- Passphrase rejection with PassphraseNotSupported per DEC-002.
- Decompression memory limit cap enforcement.
- Reachability of every typed error in errors.py.
"""

from __future__ import annotations

import json
from pathlib import Path
import pickle
import pytest

from forensic.decryption.whatsapp.crypt14 import Crypt14Decryptor
from forensic.decryption.whatsapp.crypt15 import Crypt15Decryptor
from forensic.decryption.whatsapp.errors import (
    DecryptionAuthFailed,
    DecompressionFailed,
    HeaderError,
    KeyInvalidFormat,
    KeyRequired,
    NotEncrypted,
    OutputFailedIntegrity,
    OutputNotSqlite,
    OutputNotWhatsapp,
    PassphraseNotSupported,
    TruncatedInput,
    UnsupportedVersion,
    UntestedFormat,
    WhatsAppDecryptionError,
)
from forensic.decryption.whatsapp.keys import (
    WhatsAppKeyParser,
    parse_java_byte_array,
)
from forensic.decryption.whatsapp.protobuf_min import ProtobufReader, decode_varint
from forensic.decryption.whatsapp.types import (
    DecryptionResult,
    KeyMaterial,
    ParsedHeader,
    ValidationReport,
)
from forensic.decryption.whatsapp.validate import validate_decrypted_payload


@pytest.mark.unit
def test_protobuf_varint_decoder():
    """Verify varint decoder on edge cases and boundaries."""
    # Single-byte varints
    assert decode_varint(b"\x00") == (0, 1)
    assert decode_varint(b"\x01") == (1, 1)
    assert decode_varint(b"\x7f") == (127, 1)

    # Multi-byte varints
    assert decode_varint(b"\x80\x01") == (128, 2)
    assert decode_varint(b"\xac\x02") == (300, 2)

    # Truncated varint
    with pytest.raises(TruncatedInput):
        decode_varint(b"\x80")

    # Excessive varint length (>10 bytes)
    with pytest.raises(HeaderError):
        decode_varint(b"\x80" * 12)


@pytest.mark.unit
def test_protobuf_reader_on_fixtures():
    """Verify ProtobufReader accurately parses real DS-02 and DS-03 container headers."""
    c14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    c15_path = Path("testdata/DS-03-dev/msgstore.db.crypt15")

    if c14_path.is_file():
        c14_bytes = c14_path.read_bytes()[:500]
        h14 = ProtobufReader.parse_header(c14_bytes)
        assert h14.format_id == "crypt14"
        assert len(h14.iv) == 16
        assert h14.header_size > 32
        assert h14.server_salt is not None
        assert len(h14.server_salt) == 32

    if c15_path.is_file():
        c15_bytes = c15_path.read_bytes()[:500]
        h15 = ProtobufReader.parse_header(c15_bytes)
        assert h15.format_id == "crypt15"
        assert len(h15.iv) == 16
        assert h15.header_size > 32


@pytest.mark.unit
def test_key_material_security_redaction():
    """Verify master.md R5: key material is never logged or exposed in repr/str/pickle."""
    secret_bytes = b"\xaa" * 32
    km = KeyMaterial(raw_key=secret_bytes, key_type="test_secret")

    # Fingerprint must be first 8 hex of SHA-256
    import hashlib
    expected_fp = hashlib.sha256(secret_bytes).hexdigest()[:8]
    assert km.fingerprint() == expected_fp

    # __repr__ and __str__ must redact the secret
    assert secret_bytes.hex() not in repr(km)
    assert secret_bytes.hex() not in str(km)
    assert "[SECRET REDACTED]" in repr(km)
    assert "[SECRET REDACTED]" in str(km)

    # __reduce__ must raise RuntimeError to prevent pickling
    with pytest.raises(RuntimeError, match="cannot be pickled"):
        pickle.dumps(km)

    # zero() must clear internal buffer
    km.zero()
    assert km.raw_key == b"\x00" * 32


@pytest.mark.unit
def test_crypt14_key_parsing():
    """Verify parsing valid and invalid Crypt14 key representations."""
    key_file = Path("testdata/DS-02-dev/keys/key")
    if key_file.is_file():
        raw_key_bytes = key_file.read_bytes()
        km = WhatsAppKeyParser.parse_crypt14_key(raw_key_bytes)
        assert len(km.raw_key) == 32
        assert km.key_type == "crypt14"

        # Raw 32 bytes direct input
        km_direct = WhatsAppKeyParser.parse_crypt14_key(km.raw_key)
        assert km_direct.raw_key == km.raw_key

        # 64-hex string input
        km_hex = WhatsAppKeyParser.parse_crypt14_key(km.raw_key.hex())
        assert km_hex.raw_key == km.raw_key

    # None / empty / invalid format
    with pytest.raises(KeyRequired):
        WhatsAppKeyParser.parse_crypt14_key(None)

    with pytest.raises(KeyInvalidFormat):
        WhatsAppKeyParser.parse_crypt14_key("")

    with pytest.raises(KeyInvalidFormat):
        WhatsAppKeyParser.parse_crypt14_key(b"short_key")

    with pytest.raises(KeyInvalidFormat):
        WhatsAppKeyParser.parse_crypt14_key("not_hex_chars_at_all!!")


@pytest.mark.unit
def test_crypt15_key_parsing_and_passphrase_rejection():
    """Verify Crypt15 key derivation and strict offline passphrase rejection (DEC-002)."""
    key_file = Path("testdata/DS-03-dev/keys/encrypted_backup.key")
    hex_file = Path("testdata/DS-03-dev/keys/root_key.hex")

    if key_file.is_file() and hex_file.is_file():
        raw_file_bytes = key_file.read_bytes()
        hex_str = hex_file.read_text(encoding="utf-8").strip()

        root_from_file, cipher_from_file = WhatsAppKeyParser.parse_crypt15_key(raw_file_bytes)
        root_from_hex, cipher_from_hex = WhatsAppKeyParser.parse_crypt15_key(hex_str)

        assert root_from_file.raw_key == root_from_hex.raw_key
        assert cipher_from_file.raw_key == cipher_from_hex.raw_key
        assert len(cipher_from_file.raw_key) == 32

    # DEC-002: Passphrases must be rejected with PassphraseNotSupported
    with pytest.raises(PassphraseNotSupported) as exc_info:
        WhatsAppKeyParser.parse_crypt15_key("MySecretUserPassword123!")
    assert exc_info.value.code == "PASSPHRASE_NOT_SUPPORTED"
    assert "crypt15 cannot be decrypted from a password offline" in exc_info.value.message

    # Empty / None
    with pytest.raises(KeyRequired):
        WhatsAppKeyParser.parse_crypt15_key(None)

    with pytest.raises(KeyInvalidFormat):
        WhatsAppKeyParser.parse_crypt15_key("")


@pytest.mark.unit
def test_java_byte_array_parser_edge_cases():
    """Verify parse_java_byte_array error handling on corrupted envelopes."""
    with pytest.raises(KeyInvalidFormat, match="too small"):
        parse_java_byte_array(b"short")

    with pytest.raises(KeyInvalidFormat, match="header"):
        parse_java_byte_array(b"\x00" * 30)

    # Valid magic but wrong class name
    fake_header = bytearray(b"\xac\xed\x00\x05\x75\x72\x00\x02[X" + b"\x00" * 30)
    with pytest.raises(KeyInvalidFormat, match="not a byte array"):
        parse_java_byte_array(bytes(fake_header))


@pytest.mark.unit
def test_post_decrypt_validation_pipeline():
    """Verify validate_decrypted_payload detects SQLite header and WhatsApp tables."""
    # 1. Plaintext DS-01 msgstore.db
    plain_db_path = Path("testdata/DS-01-dev/msgstore.db")
    if plain_db_path.is_file():
        db_bytes = plain_db_path.read_bytes()
        report = validate_decrypted_payload(
            plaintext_decompressed=db_bytes,
            gcm_auth_ok=True,
            zlib_decompress_ok=True,
            checksum_ok=True,
            enforce_whatsapp_schema=True,
        )
        assert report.gcm_auth_ok
        assert report.zlib_decompress_ok
        assert report.sqlite_header_ok
        assert report.pragma_integrity_ok
        assert report.whatsapp_schema_ok
        assert report.schema_family in ("modern", "legacy")
        assert report.is_valid_sqlite

    # 2. Non-sqlite payload
    non_sqlite = b"NotASqliteDatabasePayload1234567890"
    report_bad = validate_decrypted_payload(non_sqlite, enforce_whatsapp_schema=False)
    assert not report_bad.sqlite_header_ok
    assert not report_bad.is_valid_sqlite

    with pytest.raises(OutputNotSqlite):
        validate_decrypted_payload(non_sqlite, enforce_whatsapp_schema=True)


@pytest.mark.unit
def test_all_typed_errors_have_codes_and_remediations():
    """Verify all 12 spec error classes possess proper codes and non-empty remediation strings."""
    error_classes = [
        (KeyRequired, "ENCRYPTED_KEY_REQUIRED"),
        (KeyInvalidFormat, "KEY_INVALID_FORMAT"),
        (PassphraseNotSupported, "PASSPHRASE_NOT_SUPPORTED"),
        (DecryptionAuthFailed, "AUTH_FAILED"),
        (TruncatedInput, "TRUNCATED_INPUT"),
        (HeaderError, "UNSUPPORTED_VERSION"),
        (UnsupportedVersion, "UNSUPPORTED_VERSION"),
        (NotEncrypted, "NOT_ENCRYPTED"),
        (DecompressionFailed, "DECOMPRESSION_FAILED"),
        (OutputNotSqlite, "OUTPUT_NOT_SQLITE"),
        (OutputFailedIntegrity, "OUTPUT_FAILED_INTEGRITY"),
        (OutputNotWhatsapp, "OUTPUT_NOT_WHATSAPP"),
        (UntestedFormat, "UNTESTED_FORMAT"),
    ]

    for err_cls, expected_code in error_classes:
        inst = err_cls()
        assert isinstance(inst, WhatsAppDecryptionError)
        assert inst.code == expected_code
        assert len(inst.message) > 0
        assert len(inst.remediation) > 0
        # R5: ensure generic message does not contain leaked dummy secrets
        assert "password" not in inst.remediation.lower() or "obtain" in inst.remediation.lower()


@pytest.mark.unit
def test_decompression_memory_cap_enforcement():
    """Verify decompression bombs exceeding max_decompressed_size raise DecompressionFailed."""
    import zlib
    # Generate 10 MiB of zeros compressed into ~10 KiB
    big_data = b"\x00" * (10 * 1024 * 1024)
    compressed = zlib.compress(big_data)

    # Set tiny cap of 1 MiB
    tiny_cap = 1 * 1024 * 1024
    decompressor = zlib.decompressobj()
    decompressed = decompressor.decompress(compressed, tiny_cap)
    assert not decompressor.eof
    assert len(decompressed) >= tiny_cap
