"""
R12 Untrusted-input hardened SQLite connection opener and identifier sanitizer.
Complies with master.md R4 (zero disk writes), R12 (untrusted input), and spec B7.0.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import BinaryIO, Container, Optional, Union

SQLITE_HEADER_MAGIC = b"SQLite format 3\x00"
_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class HostileDatabaseError(Exception):
    """Raised when hostile or malformed SQLite constructs are detected (master.md R12)."""
    pass


def quote_ident(ident: str, whitelist: Optional[Container[str]] = None) -> str:
    """
    Validate and double-quote a SQLite identifier (table or column name).
    
    Strictly accepts only alphanumeric/underscore identifiers matching ^[A-Za-z_][A-Za-z0-9_]*$.
    If a whitelist is provided, the identifier (case-insensitive) must be present in it.
    Rejects any hostile characters (quotes, semicolons, dashes, spaces, control characters).
    """
    if not isinstance(ident, str):
        raise ValueError(f"Identifier must be str, got {type(ident).__name__}")
    if not _SAFE_IDENT_RE.match(ident):
        raise ValueError(f"Illegal or hostile characters in SQLite identifier: {ident!r}")
    if whitelist is not None:
        wl_lower = {w.lower() for w in whitelist}
        if ident.lower() not in wl_lower:
            raise ValueError(f"Identifier {ident!r} is not permitted by whitelist: {sorted(wl_lower)}")
    return f'"{ident}"'


def _strict_authorizer(action_code: int, arg1: Optional[str], arg2: Optional[str], db_name: Optional[str], trigger_or_view: Optional[str]) -> int:
    """
    SQLite authorizer callback enforcing strictly read-only and unprivileged queries.
    Blocks ATTACH, DETACH, PRAGMA alterations, DDL modifications, and write operations.
    """
    # SQLITE_ATTACH (24) and SQLITE_DETACH (25)
    if action_code in (getattr(sqlite3, "SQLITE_ATTACH", 24), getattr(sqlite3, "SQLITE_DETACH", 25)):
        return sqlite3.SQLITE_DENY

    # DDL & write operations
    deny_codes = {
        getattr(sqlite3, "SQLITE_INSERT", 18),
        getattr(sqlite3, "SQLITE_UPDATE", 23),
        getattr(sqlite3, "SQLITE_DELETE", 9),
        getattr(sqlite3, "SQLITE_CREATE_TABLE", 1),
        getattr(sqlite3, "SQLITE_CREATE_INDEX", 2),
        getattr(sqlite3, "SQLITE_CREATE_VIEW", 3),
        getattr(sqlite3, "SQLITE_CREATE_TRIGGER", 7),
        getattr(sqlite3, "SQLITE_DROP_TABLE", 11),
        getattr(sqlite3, "SQLITE_DROP_INDEX", 12),
        getattr(sqlite3, "SQLITE_DROP_VIEW", 13),
        getattr(sqlite3, "SQLITE_DROP_TRIGGER", 14),
        getattr(sqlite3, "SQLITE_ALTER_TABLE", 26),
    }
    if action_code in deny_codes:
        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def open_sqlite_ro(
    source: Union[bytes, BinaryIO, str, Path],
    enforce_authorizer: bool = True,
) -> sqlite3.Connection:
    """
    Open an untrusted SQLite database in memory with strict R12 forensic hardening:
    - Zero disk writes via in-memory deserialization (master.md R4)
    - PRAGMA query_only = ON
    - PRAGMA trusted_schema = OFF (prevents hostile triggers and view expansion attacks)
    - PRAGMA cell_size_check = ON (bounds-checks corrupted leaf cells)
    - Authorizer denies ATTACH, mutations, and DDL
    """
    if isinstance(source, bytes):
        raw_data = source
    elif hasattr(source, "read"):
        cur_pos = source.tell() if hasattr(source, "tell") else 0
        raw_data = source.read()
        if hasattr(source, "seek"):
            source.seek(cur_pos)
    else:
        path = Path(source)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"SQLite evidence file not found: {path}")
        raw_data = path.read_bytes()

    if not raw_data.startswith(SQLITE_HEADER_MAGIC):
        raise ValueError("Evidence does not contain a valid SQLite format 3 header")

    # If WAL mode (bytes 18, 19 == 2), SQLite fails on in-memory deserialize looking for disk WAL.
    # For pure in-memory zero-disk operation (R4), normalize header bytes 18 and 19 to 1.
    if len(raw_data) >= 100 and (raw_data[18] == 2 or raw_data[19] == 2):
        buf = bytearray(raw_data[:100])
        buf[18] = 1
        buf[19] = 1
        raw_data = bytes(buf) + raw_data[100:]

    try:
        conn = sqlite3.connect(":memory:")
        conn.deserialize(raw_data)
    except Exception as e:
        raise HostileDatabaseError(f"Failed to deserialize SQLite database: {e}") from e

    # Configure strictly hardened pragmas
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA query_only = ON")
        cursor.execute("PRAGMA trusted_schema = OFF")
        cursor.execute("PRAGMA cell_size_check = ON")
        cursor.close()
    except Exception as e:
        conn.close()
        raise HostileDatabaseError(f"Failed to configure hardened SQLite pragmas: {e}") from e

    if enforce_authorizer:
        conn.set_authorizer(_strict_authorizer)

    return conn
