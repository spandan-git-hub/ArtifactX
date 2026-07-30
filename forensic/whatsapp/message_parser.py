"""WhatsApp message extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


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


def _message_query(table: str, cols: set[str]) -> str:
    message_id = _first_existing(cols, ["key_id", "message_id", "_id", "id"], "msg.rowid")
    remote_jid = _first_existing(cols, ["key_remote_jid", "remote_jid", "chat_jid", "chat_row_id"], "''")
    from_me = _first_existing(cols, ["key_from_me", "from_me", "is_from_me"], "0")
    body = _first_existing(cols, ["data", "text_data", "message", "body", "text"], "''")
    timestamp = _first_existing(cols, ["timestamp", "received_timestamp", "date", "sort_id"], "0")
    media_type = _first_existing(cols, ["media_mime_type", "mime_type"], "NULL")
    media_path = _first_existing(cols, ["media_url", "media_name", "file_path", "media_path"], "NULL")
    status = _first_existing(cols, ["status", "message_status"], "''")

    return f"""
        SELECT
            {message_id} AS message_id,
            {remote_jid} AS key_remote_jid,
            CASE
                WHEN {from_me} = 1 THEN 'me'
                ELSE CAST({remote_jid} AS TEXT)
            END AS sender_jid,
            CASE
                WHEN {from_me} = 1 THEN CAST({remote_jid} AS TEXT)
                ELSE 'me'
            END AS participant_jid,
            {body} AS body,
            {timestamp} AS timestamp,
            {media_type} AS media_type,
            {media_path} AS media_path,
            CASE
                WHEN {media_type} IS NOT NULL THEN
                    CASE
                        WHEN LOWER({media_type}) LIKE 'image/%' THEN 'image'
                        WHEN LOWER({media_type}) LIKE 'video/%' THEN 'video'
                        WHEN LOWER({media_type}) LIKE 'audio/%' THEN 'audio'
                        ELSE 'document'
                    END
                WHEN {media_path} IS NOT NULL THEN 'media'
                ELSE 'text'
            END AS message_type,
            {status} AS status
        FROM {table} msg
    """


def extract_messages(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract WhatsApp messages from the database.
    Returns a list of dictionaries matching WhatsAppMessage model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # to access columns by name
        cursor = conn.cursor()
        table_names = _tables(cursor)
        if "messages" in table_names:
            table = "messages"
        elif "message" in table_names:
            table = "message"
        else:
            conn.close()
            return []

        cursor.execute(_message_query(table, _columns(cursor, table)))
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
