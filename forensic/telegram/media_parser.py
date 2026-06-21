"""Telegram media reference extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_media_references(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract media references from Telegram messages.
    Returns a list of dictionaries with media reference info.
    Each dict contains:
        - evidence_id
        - message_id (from messages table)
        - media_path (reference to media file)
        - media_type (mime type or type)
        - message_type (derived: image, video, audio, document)
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Try to get messages that have media
        # We'll look for messages where media is not null
        cursor.execute("""
            SELECT
                m._id AS message_id,
                m.media AS media_path,
                CASE
                    WHEN LOWER(m.media) LIKE '%photo%' THEN 'image/jpeg'
                    WHEN LOWER(m.media) LIKE '%video%' THEN 'video/mp4'
                    WHEN LOWER(m.media) LIKE '%audio%' THEN 'audio/mpeg'
                    ELSE 'application/octet-stream'
                END AS media_type
            FROM messages m
            WHERE m.media IS NOT NULL
        """)
        rows = cursor.fetchall()
        media_refs = []
        for row in rows:
            # Determine message type from media_type
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
    except sqlite3.Error:
        return []