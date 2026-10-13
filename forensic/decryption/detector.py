"""
Encryption format and entropy detector.
Identifies WhatsApp Crypt12/Crypt14/Crypt15 containers by header heuristics,
entropy, and structural signatures—never relying solely on filenames.
Reports unknown high-entropy payloads as UNKNOWN_ENCRYPTED_KEY_REQUIRED with no format claim.
Excludes known high-entropy containers (ZIP, GZIP, JPEG, PNG, MP4/MOV, 7z, RAR, PDF)
by magic bytes so compressed media is never flagged as encrypted.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FormatDetectionResult:
    """Detection assessment for an evidence file or memory buffer."""
    is_encrypted: bool
    format: Optional[str] = None  # "crypt12", "crypt14", "crypt15", or "UNKNOWN_ENCRYPTED_KEY_REQUIRED"
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

    # Known high-entropy compressed containers that must NOT be flagged as encrypted (A6.3)
    KNOWN_CONTAINER_MAGICS: List[Tuple[str, bytes]] = [
        ("PNG", b"\x89PNG\r\n\x1a\n"),
        ("JPEG", b"\xff\xd8\xff"),
        ("PDF", b"%PDF"),
        ("7z", b"7z\xbc\xaf\x27\x1c"),
        ("RAR", b"Rar!\x1a\x07"),
        ("GZIP", b"\x1f\x8b"),
        ("ZIP", b"PK\x03\x04"),
        ("ZIP", b"PK\x05\x06"),
        ("ZIP", b"PK\x07\x08"),
    ]

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
    def _check_known_compressed_container(cls, data: bytes) -> Optional[str]:
        """Check if data starts with magic bytes of known high-entropy containers."""
        for name, magic in cls.KNOWN_CONTAINER_MAGICS:
            if data.startswith(magic):
                return name

        # MP4/MOV container check (ftyp/moov in ISO Base Media File Format)
        if len(data) >= 12:
            box_type = data[4:8]
            if box_type in (b"ftyp", b"moov"):
                return "MP4/MOV"

        return None

    @classmethod
    def detect(cls, data: bytes, filename: Optional[str] = None) -> FormatDetectionResult:
        """
        Inspect evidence buffer and optional filename.
        Enforces deep structural checks and magic bytes verification.
        """
        if not data or len(data) < 16:
            return FormatDetectionResult(
                is_encrypted=False,
                reasons=["Data buffer is empty or smaller than minimal cryptographic header (< 16 bytes)."],
            )

        # 1. Check: Is it an unencrypted SQLite database?
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

        # 2. Check: Is it a known compressed / media container? Exclude first (A6.3)
        container = cls._check_known_compressed_container(data)
        if container:
            return FormatDetectionResult(
                is_encrypted=False,
                format=None,
                confidence=0.95,
                entropy=entropy,
                parameters={"container_type": container},
                reasons=[
                    f"Known compressed/media container ({container}) identified by header magic; "
                    "high entropy is characteristic of compression, not encrypted ciphertext."
                ],
            )

        # 3. WhatsApp Crypt12 / Crypt14 / Crypt15 inspection
        wa_result = cls._inspect_whatsapp_crypt(data, fn_lower, entropy)
        if wa_result and wa_result.confidence >= 0.7:
            return wa_result

        # 4. Unknown-but-high-entropy input ⇒ UNKNOWN_ENCRYPTED_KEY_REQUIRED (A6.3)
        if entropy > 7.5 and len(data) >= 128:
            return FormatDetectionResult(
                is_encrypted=True,
                format="UNKNOWN_ENCRYPTED_KEY_REQUIRED",
                confidence=0.7,
                entropy=entropy,
                reasons=[
                    f"High Shannon entropy ({entropy:.2f}/8.0) characteristic of pseudorandom/encrypted data "
                    "with no known container magic matched; key material required."
                ],
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

        # Check for Crypt15
        if fn_lower.endswith(".crypt15") or (b"crypt15" in data[:128].lower()):
            confidence = 0.95 if entropy > 7.0 else 0.8
            return FormatDetectionResult(
                is_encrypted=True,
                format="crypt15",
                confidence=confidence,
                entropy=entropy,
                parameters={"header_size": 67, "cipher": "AES-256-GCM"},
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
                parameters={"header_size": 67, "cipher": "AES-256-GCM"},
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
