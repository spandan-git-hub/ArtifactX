"""WhatsApp media reference extraction."""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _tables(cursor: sqlite3.Cursor) -> set[str]:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0].lower() for row in cursor.fetchall()}


def _columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _first_existing(cols: set[str], candidates: list[str], default: str = "NULL") -> str:
    for column in candidates:
        if column in cols:
            return f"msg.{column}"
    return default


def _media_query(table: str, cols: set[str]) -> str:
    message_id = _first_existing(cols, ["key_id", "message_id", "_id", "id"], "msg.rowid")
    media_path = _first_existing(cols, ["media_url", "media_name", "file_path", "media_path"], "NULL")
    media_type = _first_existing(cols, ["media_mime_type", "mime_type"], "NULL")

    return f"""
        SELECT
            {message_id} AS message_id,
            {media_path} AS media_path,
            {media_type} AS media_type
        FROM {table} msg
        WHERE ({media_path} IS NOT NULL OR {media_type} IS NOT NULL)
    """


def extract_media_references(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract media references from WhatsApp messages.
    Returns a list of dictionaries with media reference info.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        table_names = _tables(cursor)

        target_table = None
        for candidate in ["messages", "message"]:
            if candidate in table_names:
                target_table = candidate
                break

        if not target_table:
            conn.close()
            return []

        cols = _columns(cursor, target_table)
        cursor.execute(_media_query(target_table, cols))
        rows = cursor.fetchall()
        media_refs = []
        for row in rows:
            m_path = str(row["media_path"]) if row["media_path"] is not None else ""
            m_type = str(row["media_type"]) if row["media_type"] is not None else ""
            if not m_path and not m_type:
                continue

            message_type = None
            if m_type:
                mime = m_type.lower()
                if mime.startswith("image/"):
                    message_type = "image"
                elif mime.startswith("video/"):
                    message_type = "video"
                elif mime.startswith("audio/"):
                    message_type = "audio"
                else:
                    message_type = "document"
            elif m_path:
                message_type = "media"

            media_ref = {
                "evidence_id": evidence_id,
                "message_id": str(row["message_id"]) if row["message_id"] is not None else "",
                "media_path": m_path,
                "media_type": m_type,
                "message_type": message_type,
            }
            media_refs.append(media_ref)
        conn.close()
        return media_refs
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_media_references: {e}")
        return []