"""
Unit tests for Tier 4 ID-gap indicator (B10.4, spec 08_DELETED_DATA_RECOVERY.md).

Covers:
1. ID-gap confidence capping <= 0.30 and 'weak_hint' strength label.
2. Mandatory non-deletion limitations disclosure.
3. Suppression when stronger tiers (Tier 1-3) explain missing row IDs.
4. Clean handling of continuous sequences (zero false gap findings).
5. Both WhatsApp and Telegram table schemas.
"""

import sqlite3
import pytest

from forensic.recovery.tier4_gaps import detect_tier4_gaps


def _create_wa_db_with_gap(gaps: list[int] | None = None) -> bytes:
    """Create in-memory SQLite db with WhatsApp message table and optional gap."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, text_data TEXT)")
    
    # Insert rows: 1, 2, 3, 5, 6 (gap at 4)
    rows = [(1, 10, "Hello"), (2, 10, "World"), (3, 10, "How"), (5, 10, "Are"), (6, 10, "You")]
    cursor.executemany("INSERT INTO message VALUES (?, ?, ?)", rows)
    conn.commit()
    
    # Extract raw bytes
    raw_bytes = conn.serialize()
    conn.close()
    return raw_bytes


def _create_tg_db_with_gap() -> bytes:
    """Create in-memory SQLite db with Telegram messages_v2 table and gap."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE messages_v2 (mid INTEGER PRIMARY KEY, uid INTEGER, date INTEGER, data BLOB)")
    
    # Insert rows: 100, 101, 105 (gap from 102 to 104)
    rows = [(100, 1, 1720000000, b"data1"), (101, 1, 1720000001, b"data2"), (105, 1, 1720000005, b"data3")]
    cursor.executemany("INSERT INTO messages_v2 VALUES (?, ?, ?, ?)", rows)
    conn.commit()
    
    raw_bytes = conn.serialize()
    conn.close()
    return raw_bytes


@pytest.mark.unit
def test_tier4_wa_gap_detection_and_labels():
    """Verify WhatsApp ID-gap detection, confidence cap <= 0.30, and weak_hint label."""
    db_bytes = _create_wa_db_with_gap()
    
    findings = detect_tier4_gaps(db_bytes, app_hint="whatsapp", evidence_id="ev_wa", evidence_sha256="wa_sha")
    
    assert len(findings) == 1
    f = findings[0]
    assert f.tier == 4
    assert f.kind == "id_gap"
    assert f.strength == "weak_hint"
    assert f.confidence_score <= 0.30
    assert f.recovered_fields["gap_start"] == 4
    assert f.recovered_fields["gap_end"] == 4
    assert f.recovered_fields["missing_count"] == 1
    # Check mandatory non-deletion limitations
    assert any("ID gaps can arise without deletion" in lim for lim in f.limitations)
    assert any("does not prove that messages existed" in lim for lim in f.limitations)


@pytest.mark.unit
def test_tier4_tg_gap_detection():
    """Verify Telegram ID-gap detection on messages_v2 table."""
    db_bytes = _create_tg_db_with_gap()
    
    findings = detect_tier4_gaps(db_bytes, app_hint="telegram", evidence_id="ev_tg", evidence_sha256="tg_sha")
    
    assert len(findings) == 1
    f = findings[0]
    assert f.tier == 4
    assert f.kind == "id_gap"
    assert f.strength == "weak_hint"
    assert f.confidence_score <= 0.30
    assert f.recovered_fields["gap_start"] == 102
    assert f.recovered_fields["gap_end"] == 104
    assert f.recovered_fields["missing_count"] == 3


@pytest.mark.unit
def test_tier4_suppression_by_stronger_tiers():
    """Verify that if a missing ID in the gap is already explained by stronger tiers, it is suppressed."""
    db_bytes = _create_wa_db_with_gap()
    
    # Gap is at row 4. If row 4 is explained by Tier 1, 2, or 3, suppress!
    findings = detect_tier4_gaps(
        db_bytes,
        app_hint="whatsapp",
        evidence_id="ev_wa",
        evidence_sha256="wa_sha",
        stronger_tier_rowids={4},
    )
    
    assert len(findings) == 0


@pytest.mark.unit
def test_tier4_continuous_sequence_no_findings():
    """Verify continuous sequence yields zero gap findings."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, text_data TEXT)")
    rows = [(1, 10, "Hello"), (2, 10, "World"), (3, 10, "How")]
    cursor.executemany("INSERT INTO message VALUES (?, ?, ?)", rows)
    conn.commit()
    db_bytes = conn.serialize()
    conn.close()

    findings = detect_tier4_gaps(db_bytes, app_hint="whatsapp")
    assert len(findings) == 0
