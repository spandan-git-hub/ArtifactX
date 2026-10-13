"""Cryptographic hashing utilities for in-memory multi-algorithm integrity verification."""

import hashlib
from typing import Dict


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()


def compute_multi_hashes_bytes(data: bytes) -> Dict[str, str]:
    """Compute SHA-256, MD5, and SHA-1 hashes of raw byte data."""
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
    }
