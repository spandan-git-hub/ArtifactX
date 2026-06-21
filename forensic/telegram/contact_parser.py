"""Telegram contact extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def extract_contacts(db_path: Path, evidence_id: int) -> List[Dict[str, Any]]:
    """Extract Telegram contacts from the database.
    Returns a list of dictionaries matching TelegramContact model.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # to access columns by name
        cursor = conn.cursor()
        # Try to get contacts; adjust table and column names as needed
        # Common Telegram users table: _id, user_id, first_name, last_name, username, phone
        cursor.execute("""
            SELECT
                u.user_id AS user_id,
                u.first_name AS first_name,
                u.last_name AS last_name,
                u.username AS username,
                u.phone AS phone
            FROM users u
        """)
        rows = cursor.fetchall()
        contacts = []
        for row in rows:
            # Convert row to dict
            contact = {
                "evidence_id": evidence_id,
                "user_id": int(row["user_id"]) if row["user_id"] is not None else 0,
                "first_name": row["first_name"] if row["first_name"] is not None else "",
                "last_name": row["last_name"] if row["last_name"] is not None else "",
                "username": row["username"] if row["username"] is not None else "",
                "phone": row["phone"] if row["phone"] is not None else "",
            }
            contacts.append(contact)
        conn.close()
        return contacts
    except sqlite3.Error as e:
        # Log error
        return []