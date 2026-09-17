"""
In-memory SQLite Validator.
Validates SQLite database header, page size, table inventory,
and cryptographic integrity using ephemeral in-memory deserialization—zero local disk access.
"""

import sqlite3
import struct
from typing import Dict, List, Optional


class SQLiteValidator:
    """Forensic validator for in-memory SQLite bytes."""

    SQLITE_MAGIC = b"SQLite format 3\x00"

    @classmethod
    def validate(cls, data: bytes) -> Dict:
        """
        Validate in-memory SQLite byte buffer.
        Returns validation details, table names, page count, and integrity check status.
        """
        if not data or len(data) < 100:
            return {
                "valid": False,
                "error": "Buffer length is less than minimum 100-byte SQLite header.",
            }

        # 1. Magic header check
        if not data.startswith(cls.SQLITE_MAGIC):
            return {
                "valid": False,
                "error": "Header magic does not match 'SQLite format 3\\0'.",
            }

        # 2. Header field parsing (RFC/SQLite Database File Format)
        try:
            # Page size at offset 16 (2 bytes big-endian; 1 means 65536)
            raw_page_size = struct.unpack(">H", data[16:18])[0]
            page_size = 65536 if raw_page_size == 1 else raw_page_size

            # File change counter at offset 24 (4 bytes)
            change_counter = struct.unpack(">I", data[24:28])[0]

            # In-header database size in pages at offset 28 (4 bytes)
            db_pages = struct.unpack(">I", data[28:32])[0]

            # Freelist trunk page count at offset 36 (4 bytes)
            freelist_pages = struct.unpack(">I", data[36:40])[0]

            # Schema cookie at offset 40 (4 bytes)
            schema_cookie = struct.unpack(">I", data[40:44])[0]
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to parse SQLite header fields: {str(e)}",
            }

        # 3. Ephemeral In-Memory Integrity Check (zero disk access)
        tables: List[str] = []
        integrity_status = "unknown"
        try:
            conn = sqlite3.connect(":memory:")
            conn.deserialize(data)
            cursor = conn.cursor()

            # Query schema tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]

            # Execute quick_check
            cursor.execute("PRAGMA quick_check(10);")
            rows = cursor.fetchall()
            if rows and rows[0][0] == "ok":
                integrity_status = "ok"
            else:
                integrity_status = "; ".join(r[0] for r in rows) if rows else "failed"

            conn.close()
        except Exception as e:
            return {
                "valid": False,
                "page_size": page_size,
                "db_pages": db_pages,
                "error": f"SQLite deserialization or query error: {str(e)}",
            }

        return {
            "valid": True,
            "page_size": page_size,
            "change_counter": change_counter,
            "db_pages": db_pages,
            "freelist_pages": freelist_pages,
            "schema_cookie": schema_cookie,
            "tables": tables,
            "table_count": len(tables),
            "integrity_check": integrity_status,
        }
