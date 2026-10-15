"""
Post-decryption validation pipeline for WhatsApp artifacts.
Strictly adheres to:
- master.md R4: Zero disk writes; pure in-memory SQLite introspection.
- master.md R7: No fake capability; honest validation reporting.
- master.md R12: Untrusted input hardening (PRAGMA query_only=ON, trusted_schema=OFF).
- spec 04_WHATSAPP_DECRYPTION.md §B6.4.
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from forensic.decryption.whatsapp.errors import (
    OutputFailedIntegrity,
    OutputNotSqlite,
    OutputNotWhatsapp,
)
from forensic.decryption.whatsapp.types import ValidationReport

SQLITE3_HEADER = b"SQLite format 3\x00"


def validate_decrypted_payload(
    plaintext_decompressed: bytes,
    gcm_auth_ok: bool = True,
    zlib_decompress_ok: bool = True,
    checksum_ok: Optional[bool] = None,
    enforce_whatsapp_schema: bool = False,
) -> ValidationReport:
    """
    Execute 5-step forensic post-decryption verification pipeline:
    1. GCM authentication check (passed as input from cipher verify).
    2. zlib decompression check (passed as input).
    3. First 16 bytes == 'SQLite format 3\\0'.
    4. sqlite3.deserialize() with PRAGMA query_only=ON, trusted_schema=OFF -> PRAGMA integrity_check == 'ok'.
    5. WhatsApp schema introspection (detects modern vs legacy schema families).
    """
    details: Dict[str, Any] = {
        "size_bytes": len(plaintext_decompressed),
        "sha256": hashlib.sha256(plaintext_decompressed).hexdigest(),
    }

    # Step 1 & 2: GCM & zlib
    if not gcm_auth_ok:
        return ValidationReport(
            gcm_auth_ok=False,
            zlib_decompress_ok=False,
            sqlite_header_ok=False,
            pragma_integrity_ok=False,
            whatsapp_schema_ok=False,
            checksum_ok=checksum_ok,
            details=details,
        )

    if not zlib_decompress_ok:
        return ValidationReport(
            gcm_auth_ok=True,
            zlib_decompress_ok=False,
            sqlite_header_ok=False,
            pragma_integrity_ok=False,
            whatsapp_schema_ok=False,
            checksum_ok=checksum_ok,
            details=details,
        )

    # Step 3: SQLite magic bytes header
    sqlite_header_ok = len(plaintext_decompressed) >= 16 and plaintext_decompressed[:16] == SQLITE3_HEADER
    if not sqlite_header_ok:
        report = ValidationReport(
            gcm_auth_ok=True,
            zlib_decompress_ok=True,
            sqlite_header_ok=False,
            pragma_integrity_ok=False,
            whatsapp_schema_ok=False,
            checksum_ok=checksum_ok,
            details=details,
        )
        if enforce_whatsapp_schema:
            raise OutputNotSqlite()
        return report

    # Step 4: In-memory PRAGMA integrity_check
    pragma_integrity_ok = False
    tables: List[str] = []
    schema_family: Optional[str] = None
    whatsapp_schema_ok = False

    try:
        # If WAL mode (bytes 18, 19 == 2), SQLite fails on in-memory deserialize looking for disk WAL.
        # For in-memory validation, normalize header bytes 18 & 19 to 1.
        data_to_open = plaintext_decompressed
        if len(plaintext_decompressed) >= 100 and (plaintext_decompressed[18] == 2 or plaintext_decompressed[19] == 2):
            buf = bytearray(plaintext_decompressed[:100])
            buf[18] = 1
            buf[19] = 1
            data_to_open = bytes(buf) + plaintext_decompressed[100:]

        conn = sqlite3.connect(":memory:")
        try:
            conn.deserialize(data_to_open)
            conn.execute("PRAGMA query_only = ON")
            conn.execute("PRAGMA trusted_schema = OFF")

            cursor = conn.execute("PRAGMA integrity_check")
            integrity_rows = [r[0] for r in cursor.fetchall()]
            pragma_integrity_ok = (len(integrity_rows) == 1 and integrity_rows[0].lower() == "ok")
            details["integrity_check"] = integrity_rows

            # Step 5: Introspect tables
            table_cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in table_cursor.fetchall()]
            details["tables"] = tables
            table_set = set(tables)

            if "message" in table_set and ("chat" in table_set or "jid" in table_set):
                whatsapp_schema_ok = True
                schema_family = "modern"
            elif "messages" in table_set:
                whatsapp_schema_ok = True
                schema_family = "legacy"
            elif "wa_contacts" in table_set:
                whatsapp_schema_ok = True
                schema_family = "contacts"
            else:
                whatsapp_schema_ok = False
                schema_family = None
        finally:
            conn.close()

    except Exception as exc:
        details["sqlite_error"] = str(exc)
        pragma_integrity_ok = False
        whatsapp_schema_ok = False

    details["schema_family"] = schema_family
    report = ValidationReport(
        gcm_auth_ok=True,
        zlib_decompress_ok=True,
        sqlite_header_ok=True,
        pragma_integrity_ok=pragma_integrity_ok,
        whatsapp_schema_ok=whatsapp_schema_ok,
        checksum_ok=checksum_ok,
        schema_family=schema_family,
        details=details,
    )

    if enforce_whatsapp_schema:
        if not pragma_integrity_ok:
            raise OutputFailedIntegrity(details.get("sqlite_error") or "PRAGMA integrity_check != ok")
        if not whatsapp_schema_ok:
            raise OutputNotWhatsapp("Decrypted SQLite database does not contain WhatsApp message/chat tables.")

    return report
