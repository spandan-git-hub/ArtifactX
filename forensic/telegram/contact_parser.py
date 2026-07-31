"""Telegram contact extraction."""

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
            return f"u.{column}"
    return default


def _contact_query(table: str, cols: set[str]) -> str:
    user_id = _first_existing(cols, ["user_id", "_id", "id", "uid"], "u.rowid")
    first_name = _first_existing(cols, ["first_name", "fname", "name"], "''")
    last_name = _first_existing(cols, ["last_name", "lname"], "''")
    username = _first_existing(cols, ["username", "user_name", "handle"], "''")
    phone = _first_existing(cols, ["phone", "phone_number", "mobile"], "''")

    return f"""
        SELECT
            {user_id} AS user_id,
            {first_name} AS first_name,
            {last_name} AS last_name,
            {username} AS username,
            {phone} AS phone
        FROM {table} u
    """


def extract_contacts(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram contacts from the database.
    Returns a list of dictionaries matching TelegramContact model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        table_names = _tables(cursor)
        target_table = None
        for candidate in ["users", "user", "contacts"]:
            if candidate in table_names:
                target_table = candidate
                break

        if not target_table:
            conn.close()
            return []

        cols = _columns(cursor, target_table)
        cursor.execute(_contact_query(target_table, cols))
        rows = cursor.fetchall()
        contacts = []
        for row in rows:
            uid_raw = row["user_id"]
            user_id_int = 0
            if uid_raw is not None:
                try:
                    user_id_int = int(uid_raw)
                except (ValueError, TypeError):
                    user_id_int = 0

            contact = {
                "evidence_id": evidence_id,
                "user_id": user_id_int,
                "first_name": str(row["first_name"]) if row["first_name"] is not None else "",
                "last_name": str(row["last_name"]) if row["last_name"] is not None else "",
                "username": str(row["username"]) if row["username"] is not None else "",
                "phone": str(row["phone"]) if row["phone"] is not None else "",
            }
            contacts.append(contact)
        conn.close()
        return contacts
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_contacts (Telegram): {e}")
        return []