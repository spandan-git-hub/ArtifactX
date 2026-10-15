"""
Unit tests for Telegram schema introspection and family detection (spec B9.1).
"""

import sqlite3
import pytest

from forensic.telegram.models import UnsupportedSchemaError
from forensic.telegram.schema import detect_tg_schema


def test_detect_tg_schema_valid_cache4():
    """Verify detection of modern Android cache4.db schema."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version = 155")
    cursor.execute("CREATE TABLE messages_v2 (mid INTEGER, uid INTEGER, date INTEGER, data BLOB)")
    cursor.execute("CREATE TABLE dialogs (did INTEGER PRIMARY KEY, date INTEGER, unread_count INTEGER)")
    cursor.execute("CREATE TABLE users (uid INTEGER PRIMARY KEY, name TEXT, data BLOB)")
    cursor.execute("CREATE TABLE chats (uid INTEGER PRIMARY KEY, name TEXT, data BLOB)")
    cursor.execute("CREATE TABLE media_v4 (mid INTEGER, uid INTEGER, data BLOB)")
    cursor.execute("CREATE TABLE enc_chats (uid INTEGER PRIMARY KEY, authkey BLOB)")

    schema = detect_tg_schema(conn)
    assert schema.family == "android_cache4"
    assert "messages_v2" in schema.tables
    assert "dialogs" in schema.tables
    assert "users" in schema.tables
    assert schema.capabilities["has_media_v4"] is True
    assert schema.capabilities["has_enc_chats"] is True
    assert schema.capabilities["user_version_155"] is True
    conn.close()


def test_detect_tg_schema_missing_required_tables():
    """Verify unknown family or exception when required tables are missing."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE random_table (id INTEGER PRIMARY KEY)")

    schema = detect_tg_schema(conn, raise_on_unknown=False)
    assert schema.family == "unknown"

    with pytest.raises(UnsupportedSchemaError) as exc_info:
        detect_tg_schema(conn, raise_on_unknown=True)
    assert "random_table" in exc_info.value.tables_seen
    conn.close()
