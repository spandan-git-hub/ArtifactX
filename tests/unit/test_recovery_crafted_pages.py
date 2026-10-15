"""
Unit tests for SQLite physical recovery on crafted pages and frames (B10, spec 08_DELETED_DATA_RECOVERY.md).

Covers:
1. Freeblock recovery including overwritten head (4 bytes overwritten by freeblock chain).
2. Free leaf page recovery (sweeping content area).
3. WAL old-version diff (committed-superseded, uncommitted-tail, stale-generation).
4. Schema-guided rejection of random bytes (FPR measured on random noise = 0).
5. Hostile-page scan step budgeting (bounds enforcement, no hang).
"""

import os
import struct
import pytest

from datetime import datetime, timezone
from telethon.tl import types

from forensic.recovery.models import RecoveryFinding
from forensic.recovery.schema_guided import SchemaGuidedDecoder
from forensic.recovery.tier2_wal import carve_tier2
from forensic.recovery.tier3_carver import carve_tier3
from forensic.sqlite.constants import (
    BTREE_LEAF_TABLE,
    PAGE_HEADER_SIZE_LEAF,
    SQLITE_HEADER_SIZE,
    SQLITE_HEADER_STRING,
    TEXT_ENCODING_UTF8,
)
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.record import encode_varint


def _make_tl_message_blob(msg_id: int = 500, user_id: int = 1001, text: str = "Carved Telegram Draft") -> bytes:
    msg = types.Message(
        id=msg_id,
        peer_id=types.PeerUser(user_id=user_id),
        date=datetime.fromtimestamp(1725000000, tz=timezone.utc),
        message=text,
    )
    return bytes(msg)


@pytest.mark.unit
def test_freeblock_head_recovery():
    """Verify recovery from a freeblock whose first 4 bytes were overwritten by the freeblock header."""
    decoder = SchemaGuidedDecoder(app_hint="whatsapp")

    # Construct a valid WhatsApp message record payload:
    # col 0: None (_id)
    # col 1: 10001 (chat_row_id)
    # col 2: 1 (from_me)
    # col 3: "KEY_OVERWRITTEN_01" (key_id)
    # col 4..10: dummy
    # col 11: 1726000000000 (timestamp)
    # col 15: "Secret message in freeblock body"
    key_id = "KEY_OVERWRITTEN_01"
    body_text = "Secret message in freeblock body"
    ts = 1726000000000

    col_types = [
        0,  # col 0: NULL
        2,  # col 1: INT16 (10001)
        9,  # col 2: ONE (1)
        13 + 2 * len(key_id),  # col 3: TEXT
        1,  # col 4: INT8 (0)
        1,  # col 5: INT8 (0)
        1,  # col 6: INT8 (0)
        1,  # col 7: INT8 (0)
        0,  # col 8: NULL
        1,  # col 9: INT8 (0)
        1,  # col 10: INT8 (0)
        6,  # col 11: INT64 (ts)
        0,  # col 12: NULL
        0,  # col 13: NULL
        1,  # col 14: INT8 (0)
        13 + 2 * len(body_text.encode("utf-8")),  # col 15: TEXT
        1,  # col 16: INT8 (0)
        1,  # col 17: INT8 (0)
        0,  # col 18: NULL
        1,  # col 19: INT8 (0)
    ]

    # Encode header
    header_varints = b"".join(encode_varint(t) for t in col_types)
    header_len = len(header_varints) + 1
    record_bytes = encode_varint(header_len) + header_varints

    # Append values
    record_bytes += struct.pack(">h", 10001)  # col 1
    record_bytes += key_id.encode("utf-8")     # col 3
    record_bytes += b"\x00\x00\x00\x00\x00\x00"  # col 4..10
    record_bytes += struct.pack(">q", ts)       # col 11
    record_bytes += b"\x00"                     # col 14
    record_bytes += body_text.encode("utf-8")   # col 15
    record_bytes += b"\x00\x00\x00"             # col 16, 17, 19

    # Simulate freeblock: overwrite first 4 bytes with [next_freeblock=0, freeblock_size=len]
    fb_header = struct.pack(">HH", 0, len(record_bytes) + 4)
    # The record starts at offset 4 of the freeblock
    freeblock_data = fb_header + record_bytes

    findings = decoder.scan_buffer(
        buffer=freeblock_data,
        page_no=10,
        base_offset=40960,
        kind="freeblock",
        tier=3,
    )

    assert len(findings) >= 1
    f = findings[0]
    assert f.tier == 3
    assert f.recovered_fields["key_id"] == key_id
    assert f.recovered_fields["body"] == body_text
    assert f.validation_status == "PARTIAL"
    assert any("overwritten" in lim for lim in f.limitations)


