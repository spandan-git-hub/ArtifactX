"""Cryptographic hashing utilities for multi-algorithm integrity verification."""

import hashlib
from pathlib import Path
from typing import Dict, Union


def compute_sha256(filepath: Union[str, Path], chunk_size: int = 8192) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()


def compute_multi_hashes(filepath: Union[str, Path], chunk_size: int = 8192) -> Dict[str, str]:
    """Compute SHA-256, MD5, and SHA-1 hashes of a file in a single stream pass."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()

    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
            md5.update(chunk)
            sha1.update(chunk)

    return {
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
    }


def compute_multi_hashes_bytes(data: bytes) -> Dict[str, str]:
    """Compute SHA-256, MD5, and SHA-1 hashes of raw byte data."""
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
    }
