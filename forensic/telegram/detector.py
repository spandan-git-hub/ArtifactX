"""Telegram database detection."""

import sqlite3
from pathlib import Path
from typing import BinaryIO, Union

from forensic.common.sqlite import open_sqlite


def is_telegram_database(db_source: Union[Path, str, bytes, BinaryIO]) -> bool:
    """Check if the given source is a Telegram SQLite database.
    Accepts memory bytes, streams, or filesystem paths.
    Looks for known tables: sqlite_master tables.
    """
    if isinstance(db_source, (str, Path)):
        p = Path(db_source)
        if not p.exists() or not p.is_file():
            return False
    try:
        conn = open_sqlite(db_source)
        cursor = conn.cursor()
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        # Telegram database typically has these tables:
        # messages, chats, users, etc.
        required_tables = {"messages", "chats", "users"}
        # If at least two of the known tables exist, consider it a Telegram DB
        return len(tables.intersection(required_tables)) >= 2
    except Exception:
        return False