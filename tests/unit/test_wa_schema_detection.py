"""Unit tests for WhatsApp schema-family detection and capability introspection (B7.1)."""

import sqlite3
from pathlib import Path

import pytest

from forensic.whatsapp.models import SchemaFamily, UnsupportedSchemaError
from forensic.whatsapp.schema import detect_wa_schema
from forensic.whatsapp import is_whatsapp_database


def test_detect_wa_schema_modern(tmp_path):
    """Test schema detection on modern WhatsApp database with all standard tables."""
    db_path = tmp_path / "modern_test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT, raw_string TEXT, type INTEGER);
        CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER, subject TEXT, hidden INTEGER, last_message_row_id INTEGER);
        CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, from_me INTEGER, key_id TEXT, sender_jid_row_id INTEGER, timestamp INTEGER, text_data TEXT, message_type INTEGER, status INTEGER);
        CREATE TABLE message_media (message_row_id INTEGER PRIMARY KEY, file_path TEXT, media_name TEXT, mime_type TEXT);
        CREATE TABLE message_revoked (message_row_id INTEGER PRIMARY KEY, revoked_key_id TEXT);
        CREATE TABLE message_edit_info (message_row_id INTEGER PRIMARY KEY, original_key_id TEXT, original_timestamp INTEGER);
        CREATE TABLE message_quoted (message_row_id INTEGER PRIMARY KEY, key_id TEXT, parent_key_id TEXT);
        CREATE TABLE message_location (message_row_id INTEGER PRIMARY KEY, latitude REAL, longitude REAL);
        CREATE TABLE group_participants (_id INTEGER PRIMARY KEY, group_jid_row_id INTEGER, user_jid_row_id INTEGER, rank INTEGER);
        """
    )
    conn.commit()

    schema = detect_wa_schema(conn)
    conn.close()

    assert schema.family == "modern"
    assert schema.capabilities["has_text_data"] is True
    assert schema.capabilities["has_sender_jid_row_id"] is True
    assert schema.capabilities["has_message_media"] is True
    assert schema.capabilities["has_message_revoked"] is True
    assert schema.capabilities["has_message_edit_info"] is True
    assert schema.capabilities["has_message_quoted"] is True
    assert schema.capabilities["has_message_location"] is True
    assert schema.capabilities["has_group_participants"] is True
    assert is_whatsapp_database(db_path) is True


def test_detect_wa_schema_legacy(tmp_path):
    """Test schema detection on legacy WhatsApp database (messages table)."""
    db_path = tmp_path / "legacy_test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE messages (
            _id INTEGER PRIMARY KEY,
            key_remote_jid TEXT,
            key_from_me INTEGER,
            key_id TEXT,
            data TEXT,
            timestamp INTEGER,
            media_wa_type INTEGER,
            status INTEGER
        );
        CREATE TABLE chat_list (_id INTEGER PRIMARY KEY, key_remote_jid TEXT);
        """
    )
    conn.commit()

    schema = detect_wa_schema(conn)
    conn.close()

    assert schema.family == "legacy"
    assert schema.capabilities["has_key_id"] is True
    assert schema.capabilities["has_text_data"] is True
    assert schema.capabilities["has_chat_list"] is True
    assert is_whatsapp_database(db_path) is True


def test_detect_wa_schema_unknown_raises(tmp_path):
    """Test unknown database schema raises UnsupportedSchemaError."""
    db_path = tmp_path / "unrelated.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL);
        """
    )
    conn.commit()

    with pytest.raises(UnsupportedSchemaError) as exc_info:
        detect_wa_schema(conn)
    
    assert "Unsupported WhatsApp database schema" in str(exc_info.value)
    assert "customers" in exc_info.value.tables_seen
    assert "orders" in exc_info.value.tables_seen
    conn.close()
    assert is_whatsapp_database(db_path) is False


def test_detect_wa_schema_on_ds01_fixture():
    """Verify schema detection on DS-01-dev msgstore.db."""
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    if not ds01_path.exists():
        pytest.skip("DS-01-dev/msgstore.db fixture not found")

    assert is_whatsapp_database(ds01_path) is True
