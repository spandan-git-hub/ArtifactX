"""
Cryptographic and forensic types for WhatsApp decryption.
Strictly adheres to master.md R5:
- Key material has redacted __repr__ and __str__
- __reduce__ raises RuntimeError to block pickle/serialization
- .fingerprint() returns first 8 hex of SHA-256
- Best-effort zeroing of in-memory key buffers
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, Optional


class KeyMaterial:
    """
    Forensic encapsulation of cryptographic key material.
    Ensures secret key bytes are never accidentally exposed via logging,
    string output, exception messages, or pickling.
    """

    def __init__(
        self,
        raw_key: Optional[bytes] = None,
        key_hex: Optional[str] = None,
        key_file_bytes: Optional[bytes] = None,
        key_type: str = "raw",
    ):
        self.key_type = key_type
        # Maintain internal key in mutable bytearray where possible
        if raw_key is not None:
            self._buffer = bytearray(raw_key)
        elif key_hex is not None:
            clean = key_hex.strip()
            try:
                self._buffer = bytearray(bytes.fromhex(clean))
            except ValueError:
                self._buffer = bytearray(clean.encode("utf-8"))
        elif key_file_bytes is not None:
            self._buffer = bytearray(key_file_bytes)
        else:
            self._buffer = bytearray()

    @property
    def raw_key(self) -> bytes:
        """Access underlying key bytes."""
        return bytes(self._buffer)

    @property
    def key_hex(self) -> str:
        """Access underlying key hex string."""
        return self._buffer.hex()

    @property
    def key_file_bytes(self) -> bytes:
        """Access raw key file bytes."""
        return bytes(self._buffer)

    def fingerprint(self) -> str:
        """
        Return judicial key fingerprint: first 8 hex chars of SHA-256 (R5).
        Safe for logging and audit trails.
        """
        if not self._buffer:
            return "empty"
        return hashlib.sha256(self._buffer).hexdigest()[:8]

    def zero(self) -> None:
        """
        Best-effort zeroing of secret key buffer in memory (R5).
        Note: CPython immutables/copies may remain in memory until GC.
        """
        for i in range(len(self._buffer)):
            self._buffer[i] = 0

    def __repr__(self) -> str:
        return f"<KeyMaterial type={self.key_type} fingerprint={self.fingerprint()} [SECRET REDACTED]>"

    def __str__(self) -> str:
        return self.__repr__()

    def __reduce__(self):
        """Disallow pickle serialization to avoid secret leakage (R5)."""
        raise RuntimeError("KeyMaterial cannot be pickled or serialized (master.md R5).")


@dataclass(frozen=True)
class ParsedHeader:
    """Parsed WhatsApp backup container header."""
    format_id: str
    header_size: int
    iv: bytes
    key_type: Optional[int] = None
    server_salt: Optional[bytes] = None
    google_id_salt: Optional[bytes] = None
    app_version: Optional[str] = None
    jid_suffix: Optional[str] = None
    raw_header: bytes = b""


@dataclass(frozen=True)
class ValidationReport:
    """Forensic verification report for decrypted payload."""
    gcm_auth_ok: bool
    zlib_decompress_ok: bool
    sqlite_header_ok: bool
    pragma_integrity_ok: bool
    whatsapp_schema_ok: bool
    checksum_ok: Optional[bool] = None
    schema_family: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid_sqlite(self) -> bool:
        """True if steps 1-4 pass (GCM, zlib, SQLite header, PRAGMA integrity)."""
        return (
            self.gcm_auth_ok
            and self.zlib_decompress_ok
            and self.sqlite_header_ok
            and self.pragma_integrity_ok
        )


@dataclass(frozen=True)
class DecryptionResult:
    """Result of an in-memory decryption operation."""
    plaintext: bytes
    format_id: str
    output_sha256: str
    validation_report: Optional[ValidationReport] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
