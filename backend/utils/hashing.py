"""Cryptographic hashing utilities for in-memory multi-algorithm integrity verification (B5.1).

Computes SHA-256 (primary), SHA-512, SHA-1, and MD5 in one single incremental pass.
MD5 and SHA-1 are legacy-compat only and labelled as such.
"""

from __future__ import annotations

import hashlib
from typing import Dict


class IncrementalHasher:
    """Incremental multi-hash accumulator for streaming evidence."""

    def __init__(self) -> None:
        self._sha256 = hashlib.sha256()
        self._sha512 = hashlib.sha512()
        self._sha1 = hashlib.sha1()
        self._md5 = hashlib.md5()
        self._total_bytes = 0

    def update(self, chunk: bytes) -> None:
        """Feed bytes into all digest accumulators simultaneously."""
        self._sha256.update(chunk)
        self._sha512.update(chunk)
        self._sha1.update(chunk)
        self._md5.update(chunk)
        self._total_bytes += len(chunk)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def hexdigests(self) -> Dict[str, str]:
        """Return hexadecimal digests for all algorithms."""
        return {
            "sha256": self._sha256.hexdigest(),
            "sha512": self._sha512.hexdigest(),
            "sha1": self._sha1.hexdigest(),
            "md5": self._md5.hexdigest(),
        }


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()


def compute_multi_hashes_bytes(data: bytes) -> Dict[str, str]:
    """Compute SHA-256, SHA-512, MD5, and SHA-1 hashes of raw byte data in a single pass."""
    hasher = IncrementalHasher()
    hasher.update(data)
    return hasher.hexdigests()
