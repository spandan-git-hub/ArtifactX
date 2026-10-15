"""Common forensic utilities, contracts, and R12 openers."""

from forensic.common.canonical import canonical_bytes, canonical_json
from forensic.common.contracts import FindingBase, Provenance, Strength
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.common.sqlite_open import HostileDatabaseError, open_sqlite_ro, quote_ident

__all__ = [
    "canonical_bytes",
    "canonical_json",
    "FindingBase",
    "Provenance",
    "Strength",
    "deterministic_finding_id",
    "sha256_hex",
    "HostileDatabaseError",
    "open_sqlite_ro",
    "quote_ident",
]
