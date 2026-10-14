"""Unit tests for Telegram ground-truth dataset generator and fixtures (B3).

Follows master.md R1, R6, R7, R11, R13, R20, and 15_TESTING_STANDARDS.md.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from telethon.extensions import BinaryReader
from telethon.tl import types

from tools.groundtruth.tg.generator import generate_telegram_dataset
from tools.groundtruth.verify_dataset import verify_dataset


@pytest.mark.unit
def test_telegram_dataset_build_and_schema(tmp_path: Path) -> None:
    """B3.1: Build DS-05 and verify realistic schema matching MessagesStorage.java."""
    out_dir = tmp_path / "DS-05-test"
    manifest = generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=12345)

    assert manifest.dataset_id == "DS-05"
    assert manifest.origin == "synthetic"
    assert manifest.telegram is not None
    assert len(manifest.telegram["messages"]) >= 300
    assert len(manifest.telegram["users"]) >= 4
    assert len(manifest.telegram["chats"]) >= 1

    db_path = out_dir / "cache4.db"
    assert db_path.is_file()
    wal_path = out_dir / "cache4.db-wal"
    assert wal_path.is_file()

    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    cursor = conn.cursor()

    # Check user_version == 155 (MessagesStorage.LAST_DB_VERSION)
    cursor.execute("PRAGMA user_version")
    ver = cursor.fetchone()[0]
    assert ver == 155

    # Check realistic tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0].lower() for row in cursor.fetchall()}
    expected_tables = {
        "messages_v2",
        "dialogs",
        "users",
        "chats",
        "contacts",
        "user_contacts_v7",
        "user_phones_v7",
        "media_v4",
        "chat_settings_v2",
        "user_settings",
        "enc_chats",
        "messages_holes",
        "scheduled_messages_v2",
        "params",
        "search_recent",
    }
    for t in expected_tables:
        assert t in tables, f"Expected table {t} missing from cache4.db"

    # Check messages_v2 columns
    cursor.execute("PRAGMA table_info(messages_v2)")
    cols = {row[1] for row in cursor.fetchall()}
    for c in ["mid", "uid", "read_state", "send_state", "date", "data", "out", "ttl", "media", "reply_to_message_id"]:
        assert c in cols, f"Column {c} missing from messages_v2"

    conn.close()


@pytest.mark.unit
def test_telegram_tl_blobs_reread_100_percent(tmp_path: Path) -> None:
    """B3.4: Telethon must re-read 100% of well-formed generated blobs."""
    out_dir = tmp_path / "DS-05-tl"
    manifest = generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=77777)

    db_path = out_dir / "cache4.db"
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    cursor = conn.cursor()

    # 1. Verify Users
    cursor.execute("SELECT uid, data FROM users")
    user_rows = cursor.fetchall()
    assert len(user_rows) >= 4
    for uid, u_blob in user_rows:
        reader = BinaryReader(u_blob)
        user_obj = reader.tgread_object()
        assert isinstance(user_obj, types.User)
        assert user_obj.id == uid

    # 2. Verify Chats
    cursor.execute("SELECT uid, data FROM chats")
    chat_rows = cursor.fetchall()
    assert len(chat_rows) >= 1
    for cid, c_blob in chat_rows:
        reader = BinaryReader(c_blob)
        chat_obj = reader.tgread_object()
        assert isinstance(chat_obj, (types.Chat, types.Channel))
        assert chat_obj.id == cid

    # 3. Verify Messages
    manifest_messages = {m["mid"]: m for m in manifest.telegram["messages"]}
    cursor.execute("SELECT mid, data FROM messages_v2")
    msg_rows = cursor.fetchall()

    re_read_targets = 0
    re_read_successes = 0

    for mid, blob in msg_rows:
        m_meta = manifest_messages.get(mid)
        if not m_meta:
            continue
        variant = m_meta.get("blob_variant", "exact")
        reader = BinaryReader(blob)

        if variant in ("exact", "trailing_bytes"):
            re_read_targets += 1
            msg_obj = reader.tgread_object()
            assert msg_obj.id == mid
            if m_meta["text"] is not None:
                assert msg_obj.message == m_meta["text"]
            re_read_successes += 1

    conn.close()

    assert re_read_targets > 0
    assert re_read_successes == re_read_targets
    re_read_pct = re_read_successes / re_read_targets
    assert re_read_pct == 1.0


@pytest.mark.unit
def test_telegram_documented_blob_variants(tmp_path: Path) -> None:
    """B3.2: Verify documented blob variants (exact, trailing bytes, unknown, older layer)."""
    out_dir = tmp_path / "DS-05-variants"
    manifest = generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=88888)

    variants = {v["variant"]: v for v in manifest.telegram["blob_variants"]}
    assert "trailing_bytes" in variants
    assert "unknown_constructor" in variants
    assert "older_layer" in variants

    db_path = out_dir / "cache4.db"
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    cursor = conn.cursor()

    # Trailing bytes: Telethon must parse the message object cleanly
    tb_meta = variants["trailing_bytes"]
    cursor.execute("SELECT data FROM messages_v2 WHERE mid = ?", (tb_meta["mid"],))
    tb_blob = cursor.fetchone()[0]
    tb_reader = BinaryReader(tb_blob)
    parsed_tb = tb_reader.tgread_object()
    assert parsed_tb.id == tb_meta["mid"]
    assert tb_reader.tell_position() < len(tb_blob)  # Unread trailing bytes detected

    # Unknown constructor (0xDEADBEEF): must raise exception / fail to parse
    unk_meta = variants["unknown_constructor"]
    cursor.execute("SELECT data FROM messages_v2 WHERE mid = ?", (unk_meta["mid"],))
    unk_blob = cursor.fetchone()[0]
    with pytest.raises(Exception):
        BinaryReader(unk_blob).tgread_object()

    # Older layer constructor (0x38114EE2): must raise exception / fail in current layer
    old_meta = variants["older_layer"]
    cursor.execute("SELECT data FROM messages_v2 WHERE mid = ?", (old_meta["mid"],))
    old_blob = cursor.fetchone()[0]
    with pytest.raises(Exception):
        BinaryReader(old_blob).tgread_object()

    conn.close()


@pytest.mark.unit
def test_telegram_deletions_and_controls(tmp_path: Path) -> None:
    """B3.3: Verify freelist, slack, WAL-resident deletions and vacuum/secure_delete controls."""
    out_dir = tmp_path / "DS-05-del"
    manifest = generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=99999)

    deletions = {d["method"]: d for d in manifest.telegram["deletions"]}
    assert "freelist_deleted" in deletions
    assert "slack_deleted" in deletions
    assert "wal_resident" in deletions
    assert "vacuumed_control" in deletions
    assert "secure_delete_control" in deletions
    assert "benign_gap" in deletions

    db_path = out_dir / "cache4.db"
    wal_path = out_dir / "cache4.db-wal"
    raw_db = db_path.read_bytes()
    raw_wal = wal_path.read_bytes()

    # Recoverable markers must be present
    assert deletions["freelist_deleted"]["marker"].encode("utf-8") in raw_db
    assert deletions["slack_deleted"]["marker"].encode("utf-8") in raw_db
    assert deletions["wal_resident"]["marker"].encode("utf-8") in raw_wal

    # Controls must be strictly absent
    assert deletions["vacuumed_control"]["marker"].encode("utf-8") not in raw_db
    assert deletions["vacuumed_control"]["marker"].encode("utf-8") not in raw_wal
    assert deletions["secure_delete_control"]["marker"].encode("utf-8") not in raw_db
    assert deletions["secure_delete_control"]["marker"].encode("utf-8") not in raw_wal

    # Benign gap tier
    assert deletions["benign_gap"]["expected_recoverable"] is False
    assert deletions["benign_gap"]["expected_tier"] == "tier_4"


@pytest.mark.unit
def test_telegram_empty_chat_control(tmp_path: Path) -> None:
    """Empty dialog control: uid 1005 has 0 messages."""
    out_dir = tmp_path / "DS-05-empty"
    generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=11111)

    db_path = out_dir / "cache4.db"
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages_v2 WHERE uid = 1005")
    cnt = cursor.fetchone()[0]
    conn.close()
    assert cnt == 0


@pytest.mark.unit
def test_telegram_generator_determinism(tmp_path: Path) -> None:
    """R11: Deterministic generation: same seed yields byte-identical files."""
    dir1 = tmp_path / "DS-05-det1"
    dir2 = tmp_path / "DS-05-det2"

    m1 = generate_telegram_dataset(dir1, dataset_id="DS-05", variant="dev", seed=55555)
    m2 = generate_telegram_dataset(dir2, dataset_id="DS-05", variant="dev", seed=55555)

    assert len(m1.files) == len(m2.files)
    for f1, f2 in zip(m1.files, m2.files):
        assert f1.path == f2.path
        assert f1.sha256 == f2.sha256
        assert f1.size == f2.size
        # Verify file bytes on disk are identical
        assert (dir1 / f1.path).read_bytes() == (dir2 / f2.path).read_bytes()


@pytest.mark.unit
def test_telegram_verify_dataset_detects_tamper(tmp_path: Path) -> None:
    """Verify verify_dataset detects file tampering and byte flips in Telegram datasets."""
    out_dir = tmp_path / "DS-05-tamper"
    generate_telegram_dataset(out_dir, dataset_id="DS-05", variant="dev", seed=66666)

    # Clean verification passes
    is_valid, errors = verify_dataset(out_dir)
    assert is_valid is True
    assert len(errors) == 0

    # Flip 1 byte in cache4.db
    db_path = out_dir / "cache4.db"
    raw = bytearray(db_path.read_bytes())
    raw[100] ^= 0xFF
    db_path.write_bytes(bytes(raw))

    is_valid_tampered, errors_tampered = verify_dataset(out_dir)
    assert is_valid_tampered is False
    assert any("SHA-256 mismatch" in e for e in errors_tampered)
