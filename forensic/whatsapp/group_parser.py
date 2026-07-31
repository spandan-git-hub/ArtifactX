"""WhatsApp group extraction."""

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
            return f"g.{column}"
    return default


def _group_query(table: str, cols: set[str]) -> str:
    group_jid = _first_existing(cols, ["group_jid", "jid", "raw_string_jid", "id", "chat_jid"], "''")
    subject = _first_existing(cols, ["subject", "name", "title", "display_name"], "''")
    creator_jid = _first_existing(cols, ["creator_jid", "creator", "creator_raw_string"], "''")
    creation_ts = _first_existing(cols, ["creation_timestamp", "created_timestamp", "creation", "created"], "0")

    where_clause = ""
    if "is_group" in cols:
        where_clause = "WHERE g.is_group = 1"
    elif "jid" in cols or "group_jid" in cols or "id" in cols:
        where_clause = f"WHERE CAST({group_jid} AS TEXT) LIKE '%@g.us'"

    return f"""
        SELECT
            {group_jid} AS group_jid,
            {subject} AS subject,
            {creator_jid} AS creator_jid,
            {creation_ts} AS creation_timestamp
        FROM {table} g
        {where_clause}
    """


def extract_groups(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract WhatsApp groups from the database.
    Returns a list of dictionaries matching WhatsAppGroup model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        table_names = _tables(cursor)

        target_table = None
        for candidate in ["chats", "chat", "chat_view", "groups", "group_metadata"]:
            if candidate in table_names:
                target_table = candidate
                break

        if not target_table:
            conn.close()
            return []

        cols = _columns(cursor, target_table)
        cursor.execute(_group_query(target_table, cols))
        rows = cursor.fetchall()
        groups = []
        for row in rows:
            group = {
                "evidence_id": evidence_id,
                "group_jid": str(row["group_jid"]) if row["group_jid"] is not None else "",
                "subject": str(row["subject"]) if row["subject"] is not None else "",
                "creator_jid": str(row["creator_jid"]) if row["creator_jid"] is not None else "",
                "creation_timestamp": int(row["creation_timestamp"]) if row["creation_timestamp"] is not None else 0,
            }
            groups.append(group)
        conn.close()
        return groups
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_groups: {e}")
        return []