"""
ArtifactX Forensic Decryption Subsystem.
Provides plugin-based decryption orchestrator and honest format/entropy detection.
Telegram secret chats/SQLCipher and unvalidated decryptors demoted per Section A6 / DEC-004 / DEC-005.
"""

from forensic.decryption.detector import EncryptionDetector, FormatDetectionResult
from forensic.decryption.orchestrator import (
    DecryptionOrchestrator,
    Decryptor,
    DecryptorNotAvailableError,
    KeyMaterial,
    DecryptionResult,
)

__all__ = [
    "EncryptionDetector",
    "FormatDetectionResult",
    "DecryptionOrchestrator",
    "Decryptor",
    "DecryptorNotAvailableError",
    "KeyMaterial",
    "DecryptionResult",
]
