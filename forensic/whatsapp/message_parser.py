"""WhatsApp message extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_messages(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract WhatsApp messages from the database.
    Returns a list of dictionaries matching WhatsAppMessage model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factor = sqlite3.Row  # to access columns by name
        cursor = conn.cursor()
        # Try to get messages; adjust table and column names as needed
        # Common WhatsApp msgstore.db schema:
        # messages table: _id, key_remote_jid, key_from_me, key_id, status, needs_push,
        #   data, timestamp, media_url, media_mime_type, media_size, latitude, longitude,
        #   thumb_image, duration, broadcast, etc.
        # We'll attempt a simple query.
        cursor.execute("""
            SELECT
                msg.key_id AS message_id,
                msg.key_remote_jid AS key_remote_jid,
                msg.key_from_me AS sender_jid,  -- Simplified: if from_me then sender is our number, else participant?
                CASE
                    WHEN msg.key_from_me = 1 THEN ?  -- Our number (we don't have it, use placeholder)
                    ELSE msg.key_remote_jid
                END AS participant_jid,
                msg.data AS body,
                msg.timestamp AS timestamp,
                msg.media_mime_type AS media_type,
                msg.media_url AS media_path,
                CASE
                    WHEN msg.media_url IS NOT NULL THEN
                        CASE
                            WHEN LOWER(msg.media_mime_type) LIKE 'image/%' THEN 'image'
                            WHEN LOWER(msg.media_mime_type) LIKE 'video/%' THEN 'video'
                            WHEN LOWER(msg.media_mime_type) LIKE 'audio/%' THEN 'audio'
                            ELSE 'document'
                        END
                    ELSE NULL
                END AS message_type,
                msg.status AS status
            FROM messages msg
        """, (evidence_id,))  # placeholder for our number
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            # Convert row to dict
            msg = {
                "evidence_id": evidence_id,
                "message_id": str(row["message_id"]) if row["message_id"] is not None else "",
                "key_remote_jid": str(row["key_remote_jid"]) if row["key_remote_jid"] is not None else "",
                "sender_jid": str(row["sender_jid"]) if row["sender_jid"] is not None else "",
                "participant_jid": str(row["participant_jid"]) if row["participant_jid"] is not None else "",
                "body": row["body"] if row["body"] is not None else "",
                "timestamp": int(row["timestamp"]) if row["timestamp"] is not None else 0,
                "media_type": row["media_type"] if row["media_type"] is not None else None,
                "media_path": row["media_path"] if row["media_path"] is not None else None,
                "message_type": row["message_type"] if row["message_type"] is not None else None,
                "status": row["status"] if row["status"] is not None else "",
            }
            messages.append(msg)
        conn.close()
        return messages
    except sqlite3.Error as e:
        # Log error
        return []