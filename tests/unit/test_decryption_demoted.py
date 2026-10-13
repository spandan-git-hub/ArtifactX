"""
Tests for Section A6: Remove / demote unvalidated decryptors.
Verifies:
1. Telegram SQLCipher and MTProto decryptors removed (A6.1).
2. WhatsApp media (.enc) decryptor removed (A6.2).
3. Detector excludes known high-entropy compressed containers and reports
   unknown high-entropy files as UNKNOWN_ENCRYPTED_KEY_REQUIRED with no format claim (A6.3).
4. Decryptor plugin interface (Protocol) and DECRYPTOR_NOT_AVAILABLE status (A6.4).
"""

import os
import pytest
from typing import Optional

from forensic.decryption.detector import EncryptionDetector, FormatDetectionResult
from forensic.decryption.orchestrator import (
    DecryptionOrchestrator,
    Decryptor,
    DecryptorNotAvailableError,
    KeyMaterial,
    DecryptionResult,
)
from backend.schemas.decryption import DecryptionRunRequest


@pytest.mark.unit
def test_removed_modules_are_not_importable():
    """A6.1 & A6.2: sqlcipher, mtproto, and media decryptor modules must be deleted."""
    with pytest.raises(ImportError):
        import forensic.decryption.telegram.sqlcipher  # type: ignore # noqa: F401

    with pytest.raises(ImportError):
        import forensic.decryption.telegram.mtproto  # type: ignore # noqa: F401

    with pytest.raises(ImportError):
        import forensic.decryption.whatsapp.media  # type: ignore # noqa: F401


@pytest.mark.unit
def test_detector_does_not_claim_sqlcipher_or_mtproto_or_enc():
    """A6.1 & A6.2: Detector must never claim sqlcipher, mtproto, or whatsapp_enc."""
    high_entropy_bytes = bytes((i * 101 + 37) % 256 for i in range(4096))

    # Even with filenames hinting at telegram/sqlcipher/mtproto/.enc
    r1 = EncryptionDetector.detect(high_entropy_bytes, "cache4.db")
    assert r1.format not in ("sqlcipher", "telegram_sqlcipher")

    r2 = EncryptionDetector.detect(high_entropy_bytes, "secret_chat.bin")
    assert r2.format not in ("mtproto", "telegram_secret_chat")

    r3 = EncryptionDetector.detect(high_entropy_bytes, "msg.enc")
    assert r3.format != "whatsapp_enc"


