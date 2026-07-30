"""WhatsApp media reference extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_media_references(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract media references from WhatsApp messages.
    Returns a list of dictionaries with media reference info.
    Each dict contains:
        - evidence_id
        - message_id (from messages table)
        - media_path (the media_url or similar from DB)
        - media_type (mime type from DB)
        - message_type (derived from media_type: image, video, audio, document)
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Try to get messages that have media
        cursor.execute("""
            SELECT
                msg.key_id AS message_id,
                msg.media_url AS media_path,
                msg.media_mime_type AS media_type
            FROM messages msg
            WHERE msg.media_url IS NOT NULL AND msg.media_mime_type IS NOT NULL
        """)
        rows = cursor.fetchall()
        media_refs = []
        for row in rows:
            # Determine message type from media_mime_type
            message_type = None
            if row["media_type"]:
                mime = row["media_type"].lower()
                if mime.startswith("image/"):
                    message_type = "image"
                elif mime.startswith("video/"):
                    message_type = "video"
                elif mime.startswith("audio/"):
                    message_type = "audio"
                else:
                    message_type = "document"
            media_ref = {
                "evidence_id": evidence_id,
                "message_id": str(row["message_id"]) if row["message_id"] is not None else "",
                "media_path": row["media_path"] if row["media_path"] is not None else "",
                "media_type": row["media_type"] if row["media_type"] is not None else "",
                "message_type": message_type,
            }
            media_refs.append(media_ref)
        conn.close()
        return media_refs
    except sqlite3.Error as e:
        import logging
        logging.getLogger(__name__).error(f"Parse error in extract_media_references: {e}")
        return []