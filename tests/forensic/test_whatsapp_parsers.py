"""Unit tests for WhatsApp parsers."""

import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from forensic.whatsapp.detector import is_whatsapp_database
from forensic.whatsapp.message_parser import extract_messages
from forensic.whatsapp.contact_parser import extract_contacts
from forensic.whatsapp.group_parser import extract_groups
from forensic.whatsapp.media_parser import extract_media_references


def create_mock_whatsapp_db():
    """Create a mock WhatsApp SQLite database for testing."""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_file.close()

    # Create database and tables
    conn = sqlite3.connect(temp_file.name)
    cursor = conn.cursor()

    # Create minimal WhatsApp-like tables
    cursor.execute('''
        CREATE TABLE messages (
            _id INTEGER PRIMARY KEY,
            key_remote_jid TEXT,
            key_from_me INTEGER,
            key_id TEXT,
            data TEXT,
            timestamp INTEGER,
            media_mime_type TEXT,
            media_url TEXT,
            status INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE wa_contacts (
            jid TEXT PRIMARY KEY,
            display_name TEXT,
            phone_number TEXT,
            status TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE chats (
            id TEXT PRIMARY KEY,
            subject TEXT,
            creator TEXT,
            creation INTEGER,
            is_group INTEGER
        )
    ''')

    # Insert test data
    cursor.execute('''
        INSERT INTO messages (
            key_remote_jid, key_from_me, key_id, data, timestamp,
            media_mime_type, media_url, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        '1234567890@s.whatsapp.net', 0, 'msg_1', 'Hello World', 1625097600000,
        'image/jpeg', 'http://example.com/image.jpg', 1
    ))

    cursor.execute('''
        INSERT INTO messages (
            key_remote_jid, key_from_me, key_id, data, timestamp,
            media_mime_type, media_url, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        '0987654321@s.whatsapp.net', 1, 'msg_2', 'Hi there', 1625097700000,
        None, None, 1
    ))

    cursor.execute('''
        INSERT INTO wa_contacts (jid, display_name, phone_number, status)
        VALUES (?, ?, ?, ?)
    ''', (
        '1234567890@s.whatsapp.net', 'John Doe', '+1234567890', '0'
    ))

    cursor.execute('''
        INSERT INTO wa_contacts (jid, display_name, phone_number, status)
        VALUES (?, ?, ?, ?)
    ''', (
        '0987654321@s.whatsapp.net', 'Jane Smith', '+0987654321', '0'
    ))

    cursor.execute('''
        INSERT INTO chats (id, subject, creator, creation, is_group)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'group_123@g.us', 'Test Group', 'creator@s.whatsapp.net', 1625097500000, 1
    ))

    conn.commit()
    conn.close()

    return temp_file.name


def test_is_whatsapp_database():
    """Test WhatsApp database detection."""
    # Test with non-existent file
    assert is_whatsapp_database(Path('/non/existent/file.db')) is False

    # Test with mock WhatsApp database
    db_path = create_mock_whatsapp_db()
    try:
        assert is_whatsapp_database(Path(db_path)) is True
    finally:
        os.unlink(db_path)


def test_extract_messages():
    """Test message extraction from WhatsApp database."""
    db_path = create_mock_whatsapp_db()
    try:
        messages = extract_messages(Path(db_path), 1)

        # Should have 2 messages
        assert len(messages) == 2

        # Check first message (key_from_me = 0 - received)
        assert messages[0]['evidence_id'] == 1
        assert messages[0]['message_id'] == 'msg_1'
        assert messages[0]['key_remote_jid'] == '1234567890@s.whatsapp.net'
        assert messages[0]['sender_jid'] == '1234567890@s.whatsapp.net'  # Actual sender
        assert messages[0]['participant_jid'] == '1'  # Our number (placeholder)
        assert messages[0]['body'] == 'Hello World'
        assert messages[0]['timestamp'] == 1625097600000
        assert messages[0]['media_type'] == 'image/jpeg'
        assert messages[0]['media_path'] == 'http://example.com/image.jpg'
        assert messages[0]['message_type'] == 'image'
        assert messages[0]['status'] == 1

        # Check second message (key_from_me = 1 - sent)
        assert messages[1]['message_id'] == 'msg_2'
        assert messages[1]['key_remote_jid'] == '0987654321@s.whatsapp.net'
        assert messages[1]['sender_jid'] == '1'  # Our number (placeholder)
        assert messages[1]['participant_jid'] == '0987654321@s.whatsapp.net'  # Actual recipient
        assert messages[1]['body'] == 'Hi there'
        assert messages[1]['timestamp'] == 1625097700000
        assert messages[1]['media_type'] is None
        assert messages[1]['media_path'] is None
        assert messages[1]['message_type'] is None
        assert messages[1]['status'] == 1

    finally:
        os.unlink(db_path)


def test_extract_contacts():
    """Test contact extraction from WhatsApp database."""
    db_path = create_mock_whatsapp_db()
    try:
        contacts = extract_contacts(Path(db_path), 1)

        # Should have 2 contacts
        assert len(contacts) == 2

        # Check first contact
        assert contacts[0]['evidence_id'] == 1
        assert contacts[0]['jid'] == '1234567890@s.whatsapp.net'
        assert contacts[0]['display_name'] == 'John Doe'
        assert contacts[0]['phone_number'] == '+1234567890'
        assert contacts[0]['status'] == '0'

        # Check second contact
        assert contacts[1]['jid'] == '0987654321@s.whatsapp.net'
        assert contacts[1]['display_name'] == 'Jane Smith'
        assert contacts[1]['phone_number'] == '+0987654321'
        assert contacts[1]['status'] == '0'

    finally:
        os.unlink(db_path)


def test_extract_groups():
    """Test group extraction from WhatsApp database."""
    db_path = create_mock_whatsapp_db()
    try:
        groups = extract_groups(Path(db_path), 1)

        # Should have 1 group
        assert len(groups) == 1

        # Check the group
        assert groups[0]['evidence_id'] == 1
        assert groups[0]['group_jid'] == 'group_123@g.us'
        assert groups[0]['subject'] == 'Test Group'
        assert groups[0]['creator_jid'] == 'creator@s.whatsapp.net'
        assert groups[0]['creation_timestamp'] == 1625097500000

    finally:
        os.unlink(db_path)


def test_extract_from_empty_database():
    """Test extraction from database with no WhatsApp tables."""
    # Create a temporary file with no tables
    temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_file.close()

    try:
        # Should return empty lists
        assert extract_messages(Path(temp_file.name), 1) == []
        assert extract_contacts(Path(temp_file.name), 1) == []
        assert extract_groups(Path(temp_file.name), 1) == []
    finally:
        os.unlink(temp_file.name)


def test_extract_from_non_whatsapp_database():
    """Test extraction from database that doesn't have WhatsApp tables."""
    # Create a temporary file with different tables
    temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_file.close()

    try:
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE dummy (id INTEGER)')
        conn.commit()
        conn.close()

        # Should return empty lists
        assert extract_messages(Path(temp_file.name), 1) == []
        assert extract_contacts(Path(temp_file.name), 1) == []
        assert extract_groups(Path(temp_file.name), 1) == []
        assert extract_media_references(Path(temp_file.name), 1) == []
    finally:
        os.unlink(temp_file.name)


def test_extract_media_references():
    """Test media reference extraction from WhatsApp database."""
    db_path = create_mock_whatsapp_db()
    try:
        media_refs = extract_media_references(Path(db_path), 1)

        # Should have 1 media reference (from the first message)
        assert len(media_refs) == 1

        ref = media_refs[0]
        assert ref['evidence_id'] == 1
        assert ref['message_id'] == 'msg_1'
        assert ref['media_path'] == 'http://example.com/image.jpg'
        assert ref['media_type'] == 'image/jpeg'
        assert ref['message_type'] == 'image'
    finally:
        os.unlink(db_path)