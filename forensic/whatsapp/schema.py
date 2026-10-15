"""
WhatsApp schema-family detection and capability introspection (spec B7.1).
Complies with master.md R12 (untrusted input hardening), R20, and Q-001.
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Set, Tuple

from forensic.common.sqlite_open import quote_ident
from forensic.whatsapp.models import SchemaFamily, UnsupportedSchemaError


def detect_wa_schema(conn: sqlite3.Connection) -> SchemaFamily:
    """
    Introspect a SQLite connection to determine WhatsApp schema family and capabilities.
    
    Returns:
        SchemaFamily with family ("modern" | "legacy"), tables, columns, and capability flags.
        
    Raises:
        UnsupportedSchemaError if tables do not match known modern or legacy schema signatures.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    raw_tables = [row[0] for row in cursor.fetchall()]
    
    tables_lower: Set[str] = {t.lower() for t in raw_tables}
    table_map: Dict[str, str] = {t.lower(): t for t in raw_tables}
    
    # Introspect column names safely without executing DB SQL
    columns_by_table: Dict[str, Tuple[str, ...]] = {}
    for lower_name, actual_name in table_map.items():
        quoted = quote_ident(actual_name)
        cursor.execute(f"PRAGMA table_info({quoted})")
        cols = tuple(row[1] for row in cursor.fetchall())
        columns_by_table[lower_name] = cols

    cursor.close()

    capabilities: Dict[str, bool] = {}
    notes: List[str] = []

    # Check for modern schema: message + chat + jid
    if {"message", "chat", "jid"}.issubset(tables_lower):
        family = "modern"
        msg_cols = set(columns_by_table.get("message", ()))
        
        capabilities["has_text_data"] = "text_data" in msg_cols
        capabilities["has_sender_jid_row_id"] = "sender_jid_row_id" in msg_cols
        capabilities["has_received_timestamp"] = "received_timestamp" in msg_cols
        capabilities["has_receipt_server_timestamp"] = "receipt_server_timestamp" in msg_cols
        capabilities["has_origination_flags"] = "origination_flags" in msg_cols
        capabilities["has_message_media"] = "message_media" in tables_lower
        capabilities["has_message_revoked"] = "message_revoked" in tables_lower
        capabilities["has_message_edit_info"] = "message_edit_info" in tables_lower
        capabilities["has_message_quoted"] = "message_quoted" in tables_lower
        capabilities["has_message_location"] = "message_location" in tables_lower
        capabilities["has_group_participants"] = any(t.startswith("group_participant") for t in tables_lower)
        
        notes.append("Modern WhatsApp Android schema detected (message/chat/jid structure).")

    # Check for legacy schema: messages (+ optional chat_list / chats)
    elif "messages" in tables_lower or ({"chat_list", "wa_contacts"}.intersection(tables_lower)):
        family = "legacy"
        msg_table = "messages" if "messages" in tables_lower else "message"
        msg_cols = set(columns_by_table.get(msg_table, ()))
        
        capabilities["has_chat_list"] = "chat_list" in tables_lower or "chats" in tables_lower
        capabilities["has_wa_contacts"] = "wa_contacts" in tables_lower
        capabilities["has_key_id"] = "key_id" in msg_cols or "_id" in msg_cols
        capabilities["has_text_data"] = "data" in msg_cols or "text_data" in msg_cols or "message" in msg_cols
        capabilities["has_sender_jid_row_id"] = False
        capabilities["has_received_timestamp"] = "received_timestamp" in msg_cols
        capabilities["has_message_media"] = "message_media" in tables_lower
        capabilities["has_message_revoked"] = False
        capabilities["has_message_edit_info"] = False
        capabilities["has_message_quoted"] = False
        capabilities["has_message_location"] = False
        capabilities["has_group_participants"] = False
        
        notes.append("Legacy WhatsApp Android schema detected (messages structure).")

    else:
        raise UnsupportedSchemaError(
            f"Unsupported WhatsApp database schema. Tables seen: {sorted(tables_lower)}",
            tables_seen=tables_lower,
        )

    return SchemaFamily(
        family=family,
        tables=tuple(sorted(tables_lower)),
        columns=columns_by_table,
        capabilities=capabilities,
        notes=tuple(notes),
    )
