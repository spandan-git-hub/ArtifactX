"""WhatsApp database detection."""

import sqlite3
from pathlib import Path


def is_whatsapp_database(file_path: Path) -> bool:
    """Check if the given file is a WhatsApp SQLite database.
    Looks for known tables: sqlite_master tables.
    """
    if not file_path.exists() or not file_path.is_file():
        return False
    try:
        conn = sqlite3.connect(str(file_path))
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
    except sqlite3.Error:
        return False
