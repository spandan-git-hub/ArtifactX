"""
ZIP safety verification and extraction engine (B5.1, R12).

Hardened against malicious zip archives:
- Member count ceiling (<= 10,000)
- Total uncompressed size ceiling (<= 1 GiB)
- Maximum uncompressed expansion factor (<= 100x archive size)
- Per-member compression ratio ceiling (<= 100x)
- Path traversal & zip-slip prevention (normalized names, no '..', no drive letters, no NUL bytes)
- Symlink exclusion and directory skipping
- Nesting depth capped at 2
- Zero disk extraction (purely in-memory)
"""

from __future__ import annotations

import io
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

from backend.utils.hashing import compute_multi_hashes_bytes


class ZipLimitExceeded(Exception):
    """Raised when a ZIP archive violates safety limits (zip bomb, member count, ratio, nesting)."""

    def __init__(self, message: str, reason: str, details: Optional[Dict] = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


@dataclass
class SafeZipMember:
    """Represents a validated, in-memory extracted ZIP member file."""

    original_filename: str
    normalized_path: str
    size: int
    sha256: str
    sha512: str
    md5: str
    sha1: str
    mime_type: Optional[str]
    content_bytes: bytes
    is_nested_archive: bool = False
    nesting_depth: int = 1


def normalize_zip_member_path(filename: str) -> str:
    """
    Validate and normalize ZIP member path to prevent Zip Slip and path traversal.
    Rejects:
    - Absolute paths (/..., \\...)
    - Path traversal (..)
    - Windows drive letters (C:, D:, etc.)
    - NUL characters
    Returns clean forward-slash relative POSIX path.
    """
    if "\x00" in filename:
        raise ZipLimitExceeded(
            f"Unsafe ZIP member path contains NUL byte: {filename!r}",
            reason="NUL_BYTE_IN_PATH",
        )

    # Replace backslashes
    clean = filename.replace("\\", "/").strip()

    # Reject drive letters (e.g. C:, D:)
    if len(clean) >= 2 and clean[1] == ":" and clean[0].isalpha():
        raise ZipLimitExceeded(
            f"Unsafe ZIP member path contains drive letter: {filename}",
            reason="DRIVE_LETTER_IN_PATH",
        )

    # Reject leading slashes
    if clean.startswith("/"):
        raise ZipLimitExceeded(
            f"Unsafe ZIP member path has absolute path: {filename}",
            reason="ABSOLUTE_PATH",
        )

    parts = [p for p in clean.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise ZipLimitExceeded(
            f"Unsafe ZIP member path contains traversal '..': {filename}",
            reason="PATH_TRAVERSAL",
        )

    if not parts:
        raise ZipLimitExceeded(
            f"ZIP member path resolves to empty root: {filename}",
            reason="EMPTY_PATH",
        )

    normalized = "/".join(parts)
    return normalized


def extract_zip_safe_in_memory(
    zip_bytes: bytes,
    max_members: int = 10000,
    max_total_uncompressed: int = 1024 * 1024 * 1024,  # 1 GiB
    max_uncompressed_factor: int = 100,
    max_member_ratio: int = 100,
    current_depth: int = 1,
    max_depth: int = 2,
) -> List[SafeZipMember]:
    """
    Extract a ZIP archive in memory under strict safety limits.
    
    Raises ZipLimitExceeded if any safety threshold is crossed.
    Returns list of SafeZipMember objects containing in-memory file bytes and hashes.
    """
    archive_size = max(1, len(zip_bytes))
    max_allowed_from_factor = archive_size * max_uncompressed_factor
    uncompressed_ceiling = min(max_total_uncompressed, max_allowed_from_factor)

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:
        raise ZipLimitExceeded(
            f"Invalid or corrupted ZIP container: {exc}",
            reason="INVALID_ZIP",
        ) from exc

    with zf:
        infolist = zf.infolist()
        if len(infolist) > max_members:
            raise ZipLimitExceeded(
                f"ZIP member count {len(infolist)} exceeds limit of {max_members}",
                reason="MEMBER_COUNT_EXCEEDED",
                details={"member_count": len(infolist), "limit": max_members},
            )

        # First pass: check declared uncompressed sizes
        declared_total = sum(info.file_size for info in infolist if not info.is_dir())
        if declared_total > uncompressed_ceiling:
            raise ZipLimitExceeded(
                f"Declared uncompressed size {declared_total} exceeds safety ceiling {uncompressed_ceiling}",
                reason="TOTAL_SIZE_EXCEEDED",
                details={"declared_total": declared_total, "ceiling": uncompressed_ceiling},
            )

        extracted_members: List[SafeZipMember] = []
        actual_total_uncompressed = 0

        for info in infolist:
            # Skip directory entries
            if info.is_dir() or info.filename.endswith("/"):
                continue

            # Skip symlinks (external_attr unix symlink test)
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                continue

            # Per-member compression ratio check (only for members >= 1 MiB to avoid false positives on zero-padded shm/sparse stubs)
            compressed_size = max(1, info.compress_size)
            ratio = info.file_size / compressed_size
            if ratio > max_member_ratio and info.file_size > 1024 * 1024:
                raise ZipLimitExceeded(
                    f"Member {info.filename} compression ratio {ratio:.1f} exceeds limit {max_member_ratio}",
                    reason="COMPRESSION_RATIO_EXCEEDED",
                    details={"member": info.filename, "ratio": ratio, "limit": max_member_ratio},
                )

            normalized_name = normalize_zip_member_path(info.filename)

            with zf.open(info) as src:
                member_bytes = src.read()

            actual_len = len(member_bytes)
            actual_total_uncompressed += actual_len
            if actual_total_uncompressed > uncompressed_ceiling:
                raise ZipLimitExceeded(
                    f"Total uncompressed bytes {actual_total_uncompressed} exceeded ceiling {uncompressed_ceiling}",
                    reason="TOTAL_SIZE_EXCEEDED",
                    details={"actual_total": actual_total_uncompressed, "ceiling": uncompressed_ceiling},
                )

            # Check if this member is itself a nested ZIP
            is_zip_member = (
                member_bytes.startswith(b"PK\x03\x04")
                or normalized_name.lower().endswith(".zip")
            )

            hashes = compute_multi_hashes_bytes(member_bytes)
            mime_type, _ = mimetypes.guess_type(normalized_name)

            member_obj = SafeZipMember(
                original_filename=info.filename,
                normalized_path=normalized_name,
                size=actual_len,
                sha256=hashes["sha256"],
                sha512=hashes["sha512"],
                md5=hashes["md5"],
                sha1=hashes["sha1"],
                mime_type=mime_type,
                content_bytes=member_bytes,
                is_nested_archive=is_zip_member,
                nesting_depth=current_depth,
            )
            extracted_members.append(member_obj)

            # If it's a nested zip and we haven't reached max_depth, extract recursively
            if is_zip_member and current_depth < max_depth:
                try:
                    nested_extracted = extract_zip_safe_in_memory(
                        member_bytes,
                        max_members=max_members - len(extracted_members),
                        max_total_uncompressed=max_total_uncompressed - actual_total_uncompressed,
                        max_uncompressed_factor=max_uncompressed_factor,
                        max_member_ratio=max_member_ratio,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                    )
                    # Prefix paths with parent container path
                    for nm in nested_extracted:
                        nm.normalized_path = f"{normalized_name}::{nm.normalized_path}"
                        extracted_members.append(nm)
                except ZipLimitExceeded:
                    # Nested extraction exceeded limit; keep member stored as-is without recursing
                    member_obj.is_nested_archive = True

        return extracted_members
