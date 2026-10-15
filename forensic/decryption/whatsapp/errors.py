"""
Typed exceptions for WhatsApp Decryption Subsystem.
Strictly adheres to master.md R5 (keys are radioactive: never echo key bytes,
key hex, or passphrases in exception messages or representations).
"""

from typing import Optional


class WhatsAppDecryptionError(Exception):
    """Base exception for WhatsApp forensic decryption failures."""

    def __init__(
        self,
        message: str,
        code: str = "DECRYPTION_ERROR",
        remediation: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.remediation = remediation or "Verify evidence integrity and key material."
        super().__init__(f"[{self.code}] {self.message}")


class KeyRequired(WhatsAppDecryptionError):
    """Recognized encrypted backup but no key was supplied."""

    def __init__(
        self,
        message: str = "Evidence file is encrypted; key material is required to decrypt.",
        remediation: str = "Provide WhatsApp key file or 64-character hex key obtained from device.",
    ):
        super().__init__(message=message, code="ENCRYPTED_KEY_REQUIRED", remediation=remediation)


class KeyInvalidFormat(WhatsAppDecryptionError):
    """Key file or hex string is malformed or invalid."""

    def __init__(
        self,
        message: str = "Key material format is invalid.",
        remediation: str = "Ensure key is a valid 158-byte/131-byte key file, 32-byte raw key, or 64-hex string.",
    ):
        super().__init__(message=message, code="KEY_INVALID_FORMAT", remediation=remediation)


class PassphraseNotSupported(WhatsAppDecryptionError):
    """User offered a passphrase for crypt15."""

    def __init__(
        self,
        message: str = (
            "crypt15 cannot be decrypted from a password offline; "
            "supply the 64-hex key or encrypted_backup.key obtained from the device."
        ),
        remediation: str = "Obtain the 64-digit hex key or encrypted_backup.key from the seized device.",
    ):
        super().__init__(message=message, code="PASSPHRASE_NOT_SUPPORTED", remediation=remediation)


class DecryptionAuthFailed(WhatsAppDecryptionError):
    """AES-GCM authentication tag mismatch."""

    def __init__(
        self,
        message: str = "Authentication failed: wrong key OR modified/corrupted data.",
        remediation: str = "Verify that the key corresponds to this backup and that the evidence file is not corrupted.",
    ):
        super().__init__(message=message, code="AUTH_FAILED", remediation=remediation)


class TruncatedInput(WhatsAppDecryptionError):
    """Input buffer is shorter than header/tag requirements."""

    def __init__(
        self,
        message: str = "Input buffer is truncated or smaller than expected container headers.",
        remediation: str = "Verify full evidence acquisition and transmission integrity.",
    ):
        super().__init__(message=message, code="TRUNCATED_INPUT", remediation=remediation)


class HeaderError(WhatsAppDecryptionError):
    """Container header structure is malformed or invalid."""

    def __init__(
        self,
        message: str = "WhatsApp backup container header is invalid or corrupt.",
        remediation: str = "Verify backup container format version and integrity.",
    ):
        super().__init__(message=message, code="UNSUPPORTED_VERSION", remediation=remediation)


class UnsupportedVersion(WhatsAppDecryptionError):
    """Container version or feature flags are unsupported."""

    def __init__(
        self,
        message: str = "Backup container version or features are not supported.",
        remediation: str = "Check backup container format version against supported specifications.",
    ):
        super().__init__(message=message, code="UNSUPPORTED_VERSION", remediation=remediation)


class NotEncrypted(WhatsAppDecryptionError):
    """Input is already a plaintext SQLite database."""

    def __init__(
        self,
        message: str = "Evidence is already plaintext SQLite; decryption is not required.",
        remediation: str = "Ingest directly through standard SQLite evidence ingestion pipeline.",
    ):
        super().__init__(message=message, code="NOT_ENCRYPTED", remediation=remediation)


class DecompressionFailed(WhatsAppDecryptionError):
    """Zlib decompression failed or exceeded safety memory limit."""

    def __init__(
        self,
        message: str = "Decompression failed or exceeded maximum uncompressed size cap.",
        remediation: str = "Check for payload corruption or adjust decompression memory limits.",
    ):
        super().__init__(message=message, code="DECOMPRESSION_FAILED", remediation=remediation)


class OutputNotSqlite(WhatsAppDecryptionError):
    """Decrypted bytes do not start with SQLite format 3 header."""

    def __init__(
        self,
        message: str = "Decrypted payload does not contain a valid SQLite database header.",
        remediation: str = "Verify backup type; payload may be a raw ZIP archive or corrupted stream.",
    ):
        super().__init__(message=message, code="OUTPUT_NOT_SQLITE", remediation=remediation)


class OutputFailedIntegrity(WhatsAppDecryptionError):
    """Decrypted SQLite database failed PRAGMA integrity_check."""

    def __init__(
        self,
        message: str = "Decrypted SQLite database failed integrity check.",
        remediation: str = "Database file is damaged or structurally inconsistent.",
    ):
        super().__init__(message=message, code="OUTPUT_FAILED_INTEGRITY", remediation=remediation)


class OutputNotWhatsapp(WhatsAppDecryptionError):
    """Decrypted database passed integrity check but lacks WhatsApp schema."""

    def __init__(
        self,
        message: str = "Decrypted SQLite database does not conform to WhatsApp schema.",
        remediation: str = "Verify that the decrypted container is a WhatsApp msgstore or wa database.",
    ):
        super().__init__(message=message, code="OUTPUT_NOT_WHATSAPP", remediation=remediation)


class UntestedFormat(WhatsAppDecryptionError):
    """Encountered format without verified test fixtures (e.g. crypt12)."""

    def __init__(
        self,
        message: str = "Format is untested/unsupported (e.g. crypt12 without verified fixture).",
        remediation: str = "Format support requires verified synthetic fixtures and differential parity tests.",
    ):
        super().__init__(message=message, code="UNTESTED_FORMAT", remediation=remediation)
