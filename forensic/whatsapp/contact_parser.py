"""WhatsApp contact extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


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
        # Attempt to query contacts table; common name: wa_contacts
        cursor.execute("""
            SELECT
                jid AS jid,
                display_name AS display_name,
                phone_number AS phone_number,
                status AS status
            FROM wa_contacts
        """)
        rows = cursor.fetchall()
        contacts = []
        for row in rows:
            contact = {
                "evidence_id": evidence_id,
                "jid": row["jid"] if row["jid"] is not None else "",
                "display_name": row["display_name"] if row["display_name"] is not None else "",
                "phone_number": row["phone_number"] if row["phone_number"] is not None else "",
                "status": row["status"] if row["status"] is not None else "",
            }
            contacts.append(contact)
        conn.close()
        return contacts
    except sqlite3.Error:
        return []