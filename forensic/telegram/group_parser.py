"""Telegram group/channel extraction."""

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
            return f"c.{column}"
    return default


def _group_query(table: str, cols: set[str]) -> str:
    group_id = _first_existing(cols, ["chat_id", "group_id", "_id", "id"], "c.rowid")
    title = _first_existing(cols, ["title", "name", "subject"], "''")
    username = _first_existing(cols, ["username", "user_name", "handle"], "''")
    g_type = _first_existing(cols, ["type", "chat_type"], "''")

    where_clause = ""
    if "type" in cols or "chat_type" in cols:
        where_clause = f"WHERE LOWER({g_type}) IN ('group', 'supergroup', 'channel')"

    return f"""
        SELECT
            {group_id} AS group_id,
            {title} AS title,
            {username} AS username,
            {g_type} AS type
        FROM {table} c
        {where_clause}
    """


def extract_groups(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram groups and channels from the database.
    Returns a list of dictionaries matching TelegramGroup model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        table_names = _tables(cursor)
        target_table = None
        for candidate in ["chats", "chat", "dialogs"]:
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
            gid_raw = row["group_id"]
            gid_int = 0
            if gid_raw is not None:
                try:
                    gid_int = int(gid_raw)
                except (ValueError, TypeError):
                    gid_int = 0

            group = {
                "evidence_id": evidence_id,
                "group_id": gid_int,
                "title": str(row["title"]) if row["title"] is not None else "",
                "username": str(row["username"]) if row["username"] is not None else "",
                "type": str(row["type"]) if row["type"] is not None else "",
            }
            groups.append(group)
        conn.close()
        return groups
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_groups (Telegram): {e}")
        return []