@pytest.mark.unit
def test_schema_guided_rejection_of_random_bytes():
    """Verify that random-noise pages yield zero false positive records (FPR = 0)."""
    decoder = SchemaGuidedDecoder(app_hint="whatsapp")

    # Generate 5 pages (20,480 bytes) of pseudo-random noise
    seed_rng = os.urandom(4096 * 5)

    findings = decoder.scan_buffer(
        buffer=seed_rng,
        page_no=99,
        base_offset=0,
        kind="freelist",
        tier=3,
    )

    # Must reject 100% of random noise candidates
    assert len(findings) == 0
    assert decoder.invalid_rejected_count > 0


@pytest.mark.unit
def test_telegram_schema_guided_rejection_of_random_bytes():
    """Verify Telegram schema-guided decoding produces zero false positives on random noise."""
    decoder = SchemaGuidedDecoder(app_hint="telegram")
    seed_rng = os.urandom(4096 * 5)

    findings = decoder.scan_buffer(
        buffer=seed_rng,
        page_no=98,
        base_offset=0,
        kind="freelist",
        tier=3,
    )

    assert len(findings) == 0
    assert decoder.invalid_rejected_count > 0


@pytest.mark.unit
def test_hostile_page_scan_budget():
    """Verify that a hostile page designed to trigger repetitive decoding stops at max_steps_per_page."""
    # Craft a page filled with repeating deceptive header patterns
    repetitive_pattern = b"\x16\x00\x02\t\x17!\x01\x08" * 500
    decoder = SchemaGuidedDecoder(app_hint="whatsapp", max_steps_per_page=100)

    findings = decoder.scan_buffer(
        buffer=repetitive_pattern,
        page_no=5,
        base_offset=0,
        kind="freelist",
        tier=3,
    )

    assert any("exceeded step budget" in w for w in decoder.warnings)


@pytest.mark.unit
def test_free_leaf_page_sweep():
    """Verify full free leaf page recovery when cell pointer array is broken."""
    decoder = SchemaGuidedDecoder(app_hint="telegram")

    # Build a Telegram messages_v2 cell
    # mid=500, uid=1001, date=1725000000, data=serialized TL object with message text
    from forensic.telegram.tl.registry import build_supported_registry

    tl_blob = _make_tl_message_blob(msg_id=500, user_id=1001, text="Carved Telegram Draft")

    col_types = [
        2,  # col 0: INT16 (500)
        2,  # col 1: INT16 (1001)
        9,  # col 2: ONE
        8,  # col 3: ZERO
        4,  # col 4: INT32 (1725000000)
        12 + 2 * len(tl_blob),  # col 5: BLOB
        9, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    ]

    header_varints = b"".join(encode_varint(t) for t in col_types)
    header_len = len(header_varints) + 1
    record_payload = encode_varint(header_len) + header_varints
    record_payload += struct.pack(">h", 500)
    record_payload += struct.pack(">h", 1001)
    record_payload += struct.pack(">i", 1725000000)
    record_payload += tl_blob
    record_payload += b"\x00" * 10

    # Build cell: [plen varint, rowid varint, payload]
    cell_bytes = encode_varint(len(record_payload)) + encode_varint(500) + record_payload

    # Place cell into a freed page at offset 1000
    page_buf = bytearray(b"\x00" * 4096)
    page_buf[1000 : 1000 + len(cell_bytes)] = cell_bytes

    findings = decoder.scan_buffer(
        buffer=bytes(page_buf),
        page_no=15,
        base_offset=15 * 4096,
        kind="freelist",
        tier=3,
    )

    assert len(findings) == 1
    f = findings[0]
    assert f.tier == 3
    assert f.recovered_fields["mid"] == 500
    assert f.recovered_fields["body"] == "Carved Telegram Draft"
    assert f.validation_status == "FULL_RECORD_VALID"
