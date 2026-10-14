"""
Forensic format and artifact detection engine (B5.4).

Implements signature-first format classification per spec 03_INGEST_INTEGRITY_AUDIT.md:
- Structural magic bytes first (SQLite, WAL, ZIP, media containers).
- SQLite in-memory introspection with PRAGMA query_only=ON, trusted_schema=OFF.
- WhatsApp Crypt12 / Crypt14 / Crypt15 structural verification (protobuf varint + tags).
- Extension lies detected and recorded in `conflicts`.
- Never executes SQL from evidence.
- Entropy used strictly as supporting signal; compressed containers excluded by magic first.
- Zero external framework dependencies (pure standard library).
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FormatDetection:
    """Format assessment result for an evidence file or memory buffer."""

    format: str
    confidence_basis: str
    evidence: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "confidence_basis": self.confidence_basis,
            "evidence": list(self.evidence),
            "conflicts": list(self.conflicts),
            "details": dict(self.details),
        }


def calculate_entropy(data: bytes, sample_limit: int = 65536) -> float:
    """Calculate Shannon entropy in bits per byte (0.0 to 8.0)."""
    if not data:
        return 0.0
    sample = data[:sample_limit]
    length = len(sample)
    freqs: Dict[int, int] = {}
    for b in sample:
        freqs[b] = freqs.get(b, 0) + 1
    entropy = 0.0
    for count in freqs.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _parse_varint(data: bytes, offset: int = 0) -> Tuple[Optional[int], int]:
    """Parse a Protobuf varint from data at offset."""
    res = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        res |= (b & 0x7F) << shift
        if not (b & 0x80):
            return res, offset
        shift += 7
        if shift > 35:
            return None, offset
    return None, offset


def _introspect_sqlite_tables(data: bytes) -> Optional[List[str]]:
    """Safely introspect table names from an unencrypted SQLite database in memory."""
    if len(data) < 100:
        return None
    try:
        # If WAL mode (bytes 18, 19 == 2), SQLite fails on in-memory deserialize looking for disk WAL.
        # For pure in-memory read-only schema table introspection, normalize bytes 18 and 19 to 1.
        data_to_open = data
        if data[18] == 2 or data[19] == 2:
            buf = bytearray(data[:100])
            buf[18] = 1
            buf[19] = 1
            data_to_open = bytes(buf) + data[100:]

        conn = sqlite3.connect(":memory:")
        conn.deserialize(data_to_open)
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA trusted_schema = OFF")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception:
        return None


def detect_format(data: bytes, filename: Optional[str] = None) -> FormatDetection:
    """
    Classify evidence payload format using deterministic structural signatures.
    Handles filename extension lies, malformed headers, and high-entropy payloads.
    """
    filename_str = filename or ""
    fn_lower = Path(filename_str).name.lower()
    ext_lower = Path(filename_str).suffix.lower()

    # 1. Empty buffer check
    if len(data) == 0:
        conflicts = []
        if ext_lower in {".crypt14", ".crypt15", ".crypt12", ".db", ".sqlite", ".zip"}:
            conflicts.append(f"Filename declared {ext_lower} extension but file is 0 bytes (empty)")
        return FormatDetection(
            format="EMPTY_FILE",
            confidence_basis="empty_buffer",
            evidence=["Payload length is 0 bytes."],
            conflicts=conflicts,
            details={"size_bytes": 0},
        )

    entropy = calculate_entropy(data)
    evidence_items: List[str] = []
    conflict_items: List[str] = []

    # 2. SQLite format 3 check
    if data.startswith(b"SQLite format 3\x00"):
        evidence_items.append("Starts with standard 'SQLite format 3\\0' 16-byte magic header.")
        if ext_lower in {".crypt12", ".crypt14", ".crypt15"}:
            conflict_items.append(
                f"Filename claims encrypted WhatsApp container ({ext_lower}) but payload is an unencrypted SQLite database."
            )

        tables = _introspect_sqlite_tables(data)
        if tables is not None:
            tbl_set = {t.lower() for t in tables}
            # WhatsApp modern msgstore check
            if {"message", "chat", "jid"}.issubset(tbl_set):
                evidence_items.append("Introspected WhatsApp modern schema tables: 'message', 'chat', 'jid'.")
                return FormatDetection(
                    format="WHATSAPP_MSGSTORE",
                    confidence_basis="sqlite_table_fingerprint",
                    evidence=evidence_items,
                    conflicts=conflict_items,
                    details={"tables": tables, "schema_variant": "modern"},
                )
            # WhatsApp legacy msgstore check
            if {"messages", "chat_list"}.issubset(tbl_set):
                evidence_items.append("Introspected WhatsApp legacy schema tables: 'messages', 'chat_list'.")
                return FormatDetection(
                    format="WHATSAPP_MSGSTORE",
                    confidence_basis="sqlite_table_fingerprint",
                    evidence=evidence_items,
                    conflicts=conflict_items,
                    details={"tables": tables, "schema_variant": "legacy"},
                )
            # WhatsApp legacy wa.db contact database check
            if "wa_contacts" in tbl_set:
                evidence_items.append("Introspected WhatsApp legacy contact table: 'wa_contacts'.")
                return FormatDetection(
                    format="WHATSAPP_WADB",
                    confidence_basis="sqlite_table_fingerprint",
                    evidence=evidence_items,
                    conflicts=conflict_items,
                    details={"tables": tables},
                )
            # Telegram cache4.db check
            if {"messages_v2", "dialogs", "users"}.issubset(tbl_set):
                evidence_items.append("Introspected Telegram Android cache4 schema tables: 'messages_v2', 'dialogs', 'users'.")
                return FormatDetection(
                    format="TELEGRAM_CACHE4",
                    confidence_basis="sqlite_table_fingerprint",
                    evidence=evidence_items,
                    conflicts=conflict_items,
                    details={"tables": tables},
                )

        return FormatDetection(
            format="SQLITE_PLAIN",
            confidence_basis="magic_bytes",
            evidence=evidence_items,
            conflicts=conflict_items,
            details={"tables": tables or []},
        )

    # 3. SQLite WAL check (magic: 0x377F0682 or 0x377F0683, big-endian or little-endian)
    if len(data) >= 32 and data[:4] in (
        b"\x37\x7f\x06\x82",
        b"\x37\x7f\x06\x83",
        b"\x82\x06\x7f\x37",
        b"\x83\x06\x7f\x37",
    ):
        return FormatDetection(
            format="SQLITE_WAL",
            confidence_basis="magic_bytes",
            evidence=["Starts with SQLite Write-Ahead Log (WAL) 32-bit magic header."],
            conflicts=[],
            details={"magic_hex": data[:4].hex()},
        )

    # 4. ZIP archive check (PK\x03\x04)
    if data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06") or data.startswith(b"PK\x07\x08"):
        return FormatDetection(
            format="ZIP",
            confidence_basis="magic_bytes",
            evidence=["Starts with standard PK zip container magic signature."],
            conflicts=[],
            details={"entropy": round(entropy, 3)},
        )

    # 5. Media format checks (magic-first)
    if data.startswith(b"\xff\xd8\xff"):
        return FormatDetection(format="IMAGE_JPEG", confidence_basis="magic_bytes", evidence=["JPEG SOI magic 0xFFD8FF."])
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return FormatDetection(format="IMAGE_PNG", confidence_basis="magic_bytes", evidence=["PNG magic 0x89504E470D0A1A0A."])
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return FormatDetection(format="IMAGE_GIF", confidence_basis="magic_bytes", evidence=["GIF magic header."])
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return FormatDetection(format="IMAGE_WEBP", confidence_basis="magic_bytes", evidence=["RIFF WEBP container header."])
    if data.startswith(b"BM"):
        return FormatDetection(format="IMAGE_BMP", confidence_basis="magic_bytes", evidence=["BMP magic header."])
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return FormatDetection(format="IMAGE_TIFF", confidence_basis="magic_bytes", evidence=["TIFF endianness magic."])

    if len(data) >= 12 and data[4:8] in (b"ftyp", b"moov"):
        return FormatDetection(format="VIDEO_MP4", confidence_basis="magic_bytes", evidence=["ISO Base Media File Format box."])
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return FormatDetection(format="VIDEO_MKV", confidence_basis="magic_bytes", evidence=["Matroska / WebM EBML header."])
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"AVI ":
        return FormatDetection(format="VIDEO_AVI", confidence_basis="magic_bytes", evidence=["RIFF AVI container header."])

    if data.startswith(b"OggS"):
        return FormatDetection(format="AUDIO_OGG", confidence_basis="magic_bytes", evidence=["Ogg container magic OggS."])
    if data.startswith(b"ID3") or (len(data) >= 2 and data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return FormatDetection(format="AUDIO_MP3", confidence_basis="magic_bytes", evidence=["MPEG audio / ID3 header."])
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return FormatDetection(format="AUDIO_WAV", confidence_basis="magic_bytes", evidence=["RIFF WAVE header."])

    # 6. WhatsApp Crypt14 & Crypt15 Protobuf Structural Inspection
    # Both Crypt14 and Crypt15 begin with a varint header length, followed by a protobuf BackupPrefix:
    # tag 1 (0x08) -> 0 for crypt14, 1 for crypt15.
    if len(data) >= 16:
        hdr_len, prefix_offset = _parse_varint(data, 0)
        if hdr_len is not None and 20 <= hdr_len <= 4096:
            prefix_bytes = data[prefix_offset : prefix_offset + min(hdr_len, len(data) - prefix_offset)]
            if len(prefix_bytes) >= 2:
                tag1 = prefix_bytes[:2]
                is_crypt14 = tag1 == b"\x08\x00"
                is_crypt15 = tag1 == b"\x08\x01"

                if is_crypt14 or is_crypt15:
                    target_fmt = "WHATSAPP_CRYPT14" if is_crypt14 else "WHATSAPP_CRYPT15"
                    expected_ext = ".crypt14" if is_crypt14 else ".crypt15"
                    ev = [
                        f"Protobuf BackupPrefix header matches {target_fmt} structure (declared header length: {hdr_len})."
                    ]
                    conflicts: List[str] = []

                    if ext_lower and ext_lower != expected_ext:
                        conflicts.append(
                            f"Filename extension {ext_lower} disagrees with detected container {expected_ext}."
                        )

                    # Check for header truncation
                    if len(data) < prefix_offset + hdr_len:
                        conflicts.append(
                            f"File truncated inside cryptographic header (file size {len(data)} < header end {prefix_offset + hdr_len})."
                        )
                    # Check for missing trailer (16-byte MD5)
                    elif len(data) < prefix_offset + hdr_len + 16:
                        conflicts.append(
                            f"File truncated: missing or incomplete 16-byte MD5 container trailer (file size {len(data)})."
                        )
                    else:
                        import hashlib
                        expected_md5 = hashlib.md5(data[:-16]).digest()
                        actual_md5 = data[-16:]
                        if expected_md5 != actual_md5:
                            conflicts.append(
                                "Trailing 16-byte MD5 container checksum mismatch: container payload is truncated or corrupted."
                            )

                    return FormatDetection(
                        format=target_fmt,
                        confidence_basis="protobuf_backup_prefix",
                        evidence=ev,
                        conflicts=conflicts,
                        details={
                            "header_length": hdr_len,
                            "prefix_offset": prefix_offset,
                            "entropy": round(entropy, 3),
                        },
                    )

    # 7. WhatsApp Crypt12 Check (Legacy 67-byte header)
    if len(data) >= 67:
        if ext_lower == ".crypt12" or b"crypt12" in data[:128].lower():
            if entropy > 7.0:
                return FormatDetection(
                    format="WHATSAPP_CRYPT12",
                    confidence_basis="crypt12_header_heuristic",
                    evidence=["Crypt12 container markers identified with high payload entropy (> 7.0)."],
                    conflicts=[],
                    details={"header_size": 67, "entropy": round(entropy, 3)},
                )

    # 8. Handling extension lies when header is invalid / corrupt
    if ext_lower in {".crypt14", ".crypt15"}:
        # Filename claims crypt14/crypt15, but structural protobuf verification failed
        conflicts = [
            f"Filename has {ext_lower} extension but data does not match WhatsApp {ext_lower.lstrip('.').upper()} protobuf header signature."
        ]
        if len(data) < 20:
            conflicts.append(f"File truncated before minimal cryptographic header length ({len(data)} < 20 bytes).")
            return FormatDetection(
                format="UNKNOWN",
                confidence_basis="truncated_corrupted_header",
                evidence=[f"Truncated file ({len(data)} bytes) with {ext_lower} extension."],
                conflicts=conflicts,
                details={"entropy": round(entropy, 3), "size_bytes": len(data)},
            )
        if entropy > 7.5:
            return FormatDetection(
                format="UNKNOWN_ENCRYPTED_KEY_REQUIRED",
                confidence_basis="high_entropy_unidentified",
                evidence=[
                    f"High Shannon entropy ({entropy:.2f}/8.0) characteristic of ciphertext, but header signature failed."
                ],
                conflicts=conflicts,
                details={"entropy": round(entropy, 3), "claimed_extension": ext_lower},
            )
        return FormatDetection(
            format="UNKNOWN",
            confidence_basis="invalid_header_signature",
            evidence=["Cryptographic header failed to validate."],
            conflicts=conflicts,
            details={"entropy": round(entropy, 3)},
        )

    # 9. Generic high entropy check (no known container magic matched)
    if entropy > 7.5 and len(data) >= 64:
        return FormatDetection(
            format="UNKNOWN_ENCRYPTED_KEY_REQUIRED",
            confidence_basis="high_entropy_unidentified",
            evidence=[
                f"High Shannon entropy ({entropy:.2f}/8.0) with no recognized container signature; key material required."
            ],
            conflicts=[],
            details={"entropy": round(entropy, 3)},
        )

    # 10. Fallback: UNKNOWN
    return FormatDetection(
        format="UNKNOWN",
        confidence_basis="unrecognized_structure",
        evidence=["No known file signature, magic bytes, or entropy pattern matched."],
        conflicts=[],
        details={"entropy": round(entropy, 3), "size_bytes": len(data)},
    )
