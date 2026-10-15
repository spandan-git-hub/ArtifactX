"""
Unit tests for untrusted-input hardening, malicious schemas, and parser determinism (R11, R12).
"""

import sqlite3
from pathlib import Path

import pytest

from forensic.common.canonical import canonical_json
from forensic.common.hashing import sha256_hex
from forensic.common.sqlite_open import HostileDatabaseError, open_sqlite_ro, quote_ident
from forensic.whatsapp.parser import WhatsAppParser


def test_quote_ident_rejects_sql_injection():
    """Verify quote_ident strictly rejects SQL injection payloads and hostile characters."""
    bad_identifiers = [
        "message; DROP TABLE message; --",
        "chat' OR '1'='1",
        'message" AND 1=1',
        "table with spaces",
        "table\nwith\nnewlines",
        "table\x00nullbyte",
        "",
        "1starts_with_digit",
    ]
    for bad in bad_identifiers:
        with pytest.raises(ValueError):
            quote_ident(bad)


def test_quote_ident_whitelist_enforcement():
    """Verify quote_ident enforces allowed whitelist if specified."""
    allowed = ["message", "chat", "jid"]
    assert quote_ident("message", whitelist=allowed) == '"message"'
    assert quote_ident("CHAT", whitelist=allowed) == '"CHAT"'

    with pytest.raises(ValueError) as exc_info:
        quote_ident("secret_table", whitelist=allowed)
    assert "not permitted by whitelist" in str(exc_info.value)


def test_hostile_db_triggers_and_views_cannot_execute(tmp_path):
    """
    Assert that malicious SQLite triggers and views planted in untrusted evidence
    cannot execute write operations due to PRAGMA trusted_schema=OFF and strict authorizer.
    """
    db_path = tmp_path / "hostile.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE victim (id INTEGER PRIMARY KEY, secret TEXT);
        INSERT INTO victim VALUES (1, 'initial_state');

        CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, from_me INTEGER, key_id TEXT, timestamp INTEGER);
        CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER);
        CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT, raw_string TEXT);

        -- Malicious trigger attempting data mutation upon reading/accessing message
        CREATE TRIGGER malicious_trigger
        AFTER UPDATE ON message
        BEGIN
            UPDATE victim SET secret = 'tampered_via_trigger';
        END;
        """
    )
    conn.commit()
    conn.close()

    raw_bytes = db_path.read_bytes()
    ro_conn = open_sqlite_ro(raw_bytes)

    # Attempting to mutate or execute trigger must fail due to read_only and authorizer
    with pytest.raises(sqlite3.DatabaseError):
        ro_conn.execute("UPDATE message SET key_id = 'hack' WHERE _id = 1")

    # Victim table remains intact
    cur = ro_conn.cursor()
    cur.execute("SELECT secret FROM victim WHERE id = 1")
    assert cur.fetchone()[0] == "initial_state"
    ro_conn.close()


def test_hostile_db_attach_blocked(tmp_path):
    """Assert that ATTACH DATABASE is strictly blocked by authorizer."""
    db_path = tmp_path / "attach_test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t1 (x INTEGER)")
    conn.commit()
    conn.close()

    ro_conn = open_sqlite_ro(db_path.read_bytes())
    with pytest.raises(sqlite3.DatabaseError) as exc_info:
        ro_conn.execute("ATTACH DATABASE ':memory:' AS attached_db")
    assert "not authorized" in str(exc_info.value).lower()
    ro_conn.close()


def test_non_sqlite_header_raises_value_error():
    """Assert non-sqlite bytes raise ValueError."""
    fake_data = b"This is not a SQLite database file at all!"
    with pytest.raises(ValueError) as exc:
        open_sqlite_ro(fake_data)
    assert "valid SQLite format 3 header" in str(exc.value)


def test_parser_determinism(tmp_path):
    """Verify that parsing the exact same database twice produces identical output hashes (R11)."""
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    if not ds01_path.exists():
        pytest.skip("DS-01-dev fixture not found")

    raw_bytes = ds01_path.read_bytes()
    p1 = WhatsAppParser(raw_bytes, evidence_id="ev_01", evidence_sha256=sha256_hex(raw_bytes))
    res1 = p1.parse()

    p2 = WhatsAppParser(raw_bytes, evidence_id="ev_01", evidence_sha256=sha256_hex(raw_bytes))
    res2 = p2.parse()

    import json
    # Compare serialized dictionary hashes
    hash1 = sha256_hex(json.dumps(res1.to_dict(), sort_keys=True))
    hash2 = sha256_hex(json.dumps(res2.to_dict(), sort_keys=True))

    assert hash1 == hash2
    assert len(res1.messages) == len(res2.messages)
    assert len(res1.chats) == len(res2.chats)
    assert len(res1.revocations) == len(res2.revocations)
    assert len(res1.edits) == len(res2.edits)
