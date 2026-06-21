"""Telegram message extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_messages(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram messages from the database.
    Returns a list of dictionaries matching TelegramMessage model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # to access columns by name
        cursor = conn.cursor()
        # Try to get messages; adjust table and column names as needed
        # Common Telegram cache4.db schema:
        # messages table: _id, dialog_message_id, chat_id, from_id, date, media_ttl, action, etc.
        # We'll attempt a query that works for basic text messages.
        cursor.execute("""
            SELECT
                m._id AS message_id,
                m.chat_id AS dialog_id,
                m.from_id AS sender_id,
                m.message AS body,
                m.date AS timestamp,
                CASE
                    WHEN m.media IS NOT NULL THEN
                        CASE
                            WHEN LOWER(m.media) LIKE '%photo%' THEN 'image'
                            WHEN LOWER(m.media) LIKE '%video%' THEN 'video'
                            WHEN LOWER(m.media) LIKE '%audio%' THEN 'audio'
                            ELSE 'document'
                        END
                    ELSE NULL
                END AS media_type,
                NULL AS media_path,  // We'll need to map media to actual files later
                CASE
                    WHEN m.message IS NOT NULL THEN 'text'
                    WHEN m.media IS NOT NULL THEN 'media'
                    ELSE 'other'
                END AS message_type
            FROM messages m
        """)
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            # Convert row to dict
            msg = {
                "evidence_id": evidence_id,
                "message_id": str(row["message_id"]) if row["message_id"] is not None else "",
                "dialog_id": str(row["dialog_id"]) if row["dialog_id"] is not None else "",
                "sender_id": int(row["sender_id"]) if row["sender_id"] is not None else 0,
                "body": row["body"] if row["body"] is not None else "",
                "timestamp": int(row["timestamp"]) if row["timestamp"] is not None else 0,
                "media_type": row["media_type"] if row["media_type"] is not None else None,
                "media_path": row["media_path"] if row["media_path"] is not None else None,
                "message_type": row["message_type"] if row["message_type"] is not None else None,
            }
            messages.append(msg)
        conn.close()
        return messages
    except sqlite3.Error as e:
        # Log error
        return []