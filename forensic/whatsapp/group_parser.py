"""WhatsApp group extraction."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any


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
        # Try to get groups from chats table where is_group = 1
        cursor.execute("""
            SELECT
                id AS group_jid,
                subject AS subject,
                creator AS creator_jid,
                creation AS creation_timestamp
            FROM chats
            WHERE is_group = 1
        """)
        rows = cursor.fetchall()
        groups = []
        for row in rows:
            group = {
                "evidence_id": evidence_id,
                "group_jid": str(row["group_jid"]) if row["group_jid"] is not None else "",
                "subject": row["subject"] if row["subject"] is not None else "",
                "creator_jid": row["creator_jid"] if row["creator_jid"] is not None else "",
                "creation_timestamp": int(row["creation_timestamp"]) if row["creation_timestamp"] is not None else 0,
            }
            groups.append(group)
        conn.close()
        return groups
    except sqlite3.Error as e:
        import logging
        logging.getLogger(__name__).error(f"Parse error in extract_groups: {e}")
        return []