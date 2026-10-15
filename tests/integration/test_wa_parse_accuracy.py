"""
Integration test for WhatsApp parse accuracy vs ground-truth manifest (spec B7.6).
Evaluates DS-01-dev, DS-01-holdout, and decrypted DS-02/DS-03.
Target accuracy: >= 0.99 (synthetic target 1.00).
"""

import json
from pathlib import Path

import pytest

from forensic.decryption.orchestrator import DecryptionOrchestrator, KeyMaterial
from forensic.whatsapp.parser import WhatsAppParser


def test_wa_parse_accuracy_ds01_dev():
    """Verify parse accuracy on DS-01-dev plaintext fixture vs manifest."""
    manifest_path = Path("testdata/DS-01-dev/manifest.json")
    db_path = Path("testdata/DS-01-dev/msgstore.db")
    wa_db_path = Path("testdata/DS-01-dev/wa.db")

    if not manifest_path.exists() or not db_path.exists():
        pytest.skip("DS-01-dev fixture not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exp_messages = manifest["whatsapp"]["messages"]
    exp_edits = manifest["whatsapp"]["edits"]
    exp_revocations = [d for d in manifest["whatsapp"]["deletions"] if d["method"] == "revoked"]

    parser = WhatsAppParser(db_path, evidence_id="ev_ds01_dev", wa_db_source=wa_db_path)
    result = parser.parse()

    # Provenance assertions (exit criterion: no None source_table/row_id for DB rows)
    for m in result.messages:
        assert m.provenance.source_table == "message"
        assert m.provenance.row_id is not None
        assert m.provenance.evidence_id == "ev_ds01_dev"

    for c in result.chats:
        assert c.provenance.source_table == "chat"
        assert c.provenance.row_id is not None

    for r in result.revocations:
        assert r.provenance.source_table == "message_revoked"
        assert r.provenance.row_id is not None

    for e in result.edits:
        assert e.provenance.source_table == "message_edit_info"
        assert e.provenance.row_id is not None

    # Map parsed messages by key_id
    parsed_map = {m.key_id: m for m in result.messages}
    misses = []

    for em in exp_messages:
        key_id = em["key_id"]
        pm = parsed_map.get(key_id)
        if not pm:
            misses.append(f"Missing key_id: {key_id}")
            continue

        # Check fields: sender, ts_utc_ms, body, type, chat
        if pm.sender_jid != em["sender_jid"]:
            misses.append(f"Sender mismatch for {key_id}: got {pm.sender_jid}, expected {em['sender_jid']}")
        if pm.ts_utc_ms != em["ts_utc_ms"]:
            misses.append(f"Timestamp mismatch for {key_id}: got {pm.ts_utc_ms}, expected {em['ts_utc_ms']}")
        if pm.message_type_name != em["type"]:
            misses.append(f"Type mismatch for {key_id}: got {pm.message_type_name}, expected {em['type']}")
        if pm.text != em["body"]:
            misses.append(f"Body mismatch for {key_id}: got {pm.text!r}, expected {em['body']!r}")
        if pm.chat_jid != em["chat_jid"]:
            misses.append(f"Chat mismatch for {key_id}: got {pm.chat_jid}, expected {em['chat_jid']}")

    accuracy = (len(exp_messages) - len(misses)) / len(exp_messages)
    assert len(misses) == 0, f"Parse misses (accuracy={accuracy:.4f}): {misses[:10]}"
    assert accuracy >= 0.99
    assert accuracy == 1.0  # Synthetic target 100%

    # Verify revocations and edits
    assert len(result.revocations) == len(exp_revocations)
    assert len(result.edits) == len(exp_edits)

    # Verify specific edge cases
    # 1. Unicode & emojis
    unicode_msgs = [m for m in result.messages if m.text and ("नमस्कार" in m.text or "🚀✨" in m.text)]
    assert len(unicode_msgs) > 0, "Unicode/emoji message verification failed"

    # 2. Quoted reply
    quoted_msgs = [m for m in result.messages if "quoted_reply" in m.flags]
    assert len(quoted_msgs) > 0
    assert quoted_msgs[0].quoted_ref is not None
    assert quoted_msgs[0].quoted_ref.parent_key_id is not None

    # 3. Location messages
    loc_msgs = [m for m in result.messages if m.message_type_name == "location"]
    assert len(loc_msgs) > 0
    assert loc_msgs[0].location_ref is not None
    assert loc_msgs[0].location_ref.latitude != 0.0

    # 4. Empty chat (0 messages, Karan Malhotra)
    empty_chats = [c for c in result.chats if c.chat_jid == "919876540005@s.whatsapp.net"]
    assert len(empty_chats) == 1
    assert empty_chats[0].last_message_row_id is None or empty_chats[0].last_message_row_id == 0

    # 5. Revoked message body is None and flag present
    revoked_target = parsed_map[exp_revocations[0]["marker"]]
    assert revoked_target.text is None
    assert "revoked" in revoked_target.flags
    assert revoked_target.message_type_name == "revoked"


def test_wa_parse_accuracy_ds01_holdout():
    """Verify parse accuracy on DS-01-holdout plaintext fixture vs manifest."""
    manifest_path = Path("testdata/DS-01-holdout/manifest.json")
    db_path = Path("testdata/DS-01-holdout/msgstore.db")
    wa_db_path = Path("testdata/DS-01-holdout/wa.db")

    if not manifest_path.exists() or not db_path.exists():
        pytest.skip("DS-01-holdout fixture not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exp_messages = manifest["whatsapp"]["messages"]

    parser = WhatsAppParser(db_path, evidence_id="ev_ds01_holdout", wa_db_source=wa_db_path)
    result = parser.parse()

    parsed_map = {m.key_id: m for m in result.messages}
    misses = []
    for em in exp_messages:
        key_id = em["key_id"]
        pm = parsed_map.get(key_id)
        if not pm or pm.sender_jid != em["sender_jid"] or pm.ts_utc_ms != em["ts_utc_ms"] or pm.message_type_name != em["type"] or pm.text != em["body"] or pm.chat_jid != em["chat_jid"]:
            misses.append(key_id)

    accuracy = (len(exp_messages) - len(misses)) / len(exp_messages)
    assert len(misses) == 0, f"Holdout misses: {misses[:10]}"
    assert accuracy == 1.0


def test_wa_parse_decrypt_pipeline_ds02_crypt14():
    """Verify end-to-end decryption followed by parsing on DS-02-dev (Crypt14)."""
    c14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    key_path = Path("testdata/DS-02-dev/keys/key")
    manifest_path = Path("testdata/DS-01-dev/manifest.json")

    if not c14_path.exists() or not key_path.exists():
        pytest.skip("DS-02-dev fixtures not found")

    c14_bytes = c14_path.read_bytes()
    key_bytes = key_path.read_bytes()

    decrypted_bytes, _ = DecryptionOrchestrator.decrypt(
        c14_bytes,
        KeyMaterial(key_file_bytes=key_bytes),
        filename="msgstore.db.crypt14",
    )

    parser = WhatsAppParser(decrypted_bytes, evidence_id="ev_ds02_dev")
    result = parser.parse()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exp_messages = manifest["whatsapp"]["messages"]
    parsed_map = {m.key_id: m for m in result.messages}

    misses = [
        em["key_id"]
        for em in exp_messages
        if not (
            (pm := parsed_map.get(em["key_id"]))
            and pm.sender_jid == em["sender_jid"]
            and pm.ts_utc_ms == em["ts_utc_ms"]
            and pm.message_type_name == em["type"]
            and pm.text == em["body"]
            and pm.chat_jid == em["chat_jid"]
        )
    ]
    assert len(misses) == 0


def test_wa_parse_decrypt_pipeline_ds03_crypt15():
    """Verify end-to-end decryption followed by parsing on DS-03-dev (Crypt15)."""
    c15_path = Path("testdata/DS-03-dev/msgstore.db.crypt15")
    root_key_path = Path("testdata/DS-03-dev/keys/root_key.hex")
    manifest_path = Path("testdata/DS-01-dev/manifest.json")

    if not c15_path.exists() or not root_key_path.exists():
        pytest.skip("DS-03-dev fixtures not found")

    c15_bytes = c15_path.read_bytes()
    root_hex = root_key_path.read_text().strip()

    decrypted_bytes, _ = DecryptionOrchestrator.decrypt(
        c15_bytes,
        KeyMaterial(key_hex=root_hex),
        filename="msgstore.db.crypt15",
    )

    parser = WhatsAppParser(decrypted_bytes, evidence_id="ev_ds03_dev")
    result = parser.parse()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exp_messages = manifest["whatsapp"]["messages"]
    parsed_map = {m.key_id: m for m in result.messages}

    misses = [
        em["key_id"]
        for em in exp_messages
        if not (
            (pm := parsed_map.get(em["key_id"]))
            and pm.sender_jid == em["sender_jid"]
            and pm.ts_utc_ms == em["ts_utc_ms"]
            and pm.message_type_name == em["type"]
            and pm.text == em["body"]
            and pm.chat_jid == em["chat_jid"]
        )
    ]
    assert len(misses) == 0
