"""Hashing utilities and deterministic finding ID generation (spec B7.0, R8, R11)."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Union

from forensic.common.canonical import canonical_bytes


def sha256_hex(data: Union[bytes, str]) -> str:
    """Compute standard lowercase SHA-256 hex string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def deterministic_finding_id(
    method: str,
    evidence_sha256: str,
    source_table: str,
    row_or_offset: Union[int, str, None],
    key_facts: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a 32-hex deterministic finding ID per R8 and B7.0:
    sha256(canonical(method, evidence_sha256, source_table, row_id/offset, key_facts))[:32]
    """
    payload = {
        "evidence_sha256": evidence_sha256,
        "key_facts": key_facts or {},
        "method": method,
        "row_or_offset": row_or_offset if row_or_offset is not None else 0,
        "source_table": source_table,
    }
    raw = canonical_bytes(payload)
    return hashlib.sha256(raw).hexdigest()[:32]
