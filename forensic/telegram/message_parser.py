"""Telegram message extraction."""

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
            return f"m.{column}"
    return default


def _message_query(table: str, cols: set[str]) -> str:
    message_id = _first_existing(cols, ["_id", "id", "mid", "dialog_message_id"], "m.rowid")
    dialog_id = _first_existing(cols, ["chat_id", "dialog_id", "peer_id"], "0")
    sender_id = _first_existing(cols, ["from_id", "sender_id", "user_id"], "0")
    body = _first_existing(cols, ["message", "body", "text"], "''")
    timestamp = _first_existing(cols, ["date", "timestamp", "created_at"], "0")
    media = _first_existing(cols, ["media", "media_type", "type"], "NULL")
    media_path = _first_existing(cols, ["media_path", "file_path", "path"], "NULL")

    return f"""
        SELECT
            {message_id} AS message_id,
            {dialog_id} AS dialog_id,
            {sender_id} AS sender_id,
            {body} AS body,
            {timestamp} AS timestamp,
            {media} AS media,
            {media_path} AS media_path
        FROM {table} m
    """


def extract_messages(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram messages from the database.
    Returns a list of dictionaries matching TelegramMessage model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        table_names = _tables(cursor)
        target_table = None
        for candidate in ["messages", "message", "messages_v2"]:
            if candidate in table_names:
                target_table = candidate
                break

        if not target_table:
            conn.close()
            return []

        cols = _columns(cursor, target_table)
        cursor.execute(_message_query(target_table, cols))
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            raw_media = str(row["media"]) if row["media"] is not None else ""
            media_type = None
            if raw_media:
                lower_m = raw_media.lower()
                if "photo" in lower_m or lower_m.startswith("image/"):
                    media_type = "image"
                elif "video" in lower_m or lower_m.startswith("video/"):
                    media_type = "video"
                elif "audio" in lower_m or lower_m.startswith("audio/"):
                    media_type = "audio"
                else:
                    media_type = "document"

            body_str = str(row["body"]) if row["body"] is not None else ""
            m_path_str = str(row["media_path"]) if row["media_path"] is not None else None

            if body_str:
                msg_type = "text"
            elif media_type or m_path_str:
                msg_type = "media"
            else:
                msg_type = "other"

            sender_raw = row["sender_id"]
            sender_id_int = 0
            if sender_raw is not None:
                try:
                    sender_id_int = int(sender_raw)
                except (ValueError, TypeError):
                    sender_id_int = 0

            ts_raw = row["timestamp"]
            ts_int = 0
            if ts_raw is not None:
                try:
                    ts_int = int(ts_raw)
                except (ValueError, TypeError):
                    ts_int = 0

            msg = {
                "evidence_id": evidence_id,
                "message_id": str(row["message_id"]) if row["message_id"] is not None else "",
                "dialog_id": str(row["dialog_id"]) if row["dialog_id"] is not None else "",
                "sender_id": sender_id_int,
                "body": body_str,
                "timestamp": ts_int,
                "media_type": media_type,
                "media_path": m_path_str,
                "message_type": msg_type,
            }
            messages.append(msg)
        conn.close()
        return messages
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_messages (Telegram): {e}")
        return []