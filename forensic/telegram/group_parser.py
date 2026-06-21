"""Telegram group/channel extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_groups(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram groups and channels from the database.
    Returns a list of dictionaries matching TelegramGroup model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # to access columns by name
        cursor = conn.cursor()
        # Try to get groups; adjust table and column names as needed
        # Common Telegram chats table: _id, chat_id, title, username, type
        cursor.execute("""
            SELECT
                c.chat_id AS group_id,
                c.title AS title,
                c.username AS username,
                c.type AS type
            FROM chats c
            WHERE c.type IN ('group', 'supergroup', 'channel')
        """)
        rows = cursor.fetchall()
        groups = []
        for row in rows:
            # Convert row to dict
            group = {
                "evidence_id": evidence_id,
                "group_id": int(row["group_id"]) if row["group_id"] is not None else 0,
                "title": row["title"] if row["title"] is not None else "",
                "username": row["username"] if row["username"] is not None else "",
                "type": row["type"] if row["type"] is not None else "",
            }
            groups.append(group)
        conn.close()
        return groups
    except sqlite3.Error as e:
        # Log error
        return []