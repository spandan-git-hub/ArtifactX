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
        # WhatsApp msgstore.db typically has these tables:
        # chats, messages, wa_contacts, etc.
        # We'll check for a combination of known tables.
        required_tables = {"messages", "wa_contacts", "chats"}
        # If at least one of the known tables exists, consider it a WhatsApp DB
        # (more robust: check for multiple)
        return len(tables.intersection(required_tables)) >= 2
    except sqlite3.Error:
        return False