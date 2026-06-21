"""Telegram database detection."""

import sqlite3
from pathlib import Path


def is_telegram_database(file_path: Path) -> bool:
    """Check if the given file is a Telegram SQLite database.
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
        # Telegram database typically has these tables:
        # messages, chats, users, etc.
        # We'll check for a combination of known tables.
        required_tables = {"messages", "chats", "users"}
        # If at least two of the known tables exist, consider it a Telegram DB
        return len(tables.intersection(required_tables)) >= 2
    except sqlite3.Error:
        return False