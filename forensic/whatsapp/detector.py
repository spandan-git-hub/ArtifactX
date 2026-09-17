"""WhatsApp database detection."""

import sqlite3
from pathlib import Path
from typing import BinaryIO, Union

from forensic.common.sqlite import open_sqlite


def is_whatsapp_database(db_source: Union[Path, str, bytes, BinaryIO]) -> bool:
    """Check if the given source is a WhatsApp SQLite database.
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
        tables = {table.lower() for table in tables}

        legacy_tables = {"messages", "wa_contacts", "chats"}
        modern_tables = {"message", "chat", "jid"}

        if len(tables.intersection(legacy_tables)) >= 2:
            return True
        if "message" in tables and ("jid" in tables or "chat" in tables):
            return True
        if "messages" in tables and ("jid" in tables or "chat" in tables or "chats" in tables):
            return True
        if len(tables.intersection(modern_tables)) >= 2:
            return True
        return False
    except Exception:
        return False
