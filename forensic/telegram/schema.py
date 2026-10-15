"""
Telegram SQLite database schema introspection and family detection (spec B9.1).

Detects schema family, tables, column layouts, and capability flags safely without
executing untrusted SQL statements from evidence (master.md R12).
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Set, Tuple

from forensic.common.sqlite_open import quote_ident
from forensic.telegram.models import TgSchemaInfo, UnsupportedSchemaError

REQUIRED_CACHE4_TABLES: Set[str] = {"messages_v2", "dialogs", "users"}


def detect_tg_schema(
    conn: sqlite3.Connection,
    raise_on_unknown: bool = False,
) -> TgSchemaInfo:
    """
    Introspect SQLite schema to detect Telegram database family and capabilities (B9.1).

    Args:
        conn: Hardened read-only SQLite connection.
        raise_on_unknown: If True, raises UnsupportedSchemaError when required tables are missing.

    Returns:
        TgSchemaInfo containing family, tables, columns, capabilities, and notes.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    table_names = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
    tables_set = {t.lower() for t in table_names}

    columns: Dict[str, Tuple[str, ...]] = {}
    for tbl in table_names:
        safe_tbl = quote_ident(tbl)
        cursor.execute(f"PRAGMA table_info({safe_tbl})")
        columns[tbl] = tuple(row[1] for row in cursor.fetchall())

    cursor.execute("PRAGMA user_version")
    user_version_row = cursor.fetchone()
    user_version = user_version_row[0] if user_version_row else 0
    cursor.close()

    is_cache4 = REQUIRED_CACHE4_TABLES.issubset(tables_set)

    if not is_cache4:
        if raise_on_unknown:
            raise UnsupportedSchemaError(
                f"SQLite database lacks required Telegram cache4 tables: {sorted(REQUIRED_CACHE4_TABLES - tables_set)}",
                tables_seen=set(table_names),
            )
        return TgSchemaInfo(
            family="unknown",
            tables=tuple(sorted(table_names)),
            columns=columns,
            capabilities={},
            notes=(f"Missing required tables: {sorted(REQUIRED_CACHE4_TABLES - tables_set)}",),
        )

    capabilities = {
        "has_media_v4": "media_v4" in tables_set,
        "has_contacts": "contacts" in tables_set,
        "has_user_contacts_v7": "user_contacts_v7" in tables_set,
        "has_chats": "chats" in tables_set,
        "has_chat_settings_v2": "chat_settings_v2" in tables_set,
        "has_enc_chats": "enc_chats" in tables_set,
        "has_messages_holes": "messages_holes" in tables_set,
        "has_scheduled_messages_v2": "scheduled_messages_v2" in tables_set,
        "has_search_recent": "search_recent" in tables_set,
        "user_version_155": (user_version == 155),
    }

    notes = [
        f"Introspected Android cache4.db schema (PRAGMA user_version = {user_version}).",
    ]
    if capabilities["has_media_v4"]:
        notes.append("Standalone media_v4 cache table present.")
    if capabilities["has_enc_chats"]:
        notes.append("enc_chats table present (secret chat keys/metadata; message content device-only per DEC-004).")

    return TgSchemaInfo(
        family="android_cache4",
        tables=tuple(sorted(table_names)),
        columns=columns,
        capabilities=capabilities,
        notes=tuple(notes),
    )
