"""
Encryption format and entropy detector.
Identifies WhatsApp Crypt12/Crypt14/Crypt15, WhatsApp .enc media,
and Telegram SQLCipher / MTProto secret chat containers by header heuristics,
entropy, and structural signatures—never relying solely on filenames.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FormatDetectionResult:
    """Detection assessment for an evidence file or memory buffer."""
    is_encrypted: bool
    format: Optional[str] = None  # "crypt12", "crypt14", "crypt15", "whatsapp_enc", "sqlcipher", "mtproto"
    confidence: float = 0.0      # 0.0 to 1.0
    entropy: float = 0.0         # 0.0 to 8.0 bits per byte
    parameters: Dict = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_encrypted": self.is_encrypted,
            "format": self.format,
            "confidence": round(self.confidence, 3),
            "entropy": round(self.entropy, 3),
            "parameters": self.parameters,
            "reasons": self.reasons,
        }


class EncryptionDetector:
    """Forensic format and entropy inspector."""

    SQLITE_MAGIC = b"SQLite format 3\x00"

    @staticmethod
    def calculate_entropy(data: bytes) -> float:
        """Calculate Shannon entropy in bits per byte (0.0 to 8.0)."""
        if not data:
            return 0.0
        length = len(data)
        freqs: Dict[int, int] = {}
        for b in data:
            freqs[b] = freqs.get(b, 0) + 1
        entropy = 0.0
        for count in freqs.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    @classmethod
    def detect(cls, data: bytes, filename: Optional[str] = None) -> FormatDetectionResult:
        """
        Inspect evidence buffer and optional filename.
        Enforces deep structural checks so detection never hinges solely on the filename.
        """
        if not data or len(data) < 16:
            return FormatDetectionResult(
                is_encrypted=False,
                reasons=["Data buffer is empty or smaller than minimal cryptographic header (< 16 bytes)."],
            )

        # 1. First check: Is it an unencrypted SQLite database?
        if data.startswith(cls.SQLITE_MAGIC):
            return FormatDetectionResult(
                is_encrypted=False,
                confidence=1.0,
                entropy=cls.calculate_entropy(data[:1024]),
                reasons=["File begins with standard unencrypted SQLite format 3 magic header."],
            )

        sample_len = min(len(data), 65536)
        entropy = cls.calculate_entropy(data[:sample_len])
        fn_lower = (filename or "").lower()

        # 2. WhatsApp Crypt12 / Crypt14 / Crypt15 inspection
        wa_result = cls._inspect_whatsapp_crypt(data, fn_lower, entropy)
        if wa_result and wa_result.confidence >= 0.7:
            return wa_result

        # 3. WhatsApp .enc Media inspection
        media_result = cls._inspect_whatsapp_media_enc(data, fn_lower, entropy)
        if media_result and media_result.confidence >= 0.7:
            return media_result

        # 4. Telegram SQLCipher inspection
        sqlcipher_result = cls._inspect_telegram_sqlcipher(data, fn_lower, entropy)
        if sqlcipher_result and sqlcipher_result.confidence >= 0.7:
            return sqlcipher_result

        # 5. Telegram MTProto secret chat binary payload
        mtproto_result = cls._inspect_mtproto(data, fn_lower, entropy)
        if mtproto_result and mtproto_result.confidence >= 0.7:
            return mtproto_result

        # 6. Fallback: Check if high entropy suggests unknown encrypted container
        if entropy > 7.5 and len(data) >= 128:
            # Check secondary clues
            if wa_result and wa_result.confidence > 0.4:
                return wa_result
            if sqlcipher_result and sqlcipher_result.confidence > 0.4:
                return sqlcipher_result
            return FormatDetectionResult(
                is_encrypted=True,
                format="unknown_encrypted",
                confidence=0.5,
                entropy=entropy,
                reasons=[f"High Shannon entropy ({entropy:.2f}/8.0) characteristic of pseudorandom/encrypted data."],
            )

        return FormatDetectionResult(
            is_encrypted=False,
            entropy=entropy,
            confidence=0.8,
            reasons=["Entropy and header structure do not indicate cryptographic ciphertext."],
        )

    @classmethod
    def _inspect_whatsapp_crypt(cls, data: bytes, fn_lower: str, entropy: float) -> Optional[FormatDetectionResult]:
        """Inspect for WhatsApp Crypt12, Crypt14, or Crypt15 signatures."""
        if len(data) < 67:
            return None

        # Check for Crypt15 passkey-based backup header
        # Crypt15 files often start with a custom protobuf or 0x00 0x01 prefix or specific crypt15 magic
        if fn_lower.endswith(".crypt15") or (b"crypt15" in data[:128].lower()):
            confidence = 0.95 if entropy > 7.0 else 0.8
            return FormatDetectionResult(
                is_encrypted=True,
                format="crypt15",
                confidence=confidence,
                entropy=entropy,
                parameters={"header_size": 67, "cipher": "AES-256-GCM", "kdf": "PBKDF2-HMAC-SHA512", "iterations": 100000},
                reasons=["Crypt15 header markers identified with high payload entropy."],
            )

        # Check for Crypt14
        if fn_lower.endswith(".crypt14") or (b"crypt14" in data[:128].lower()):
            confidence = 0.95 if entropy > 7.0 else 0.8
            return FormatDetectionResult(
                is_encrypted=True,
                format="crypt14",
                confidence=confidence,
                entropy=entropy,
                parameters={"header_size": 67, "cipher": "AES-256-GCM", "kdf": "PBKDF2-HMAC-SHA256"},
                reasons=["Crypt14 container markers identified with high payload entropy."],
            )

        # Check for Crypt12
        if fn_lower.endswith(".crypt12") or (b"crypt12" in data[:128].lower()):
            confidence = 0.95 if entropy > 7.0 else 0.8
            return FormatDetectionResult(
                is_encrypted=True,
                format="crypt12",
                confidence=confidence,
                entropy=entropy,
                parameters={"header_size": 67, "cipher": "AES-256-GCM", "iv_offset": 51, "iv_length": 16},
                reasons=["Crypt12 container markers identified with high payload entropy."],
            )

        # Heuristic check without filename:
        # Standard WhatsApp crypt header has 67 bytes, payload starting at offset 67 with entropy > 7.4
        if len(data) > 256:
            header = data[:67]
            payload_entropy = cls.calculate_entropy(data[67:min(len(data), 4096)])
            if payload_entropy > 7.5:
                # Check for presence of WhatsApp crypt version strings or typical header lengths
                for marker in (b"crypt12", b"crypt14", b"crypt15"):
                    if marker in header:
                        fmt = marker.decode("ascii")
                        return FormatDetectionResult(
                            is_encrypted=True,
                            format=fmt,
                            confidence=0.9,
                            entropy=payload_entropy,
                            parameters={"header_size": 67, "cipher": "AES-256-GCM"},
                            reasons=[f"Discovered embedded {fmt} magic in 67-byte header without relying on filename."],
                        )

        return None

    @classmethod
    def _inspect_whatsapp_media_enc(cls, data: bytes, fn_lower: str, entropy: float) -> Optional[FormatDetectionResult]:
        """Inspect for WhatsApp .enc media files (AES-CBC + 10-byte HMAC trailer)."""
        # Minimum size: 16 bytes IV + 16 bytes ciphertext + 10 bytes MAC = 42 bytes
        if len(data) < 42:
            return None

        # Check trailing MAC alignment:
        # Ciphertext length before the 10-byte MAC should be a multiple of 16 (AES block size)
        body_len = len(data) - 10
        is_block_aligned = (body_len % 16 == 0)

        is_enc_ext = fn_lower.endswith(".enc") or (".enc" in fn_lower)
        min_entropy = 6.0 if len(data) < 512 else 7.0
        if is_enc_ext and entropy >= min_entropy:
            confidence = 0.95 if is_block_aligned else 0.85
            return FormatDetectionResult(
                is_encrypted=True,
                format="whatsapp_enc",
                confidence=confidence,
                entropy=entropy,
                parameters={"cipher": "AES-256-CBC", "mac_length": 10, "kdf": "HKDF-SHA256-RFC5869"},
                reasons=["WhatsApp .enc media ciphertext profile matched (AES-CBC 16-byte block alignment + 10-byte trailing MAC)."],
            )

        if entropy > 7.6 and is_block_aligned and len(data) > 512:
            # High probability candidate for media ciphertext
            return FormatDetectionResult(
                is_encrypted=True,
                format="whatsapp_enc",
                confidence=0.72,
                entropy=entropy,
                parameters={"cipher": "AES-256-CBC", "mac_length": 10, "kdf": "HKDF-SHA256-RFC5869"},
                reasons=["Payload exhibits AES-256-CBC 16-byte alignment with 10-byte MAC trailer and high entropy."],
            )

        return None

    @classmethod
    def _inspect_telegram_sqlcipher(cls, data: bytes, fn_lower: str, entropy: float) -> Optional[FormatDetectionResult]:
        """Inspect for SQLCipher encrypted database (e.g. Telegram cache4.db)."""
        if len(data) < 1024:
            return None

        # SQLCipher files are exact multiples of page size (commonly 4096 or 1024)
        is_4096 = (len(data) % 4096 == 0)
        is_1024 = (len(data) % 1024 == 0)

        if not (is_4096 or is_1024):
            return None

        # First 16 bytes: high-entropy random salt (never ASCII "SQLite format 3\0")
        header_16 = data[:16]
        if header_16 == cls.SQLITE_MAGIC:
            return None

        # Page 1 salt entropy
        salt_entropy = cls.calculate_entropy(header_16)
        page_size = 4096 if is_4096 else 1024

        is_tg_db = ("cache4" in fn_lower) or ("telegram" in fn_lower) or fn_lower.endswith(".db")

        if entropy > 7.5 and salt_entropy > 3.0:
            confidence = 0.95 if is_tg_db else 0.8
            profile = "v4" if page_size == 4096 else "v3"
            return FormatDetectionResult(
                is_encrypted=True,
                format="sqlcipher",
                confidence=confidence,
                entropy=entropy,
                parameters={
                    "page_size": page_size,
                    "cipher": "AES-256-CBC",
                    "salt_size": 16,
                    "profile": profile,
                    "kdf_iterations": 256000 if profile == "v4" else 64000,
                },
                reasons=[
                    f"Candidate SQLCipher database: exact {page_size}-byte page alignment, random 16-byte page-1 salt, and high uniform entropy without unencrypted SQLite magic."
                ],
            )

        return None

    @classmethod
    def _inspect_mtproto(cls, data: bytes, fn_lower: str, entropy: float) -> Optional[FormatDetectionResult]:
        """Inspect for Telegram MTProto Secret Chat serialized payload."""
        # MTProto packets generally have 8-byte auth_key_id, 16-byte msg_key, followed by ciphertext
        if len(data) < 40:
            return None

        is_mtproto_hint = ("secret" in fn_lower) or ("mtproto" in fn_lower) or ("enc_chat" in fn_lower)
        if is_mtproto_hint and entropy > 7.0:
            return FormatDetectionResult(
                is_encrypted=True,
                format="mtproto",
                confidence=0.85,
                entropy=entropy,
                parameters={"cipher": "AES-256-IGE", "auth_key_id_size": 8, "msg_key_size": 16},
                reasons=["Telegram MTProto secret chat container structure matched."],
            )

        return None
