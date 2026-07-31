"""WhatsApp contact extraction."""

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


def _contact_query(table: str, cols: set[str]) -> str:
    jid = _first_existing(cols, ["jid", "raw_string_jid", "raw_string", "user", "key_remote_jid"], "''")
    display_name = _first_existing(cols, ["display_name", "wa_name", "given_name", "name"], "''")
    phone_number = _first_existing(cols, ["phone_number", "number", "phone"], "''")
    status = _first_existing(cols, ["status", "status_autofill"], "''")

    return f"""
        SELECT
            {jid} AS jid,
            {display_name} AS display_name,
            {phone_number} AS phone_number,
            {status} AS status
        FROM {table} c
    """


def extract_contacts(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract WhatsApp contacts from the database.
    Returns a list of dictionaries matching WhatsAppContact model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        table_names = _tables(cursor)

        target_table = None
        for candidate in ["wa_contacts", "contacts", "wa_contact", "jid"]:
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
            contact = {
                "evidence_id": evidence_id,
                "jid": str(row["jid"]) if row["jid"] is not None else "",
                "display_name": str(row["display_name"]) if row["display_name"] is not None else "",
                "phone_number": str(row["phone_number"]) if row["phone_number"] is not None else "",
                "status": str(row["status"]) if row["status"] is not None else "",
            }
            contacts.append(contact)
        conn.close()
        return contacts
    except sqlite3.Error as e:
        logger.error(f"Parse error in extract_contacts: {e}")
        return []