"""Forensic SQLite in-memory and zero-disk connection abstractions."""

import io
import sqlite3
from pathlib import Path
from typing import BinaryIO, Union

SQLITE_HEADER_MAGIC = b"SQLite format 3\x00"


def open_sqlite(
    source: Union[bytes, BinaryIO, str, Path],
    read_only: bool = True,
) -> sqlite3.Connection:
    """
    Open a SQLite database connection from memory bytes, stream, or file path.
    Supports in-memory zero-disk operation via sqlite3.Connection.deserialize().
    """
    if isinstance(source, bytes):
        conn = sqlite3.connect(":memory:")
        conn.deserialize(source)
        return conn

    if hasattr(source, "read"):
        # BinaryIO or BytesIO
        current_pos = source.tell() if hasattr(source, "tell") else 0
        data = source.read()
        if hasattr(source, "seek"):
            source.seek(current_pos)
        conn = sqlite3.connect(":memory:")
        conn.deserialize(data)
        return conn

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"SQLite file not found: {path}")

    if read_only:
        uri = f"file:{path.resolve()}?mode=ro"
        return sqlite3.connect(uri, uri=True)
    return sqlite3.connect(str(path))


def is_sqlite_database(source: Union[bytes, BinaryIO, str, Path]) -> bool:
    """Check if the source starts with the SQLite magic header and is a valid SQLite database."""
    try:
        if isinstance(source, bytes):
            if not source.startswith(SQLITE_HEADER_MAGIC):
                return False
            conn = open_sqlite(source)
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            conn.close()
            return True

        if hasattr(source, "read"):
            current_pos = source.tell() if hasattr(source, "tell") else 0
            header = source.read(16)
            if hasattr(source, "seek"):
                source.seek(current_pos)
            if header != SQLITE_HEADER_MAGIC:
                return False
            conn = open_sqlite(source)
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            conn.close()
            return True

        path = Path(source)
        if not path.exists() or not path.is_file():
            return False
        with open(path, "rb") as f:
            header = f.read(16)
        if header != SQLITE_HEADER_MAGIC:
            return False
        conn = open_sqlite(path)
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False
