"""
Unit tests for recovery deduplication and validation status (B10.5, spec 08_DELETED_DATA_RECOVERY.md).

Covers:
1. Live row deduplication: records matching live rows marked DUPLICATE_OF_LIVE and retained.
2. Cross-tier deduplication: stronger tier wins, weaker tier marked DUPLICATE_OF_OTHER_TIER.
3. Deterministic sort ordering: (tier, table, page_no, byte_offset, row_id, finding_id).
4. Live row index generation for WhatsApp and Telegram databases.
"""

import random
import sqlite3
import pytest

from forensic.common.contracts import Provenance
from forensic.recovery.deduplication import (
    build_live_row_index,
    deduplicate_and_sort_findings,
    get_finding_identity_key,
)
from forensic.recovery.models import RecoveryFinding


def _make_dummy_finding(
    finding_id: str,
    tier: int,
    table_name: str,
    page_no: int = 1,
    byte_offset: int = 100,
    row_id: int | None = 10,
    key_id: str | None = None,
    mid: int | None = None,
    uid: int | None = None,
    kind: str = "slack",
    status: str = "FULL_RECORD_VALID",
) -> RecoveryFinding:
    rf = {}
    if key_id:
        rf["key_id"] = key_id
    if mid is not None:
        rf["mid"] = mid
    if uid is not None:
        rf["uid"] = uid

    return RecoveryFinding(
        finding_id=finding_id,
        confidence_score=0.85,
        strength="strong",
        limitations=("test limitation",),
        provenance=Provenance(
            evidence_id="ev1",
            evidence_sha256="sha1",
            source_table=table_name,
            row_id=row_id,
            method="test_method",
        ),
        tier=tier,
        kind=kind,
        validation_status=status,
        table_name=table_name,
        row_id=row_id,
        page_no=page_no,
        byte_offset=byte_offset,
        recovered_fields=rf,
        raw_payload_hash="dummy_hash",
        raw_payload_preview="dummy_preview",
    )


@pytest.mark.unit
def test_live_row_dedup_retained_with_duplicate_status():
    """Verify that a finding matching an active live row is retained as DUPLICATE_OF_LIVE."""
    live_keys = {"KEY_LIVE_123", "rowid:55"}

    finding = _make_dummy_finding(
        finding_id="f_live",
        tier=3,
        table_name="message",
        key_id="KEY_LIVE_123",
        row_id=55,
    )

    result = deduplicate_and_sort_findings([finding], live_keys=live_keys)
    assert len(result) == 1
    assert result[0].validation_status == "DUPLICATE_OF_LIVE"
    assert any("not counted as deleted" in lim for lim in result[0].limitations)


@pytest.mark.unit
def test_cross_tier_deduplication():
    """Verify that stronger tier (e.g. Tier 2) takes precedence over weaker tier (Tier 3)."""
    # Finding 1 in Tier 2
    f_tier2 = _make_dummy_finding(
        finding_id="f_t2",
        tier=2,
        table_name="message",
        key_id="MSG_SHARED_KEY",
        row_id=10,
        page_no=2,
        byte_offset=50,
    )

    # Finding 2 in Tier 3 (same key)
    f_tier3 = _make_dummy_finding(
        finding_id="f_t3",
        tier=3,
        table_name="message",
        key_id="MSG_SHARED_KEY",
        row_id=10,
        page_no=5,
        byte_offset=200,
    )

    # Pass in reverse tier order
    result = deduplicate_and_sort_findings([f_tier3, f_tier2], live_keys=set())

    assert len(result) == 2
    # Tier 2 finding is first and remains FULL_RECORD_VALID
    assert result[0].finding_id == "f_t2"
    assert result[0].validation_status == "FULL_RECORD_VALID"

    # Tier 3 finding is marked DUPLICATE_OF_OTHER_TIER
    assert result[1].finding_id == "f_t3"
    assert result[1].validation_status == "DUPLICATE_OF_OTHER_TIER"
    assert any("superseded by stronger finding in Tier 2" in lim for lim in result[1].limitations)


@pytest.mark.unit
def test_deterministic_sorting():
    """Verify findings are sorted deterministically regardless of input order."""
    f1 = _make_dummy_finding(finding_id="f1", tier=1, table_name="message", page_no=1, byte_offset=10, row_id=1)
    f2 = _make_dummy_finding(finding_id="f2", tier=2, table_name="message", page_no=2, byte_offset=20, row_id=2)
    f3 = _make_dummy_finding(finding_id="f3", tier=3, table_name="message", page_no=3, byte_offset=30, row_id=3)
    f4 = _make_dummy_finding(finding_id="f4", tier=4, table_name="message", page_no=4, byte_offset=40, row_id=4)

    expected_ids = ["f1", "f2", "f3", "f4"]

    rng = random.Random(42)
    for _ in range(10):
        shuffled = [f1, f2, f3, f4]
        rng.shuffle(shuffled)
        sorted_res = deduplicate_and_sort_findings(shuffled, live_keys=set())
        assert [f.finding_id for f in sorted_res] == expected_ids


@pytest.mark.unit
def test_build_live_row_index_wa_and_tg():
    """Verify build_live_row_index indexes live rows from SQLite databases."""
    # Test WhatsApp DB
    conn_wa = sqlite3.connect(":memory:")
    c_wa = conn_wa.cursor()
    c_wa.execute("CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, key_id TEXT, timestamp INTEGER, text_data TEXT)")
    c_wa.execute("INSERT INTO message VALUES (1, 10, 'KEY_WA_01', 1700000000, 'Test body')")
    conn_wa.commit()
    wa_bytes = conn_wa.serialize()
    conn_wa.close()

    wa_keys = build_live_row_index(wa_bytes, app_hint="whatsapp")
    assert "KEY_WA_01" in wa_keys
    assert "rowid:1" in wa_keys

    # Test Telegram DB
    conn_tg = sqlite3.connect(":memory:")
    c_tg = conn_tg.cursor()
    c_tg.execute("CREATE TABLE messages_v2 (mid INTEGER PRIMARY KEY, uid INTEGER, date INTEGER, data BLOB)")
    c_tg.execute("INSERT INTO messages_v2 VALUES (500, 1001, 1720000000, X'DEADBEEF')")
    conn_tg.commit()
    tg_bytes = conn_tg.serialize()
    conn_tg.close()

    tg_keys = build_live_row_index(tg_bytes, app_hint="telegram")
    assert (1001, 500) in tg_keys
    assert 500 in tg_keys
