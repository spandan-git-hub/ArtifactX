"""
WhatsApp Decryption Subsystem.
Provides validated, independent decryptors for WhatsApp encrypted containers (B6).
Strictly adheres to master.md R4, R5, R7, R12, R15.
"""

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
from forensic.decryption.whatsapp.keys import WhatsAppKeyParser
from forensic.decryption.whatsapp.types import (
    DecryptionResult,
    KeyMaterial,
    ParsedHeader,
    ValidationReport,
)

__all__ = [
    "Crypt14Decryptor",
    "Crypt15Decryptor",
    "WhatsAppKeyParser",
    "KeyMaterial",
    "ParsedHeader",
    "ValidationReport",
    "DecryptionResult",
    "WhatsAppDecryptionError",
    "KeyRequired",
    "KeyInvalidFormat",
    "PassphraseNotSupported",
    "DecryptionAuthFailed",
    "TruncatedInput",
    "HeaderError",
    "UnsupportedVersion",
    "NotEncrypted",
    "DecompressionFailed",
    "OutputNotSqlite",
    "OutputFailedIntegrity",
    "OutputNotWhatsapp",
    "UntestedFormat",
]