@pytest.mark.unit
@pytest.mark.parametrize(
    "container_name,magic_header",
    [
        ("ZIP", b"PK\x03\x04\x14\x00\x00\x00"),
        ("GZIP", b"\x1f\x8b\x08\x00\x00\x00\x00\x00"),
        ("JPEG", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"),
        ("PNG", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
        ("MP4", b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00"),
        ("7z", b"7z\xbc\xaf\x27\x1c\x00\x04"),
        ("RAR", b"Rar!\x1a\x07\x00\xcf\x90\x73"),
        ("PDF", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"),
    ],
)
def test_detector_excludes_known_high_entropy_containers(container_name: str, magic_header: bytes):
    """
    A6.3: Known compressed / media containers must be excluded by magic bytes
    and never classified as encrypted ciphertext.
    """
    # Create high-entropy pseudo-random body following magic bytes
    random_payload = bytes((i * 97 + 13) % 256 for i in range(2048))
    data = magic_header + random_payload

    result = EncryptionDetector.detect(data, f"sample.{container_name.lower()}")
    assert not result.is_encrypted, f"{container_name} container must not be detected as encrypted"
    assert result.format is None
    assert any("compressed" in r.lower() or container_name.lower() in r.lower() for r in result.reasons)


@pytest.mark.unit
def test_detector_reports_unknown_high_entropy_honestly():
    """
    A6.3: Unknown high-entropy payload without known container or crypt magic
    must report UNKNOWN_ENCRYPTED_KEY_REQUIRED with no format claim.
    """
    # Deterministic high-entropy block without any known magic
    data = bytes((i * 137 + 59) % 256 for i in range(2048))
    result = EncryptionDetector.detect(data, "unknown.bin")

    assert result.is_encrypted is True
    assert result.format == "UNKNOWN_ENCRYPTED_KEY_REQUIRED"
    assert result.entropy > 7.5
    assert any("unknown" in r.lower() or "no known" in r.lower() for r in result.reasons)


@pytest.mark.unit
def test_orchestrator_plugin_interface():
    """A6.4: DecryptionOrchestrator exposes clean Decryptor plugin protocol."""
    class DummyDecryptor:
        format_id: str = "test_custom_format"

        def can_handle(self, header: bytes, filename: Optional[str] = None) -> bool:
            return header.startswith(b"TEST_MAGIC")

        def decrypt(self, data: bytes, key_material: KeyMaterial) -> DecryptionResult:
            return DecryptionResult(
                plaintext=b"DECRYPTED_OK",
                format_id=self.format_id,
                output_sha256="fake_sha",
                metadata={"test": True},
            )

    dummy = DummyDecryptor()
    assert isinstance(dummy, Decryptor)

    DecryptionOrchestrator.register(dummy)
    assert "test_custom_format" in DecryptionOrchestrator.get_registered_formats()

    # Clean up registry
    DecryptionOrchestrator.unregister("test_custom_format")
    assert "test_custom_format" not in DecryptionOrchestrator.get_registered_formats()


@pytest.mark.unit
def test_orchestrator_raises_decryptor_not_available():
    """A6.4: Demoted/unregistered decryptors raise DecryptorNotAvailableError."""
    fake_crypt_data = b"crypt15_header_bytes_" + bytes(200)

    with pytest.raises(DecryptorNotAvailableError) as exc_info:
        DecryptionOrchestrator.decrypt(
            data=fake_crypt_data,
            key_or_passcode="0123456789abcdef" * 4,
            format_hint="crypt15",
        )

    assert "crypt15" in str(exc_info.value).lower()
    assert "not available" in str(exc_info.value).lower()


@pytest.mark.unit
def test_decryption_run_request_schema():
    """A6.1: DecryptionRunRequest has key_material and no passcode field."""
    # passcode should not be in model fields
    assert "passcode" not in DecryptionRunRequest.model_fields
    req = DecryptionRunRequest(key_material="0123456789abcdef" * 4)
    assert req.key_material is not None


@pytest.mark.unit
def test_detector_edge_cases_and_to_dict():
    """Verify empty inputs, SQLite unencrypted magic, and to_dict serialization."""
    empty_res = EncryptionDetector.detect(b"")
    assert not empty_res.is_encrypted
    assert "empty" in empty_res.reasons[0].lower()

    short_res = EncryptionDetector.detect(b"short_bytes")
    assert not short_res.is_encrypted

    sqlite_data = b"SQLite format 3\x00" + bytes(100)
    sqlite_res = EncryptionDetector.detect(sqlite_data)
    assert not sqlite_res.is_encrypted
    assert sqlite_res.confidence == 1.0
    d = sqlite_res.to_dict()
    assert d["is_encrypted"] is False
    assert d["confidence"] == 1.0


@pytest.mark.unit
def test_detector_whatsapp_crypt_signatures():
    """Verify WhatsApp Crypt12, Crypt14, Crypt15 detection heuristics."""
    high_entropy = bytes((i * 137 + 59) % 256 for i in range(1024))

    # Filename based
    c12 = EncryptionDetector.detect(high_entropy, "msgstore.db.crypt12")
    assert c12.is_encrypted and c12.format == "crypt12"

    c14 = EncryptionDetector.detect(high_entropy, "msgstore.db.crypt14")
    assert c14.is_encrypted and c14.format == "crypt14"

    c15 = EncryptionDetector.detect(high_entropy, "msgstore.db.crypt15")
    assert c15.is_encrypted and c15.format == "crypt15"

    # Embedded magic in header without filename
    header_with_magic = b"\x00" * 10 + b"crypt14" + b"\x00" * 50 + high_entropy
    c14_magic = EncryptionDetector.detect(header_with_magic)
    assert c14_magic.is_encrypted and c14_magic.format == "crypt14"


@pytest.mark.unit
def test_orchestrator_execution_workflow_with_plugin():
    """Verify DecryptionOrchestrator dispatch with registered plugin for different key types."""
    class MockPlugin:
        format_id = "test_engine"

        def can_handle(self, header: bytes, filename: Optional[str] = None) -> bool:
            return True

        def decrypt(self, data: bytes, key_material: KeyMaterial) -> DecryptionResult:
            return DecryptionResult(
                plaintext=b"DECRYPTED_PAYLOAD",
                format_id=self.format_id,
                output_sha256="",
                metadata={"key_type": key_material.key_type},
            )

    plugin = MockPlugin()
    DecryptionOrchestrator.register(plugin)

    try:
        # Empty data error
        with pytest.raises(ValueError, match="empty"):
            DecryptionOrchestrator.decrypt(b"", "key")

        # Key as string
        plain, meta = DecryptionOrchestrator.decrypt(b"dummy_encrypted_data", "deadbeef", format_hint="test_engine")
        assert plain == b"DECRYPTED_PAYLOAD"
        assert meta["operation_details"]["key_type"] == "hex_string"

        # Key as bytes
        plain, meta = DecryptionOrchestrator.decrypt(b"dummy_encrypted_data", b"\x01" * 32, format_hint="test_engine")
        assert meta["operation_details"]["key_type"] == "raw_bytes"

        # Key as KeyMaterial
        km = KeyMaterial(key_hex="1234", key_type="custom")
        plain, meta = DecryptionOrchestrator.decrypt(b"dummy_encrypted_data", km, format_hint="test_engine")
        assert meta["operation_details"]["key_type"] == "custom"

        # Invalid key type
        with pytest.raises(ValueError, match="Invalid key material"):
            DecryptionOrchestrator.decrypt(b"dummy_encrypted_data", 12345, format_hint="test_engine")  # type: ignore

    finally:
        DecryptionOrchestrator.unregister("test_engine")

