"""Ground-truth WhatsApp plain dataset generator (DS-01).

Follows master.md R6, R11, R20, and 02_GROUND_TRUTH_DATASETS.md B1:
- Pure deterministic generation based on seeded RNG.
- Modern WhatsApp schema for msgstore.db (verified in docs/FORMAT_NOTES.md).
- Optional legacy wa.db with wa_contacts.
- Media directory with real small Pillow-generated JPEG/PNG files with EXIF variants.
- Comprehensive deletion scenarios (revoked, edited, freelist, slack, WAL, controls, benign gap).
- Self-verification via raw byte search (B1.5).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import PIL

from tools.groundtruth.entities import (
    CONTACT_POOL,
    MESSAGE_TEXT_CORPUS,
    PRIMARY_USER,
    TEST_GROUP,
    TEST_LOCATIONS,
    FictitiousLocation,
    FictitiousPerson,
)
from tools.groundtruth.manifest import (
    DatasetFileInfo,
    DatasetManifest,
    WAContactEntry,
    WAChatEntry,
    WADeletionEntry,
    WAEditEntry,
    WAMessageEntry,
)
from tools.groundtruth.rng import DeterministicRNG
from tools.groundtruth.wa.media import generate_deterministic_image
from tools.groundtruth.wa.schema import MSGSTORE_SCHEMA_SQL, WA_DB_SCHEMA_SQL


def _compute_file_sha256(path: Path) -> Tuple[str, int]:
    """Compute SHA-256 and byte size of a file."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _find_byte_offsets(data: bytes, pattern: bytes) -> List[int]:
    """Find all byte offset occurrences of pattern in raw bytes."""
    offsets = []
    idx = 0
    while True:
        pos = data.find(pattern, idx)
        if pos == -1:
            break
        offsets.append(pos)
        idx = pos + 1
    return offsets


def _normalize_wal_salts(wal_path: Path, salt1: int, salt2: int) -> None:
    """Normalize SQLite WAL salts and recompute checksums for byte-level determinism (R11)."""
    raw = bytearray(wal_path.read_bytes())
    if len(raw) < 32:
        return
    # Header salt at bytes 16..24
    struct.pack_into(">2I", raw, 16, salt1, salt2)
    s1, s2 = 0, 0
    for i in range(0, 24, 8):
        v1, v2 = struct.unpack("<2I", raw[i:i+8])
        s1 = (s1 + v1 + s2) & 0xFFFFFFFF
        s2 = (s2 + v2 + s1) & 0xFFFFFFFF
    struct.pack_into(">2I", raw, 24, s1, s2)

    offset = 32
    page_size = 4096
    frame_len = 24 + page_size
    while offset + frame_len <= len(raw):
        # Frame salt at bytes 8..16 of frame header
        struct.pack_into(">2I", raw, offset + 8, salt1, salt2)
        f_hdr_8 = raw[offset:offset+8]
        f_page = raw[offset+24:offset+frame_len]
        for chunk in (f_hdr_8, f_page):
            for i in range(0, len(chunk), 8):
                v1, v2 = struct.unpack("<2I", chunk[i:i+8])
                s1 = (s1 + v1 + s2) & 0xFFFFFFFF
                s2 = (s2 + v2 + s1) & 0xFFFFFFFF
        struct.pack_into(">2I", raw, offset + 16, s1, s2)
        offset += frame_len
    wal_path.write_bytes(bytes(raw))


def generate_whatsapp_plain_dataset(
    output_dir: Path,
    dataset_id: str = "DS-01",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate the complete WhatsApp plain ground-truth dataset (DS-01)."""
    if seed is None:
        seed = 20261014 if variant == "dev" else 987654321

    rng = DeterministicRNG(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output paths
    db_path = output_dir / "msgstore.db"
    wal_path = output_dir / "msgstore.db-wal"
    wa_db_path = output_dir / "wa.db"
    media_dir = output_dir / "Media" / "WhatsApp Images"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing generated files in target dir
    for old_file in output_dir.glob("msgstore.db*"):
        try:
            old_file.unlink()
        except OSError:
            pass
    if wa_db_path.exists():
        wa_db_path.unlink()

    # -------------------------------------------------------------------------
    # 1. Generate Media Files (B1.3)
    # -------------------------------------------------------------------------
    generated_media = []
    media_files_map: Dict[str, Any] = {}

    # Media file 1: Naive datetime EXIF only
    m1 = generate_deterministic_image(
        rng,
        filename="IMG-20260915-WA0001.jpg",
        relative_path="Media/WhatsApp Images/IMG-20260915-WA0001.jpg",
        img_type="jpeg",
        exif_variant="naive_dt",
    )
    # Media file 2: Offset datetime EXIF (+05:30)
    m2 = generate_deterministic_image(
        rng,
        filename="IMG-20260916-WA0002.jpg",
        relative_path="Media/WhatsApp Images/IMG-20260916-WA0002.jpg",
        img_type="jpeg",
        exif_variant="offset_dt",
    )
    # Media file 3: Full GPS EXIF (Gateway of India)
    loc_gw = TEST_LOCATIONS[0]
    m3 = generate_deterministic_image(
        rng,
        filename="IMG-20260917-WA0003.jpg",
        relative_path="Media/WhatsApp Images/IMG-20260917-WA0003.jpg",
        img_type="jpeg",
        exif_variant="gps_dt",
        lat=loc_gw.latitude,
        lon=loc_gw.longitude,
    )
    # Media file 4: Standard PNG diagram
    m4 = generate_deterministic_image(
        rng,
        filename="IMG-20260918-WA0004.png",
        relative_path="Media/WhatsApp Images/IMG-20260918-WA0004.png",
        img_type="png",
        exif_variant="none",
    )

    for m in (m1, m2, m3, m4):
        target_path = output_dir / m.relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(m.content_bytes)
        generated_media.append(m)
        media_files_map[m.filename] = m

    # -------------------------------------------------------------------------
    # 2. Build Legacy Contacts DB: wa.db (B1.3)
    # -------------------------------------------------------------------------
    wa_conn = sqlite3.connect(wa_db_path)
    wa_conn.executescript(WA_DB_SCHEMA_SQL)
    wa_cursor = wa_conn.cursor()

    wa_cursor.execute("INSERT INTO android_metadata (locale) VALUES ('en_US')")

    contacts_manifest: List[WAContactEntry] = []
    # Primary user contact
    contacts_manifest.append(
        WAContactEntry(
            jid=PRIMARY_USER.jid,
            display_name=PRIMARY_USER.full_name,
            phone_number=PRIMARY_USER.phone_number,
            is_group=False,
        )
    )

    # Contacts from pool
    for idx, c in enumerate(CONTACT_POOL, start=1):
        wa_cursor.execute(
            """
            INSERT INTO wa_contacts (
                jid, is_whatsapp_user, status, number, raw_contact_id, display_name, sort_name
            ) VALUES (?, 1, ?, ?, ?, ?, ?)
            """,
            (
                c.jid,
                f"Available for official inquiry ({c.full_name})",
                c.phone_number,
                idx,
                c.full_name,
                c.full_name.split()[0],
            ),
        )
        contacts_manifest.append(
            WAContactEntry(
                jid=c.jid,
                display_name=c.full_name,
                phone_number=c.phone_number,
                is_group=False,
            )
        )

    wa_conn.commit()
    wa_conn.close()

    # -------------------------------------------------------------------------
    # 3. Build Modern msgstore.db (B1.2)
    # -------------------------------------------------------------------------
    # Use temporary file to allow uncheckpointed WAL snapshotting
    temp_dir = output_dir / ".tmp_gen"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_db_path = temp_dir / "msgstore.db"

    if temp_db_path.exists():
        temp_db_path.unlink()

    conn = sqlite3.connect(temp_db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA page_size = 4096")
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.executescript(MSGSTORE_SCHEMA_SQL)
    cursor = conn.cursor()

    # --- Deletion Control 1: Vacuumed Control (B1.4) ---
    # Insert a message, delete it, and VACUUM so it is strictly unrecoverable
    marker_vacuum_ctrl = rng.unique_marker("VACUUM_CTRL")
    cursor.execute(
        """
        INSERT INTO jid (_id, user, server, raw_string)
        VALUES (9999, '919876549999', 's.whatsapp.net', '919876549999@s.whatsapp.net')
        """
    )
    cursor.execute("INSERT INTO chat (_id, jid_row_id) VALUES (9999, 9999)")
    cursor.execute(
        """
        INSERT INTO message (chat_row_id, from_me, key_id, timestamp, text_data)
        VALUES (9999, 1, 'CTRL_VAC_KEY_01', 1726000000000, ?)
        """,
        (f"Control message before vacuum: {marker_vacuum_ctrl}",),
    )
    conn.commit()
    cursor.execute("DELETE FROM message WHERE key_id = 'CTRL_VAC_KEY_01'")
    cursor.execute("DELETE FROM chat WHERE _id = 9999")
    cursor.execute("DELETE FROM jid WHERE _id = 9999")
    conn.commit()
    cursor.execute("VACUUM")

    # --- Deletion Control 2: Secure Delete Control (B1.4) ---
    # With PRAGMA secure_delete=ON, delete message so cell payload is zeroed
    marker_sec_del_ctrl = rng.unique_marker("SEC_DEL_CTRL")
    cursor.execute("PRAGMA secure_delete = ON")
    cursor.execute(
        """
        INSERT INTO message (chat_row_id, from_me, key_id, timestamp, text_data)
        VALUES (1, 1, 'CTRL_SEC_DEL_KEY_01', 1726000001000, ?)
        """,
        (f"Control message secure delete: {marker_sec_del_ctrl}",),
    )
    conn.commit()
    cursor.execute("DELETE FROM message WHERE key_id = 'CTRL_SEC_DEL_KEY_01'")
    conn.commit()

    # Set secure_delete back to OFF for realistic freelist and slack carving
    cursor.execute("PRAGMA secure_delete = OFF")

    # --- Insert JIDs & Chats ---
    # JID 1: Primary user
    cursor.execute(
        "INSERT INTO jid (user, server, type, raw_string) VALUES (?, ?, 0, ?)",
        (PRIMARY_USER.user_id, PRIMARY_USER.server, PRIMARY_USER.jid),
    )
    primary_jid_id = cursor.lastrowid

    # Contacts 1 to 4:
    # Contact 1 (Rohan), Contact 2 (Priya), Contact 3 (Vikram) -> active 1-on-1 chats
    # Contact 4 (Ananya) -> group member only
    # Contact 5 (Karan) -> Empty chat (0 messages, B1.2 test)
    contact_jid_ids: Dict[str, int] = {}
    for c in CONTACT_POOL:
        cursor.execute(
            "INSERT INTO jid (user, server, type, raw_string) VALUES (?, ?, 0, ?)",
            (c.user_id, c.server, c.jid),
        )
        contact_jid_ids[c.user_id] = cursor.lastrowid

    # Group JID
    cursor.execute(
        "INSERT INTO jid (user, server, type, raw_string) VALUES (?, ?, 1, ?)",
        (TEST_GROUP.group_id, TEST_GROUP.server, TEST_GROUP.jid),
    )
    group_jid_id = cursor.lastrowid

    # Chats table insertion
    # Chat 1: Rohan Sharma (1-on-1)
    cursor.execute("INSERT INTO chat (jid_row_id, subject) VALUES (?, NULL)", (contact_jid_ids["919876540001"],))
    chat_rohan_id = cursor.lastrowid

    # Chat 2: Priya Verma (1-on-1)
    cursor.execute("INSERT INTO chat (jid_row_id, subject) VALUES (?, NULL)", (contact_jid_ids["919876540002"],))
    chat_priya_id = cursor.lastrowid

    # Chat 3: Vikram Patel (1-on-1)
    cursor.execute("INSERT INTO chat (jid_row_id, subject) VALUES (?, NULL)", (contact_jid_ids["919876540003"],))
    chat_vikram_id = cursor.lastrowid

    # Chat 4: Operation Garuda Discussion (Group chat)
    cursor.execute(
        "INSERT INTO chat (jid_row_id, subject) VALUES (?, ?)",
        (group_jid_id, TEST_GROUP.subject),
    )
    chat_group_id = cursor.lastrowid

    # Chat 5: Karan Malhotra (Empty chat: 0 messages per B1.2)
    cursor.execute("INSERT INTO chat (jid_row_id, subject) VALUES (?, NULL)", (contact_jid_ids["919876540005"],))
    chat_empty_id = cursor.lastrowid

    # Insert Group Participants (5 participants: Primary + Rohan + Priya + Vikram + Ananya)
    group_members = [
        (primary_jid_id, 1),                        # Primary user (Admin)
        (contact_jid_ids["919876540001"], 1),       # Rohan (Admin)
        (contact_jid_ids["919876540002"], 0),       # Priya (Member)
        (contact_jid_ids["919876540003"], 0),       # Vikram (Member)
        (contact_jid_ids["919876540004"], 0),       # Ananya (Member)
    ]
    for m_jid_id, rank in group_members:
        cursor.execute(
            """
            INSERT INTO group_participants (group_jid_row_id, user_jid_row_id, rank)
            VALUES (?, ?, ?)
            """,
            (group_jid_id, m_jid_id, rank),
        )

    # -------------------------------------------------------------------------
    # 4. Generate Messages (B1.2: 300-500 messages, >= 4 weeks)
    # -------------------------------------------------------------------------
    # Start: 2026-08-20 09:00:00 UTC (1787216400000 ms)
    # Span: 35 days (5 weeks)
    start_ts_ms = 1787216400000
    current_ts_ms = start_ts_ms

    messages_manifest: List[WAMessageEntry] = []
    chats_meta = [
        {"chat_id": chat_rohan_id, "chat_jid": "919876540001@s.whatsapp.net", "partner_jid_id": contact_jid_ids["919876540001"], "is_group": False},
        {"chat_id": chat_priya_id, "chat_jid": "919876540002@s.whatsapp.net", "partner_jid_id": contact_jid_ids["919876540002"], "is_group": False},
        {"chat_id": chat_vikram_id, "chat_jid": "919876540003@s.whatsapp.net", "partner_jid_id": contact_jid_ids["919876540003"], "is_group": False},
        {"chat_id": chat_group_id, "chat_jid": TEST_GROUP.jid, "partner_jid_id": None, "is_group": True},
    ]

    total_msg_count = 380
    created_messages: List[Dict[str, Any]] = []

    # Keep track of previous messages for quoting
    previous_keys: List[Dict[str, Any]] = []

    for i in range(1, total_msg_count + 1):
        # Time progression: diurnal cycle (advance 10 min to 3 hours between messages, sleep gap at night)
        interval_min = rng.randint(5, 120)
        current_ts_ms += interval_min * 60 * 1000

        # Check hour of day in UTC (assuming approx local time UTC+05:30)
        hour = ((current_ts_ms // (3600 * 1000)) + 5) % 24
        if hour < 7:  # Between midnight and 7 AM, skip to morning
            current_ts_ms += rng.randint(6, 8) * 3600 * 1000

        # Select chat
        chat_meta = rng.choice(chats_meta)
        c_id = chat_meta["chat_id"]
        c_jid = chat_meta["chat_jid"]
        is_grp = chat_meta["is_group"]

        # Determine sender
        from_me = rng.choice([0, 1])
        if is_grp:
            if from_me == 1:
                sender_jid_id = primary_jid_id
                sender_jid_str = PRIMARY_USER.jid
            else:
                chosen_user_id = rng.choice(["919876540001", "919876540002", "919876540003", "919876540004"])
                sender_jid_id = contact_jid_ids[chosen_user_id]
                sender_jid_str = f"{chosen_user_id}@s.whatsapp.net"
        else:
            if from_me == 1:
                sender_jid_id = primary_jid_id
                sender_jid_str = PRIMARY_USER.jid
            else:
                sender_jid_id = chat_meta["partner_jid_id"]
                sender_jid_str = c_jid

        key_id = rng.whatsapp_key_id()
        msg_text = rng.choice(MESSAGE_TEXT_CORPUS)
        msg_type_code = 0
        msg_type_str = "text"
        media_ref_name = None
        quoted_key_id = None
        flags = []

        # Determine if special message type
        # 1. Image message (types 1)
        if i in (25, 80, 160, 240):
            msg_type_code = 1
            msg_type_str = "image"
            media_obj = generated_media[(i // 80) % len(generated_media)]
            media_ref_name = media_obj.filename
            msg_text = f"Check this media attachment ({media_obj.filename})"

        # 2. Audio message (type 2)
        elif i in (50, 190):
            msg_type_code = 2
            msg_type_str = "audio"
            msg_text = "Voice note (0:35)"

        # 3. Location message (type 5)
        elif i in (110, 290):
            msg_type_code = 5
            msg_type_str = "location"
            msg_text = "Current location marker"

        # 4. Quoted reply
        elif i > 10 and rng.random() < 0.12 and previous_keys:
            prev = rng.choice(previous_keys[-8:])
            quoted_key_id = prev["key_id"]
            flags.append("quoted_reply")
            msg_text = f"Replying to earlier note: {rng.choice(MESSAGE_TEXT_CORPUS)}"

        # 5. Forwarded message flag
        if rng.random() < 0.08:
            flags.append("forwarded")

        # 6. Identical-timestamp ties test (B1.2 requirement: test tie-breaker)
        if i in (141, 221, 311) and created_messages:
            current_ts_ms = created_messages[-1]["timestamp"]
            flags.append("timestamp_tie")

        # Insert into message table
        orig_flags = 1 if "forwarded" in flags else 0
        cursor.execute(
            """
            INSERT INTO message (
                chat_row_id, from_me, key_id, sender_jid_row_id, status,
                timestamp, received_timestamp, receipt_server_timestamp,
                message_type, text_data, origination_flags
            ) VALUES (?, ?, ?, ?, 13, ?, ?, ?, ?, ?, ?)
            """,
            (
                c_id,
                from_me,
                key_id,
                sender_jid_id,
                current_ts_ms,
                current_ts_ms + rng.randint(50, 300),
                current_ts_ms + rng.randint(100, 500),
                msg_type_code,
                msg_text,
                orig_flags,
            ),
        )
        msg_row_id = cursor.lastrowid

        # Insert auxiliary tables for media, location, quoted
        if msg_type_code == 1 and media_ref_name:
            m_info = media_files_map[media_ref_name]
            cursor.execute(
                """
                INSERT INTO message_media (
                    message_row_id, chat_row_id, file_path, file_size,
                    media_name, mime_type, file_hash, media_width, media_height
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_row_id,
                    c_id,
                    f"/sdcard/WhatsApp/Media/WhatsApp Images/{m_info.filename}",
                    m_info.size,
                    m_info.filename,
                    m_info.mime_type,
                    m_info.sha256,
                    m_info.width,
                    m_info.height,
                ),
            )
        elif msg_type_code == 2:
            cursor.execute(
                """
                INSERT INTO message_media (
                    message_row_id, chat_row_id, file_path, file_size,
                    media_name, mime_type, media_duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_row_id,
                    c_id,
                    f"/sdcard/WhatsApp/Media/WhatsApp Audio/AUD-202609-{msg_row_id:04d}.opus",
                    14520,
                    f"AUD-202609-{msg_row_id:04d}.opus",
                    "audio/ogg; codecs=opus",
                    35,
                ),
            )
        elif msg_type_code == 5:
            loc = rng.choice(TEST_LOCATIONS)
            cursor.execute(
                """
                INSERT INTO message_location (
                    message_row_id, chat_row_id, latitude, longitude,
                    place_name, place_address
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_row_id,
                    c_id,
                    loc.latitude,
                    loc.longitude,
                    loc.name,
                    loc.address,
                ),
            )
        elif quoted_key_id:
            cursor.execute(
                """
                INSERT INTO message_quoted (
                    message_row_id, chat_row_id, key_id, parent_key_id,
                    sender_jid_row_id, timestamp, text_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_row_id,
                    c_id,
                    key_id,
                    quoted_key_id,
                    sender_jid_id,
                    current_ts_ms - 3600000,
                    "Quoted text snippet",
                ),
            )

        msg_record = {
            "row_id": msg_row_id,
            "key_id": key_id,
            "chat_jid": c_jid,
            "sender_jid": sender_jid_str,
            "from_me": from_me,
            "timestamp": current_ts_ms,
            "text": msg_text,
            "type_code": msg_type_code,
            "type_str": msg_type_str,
            "media_ref": media_ref_name,
            "quoted_of": quoted_key_id,
            "flags": flags,
        }
        created_messages.append(msg_record)
        previous_keys.append({"key_id": key_id, "row_id": msg_row_id})

        messages_manifest.append(
            WAMessageEntry(
                row_id=msg_row_id,
                key_id=key_id,
                chat_jid=c_jid,
                sender_jid=sender_jid_str,
                from_me=from_me,
                ts_raw=current_ts_ms,
                ts_utc_ms=current_ts_ms,
                type=msg_type_str,
                body=msg_text,
                media_ref=media_ref_name,
                quoted_of=quoted_key_id,
                flags=flags,
            )
        )

    # Update last_message_row_id in chats
    for cm in chats_meta:
        cursor.execute(
            """
            SELECT _id, timestamp FROM message
            WHERE chat_row_id = ?
            ORDER BY _id DESC LIMIT 1
            """,
            (cm["chat_id"],),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE chat SET last_message_row_id = ?, sort_timestamp = ? WHERE _id = ?",
                (row[0], row[1], cm["chat_id"]),
            )

    conn.commit()

    # -------------------------------------------------------------------------
    # 5. Deletion & Modification Scenarios (B1.4)
    # -------------------------------------------------------------------------
    deletions_manifest: List[WADeletionEntry] = []
    edits_manifest: List[WAEditEntry] = []

    # Scenario 1: Revoked ("Delete for Everyone", Tier 1)
    # Pick message row 45 to convert into a revoked message
    revoked_target = created_messages[44]
    cursor.execute(
        """
        UPDATE message
        SET message_type = 12, text_data = NULL
        WHERE _id = ?
        """,
        (revoked_target["row_id"],),
    )
    cursor.execute(
        """
        INSERT INTO message_revoked (message_row_id, revoked_key_id)
        VALUES (?, ?)
        """,
        (revoked_target["row_id"], revoked_target["key_id"]),
    )
    # Update manifest message entry to reflect revocation
    messages_manifest[44].type = "revoked"
    messages_manifest[44].body = None
    messages_manifest[44].flags.append("revoked")

    deletions_manifest.append(
        WADeletionEntry(
            case_id="del_01_revoked",
            method="revoked",
            expected_recoverable=True,
            expected_tier="tier_1",
            marker=revoked_target["key_id"],
            original_message_row_id=revoked_target["row_id"],
            original_key_id=revoked_target["key_id"],
            original_body=revoked_target["text"],
            notes="Tier 1 explicit deletion evidence: message_revoked row links to original key_id.",
        )
    )

    # Scenario 2: Edit history (B1.4)
    # Pick message row 75 to edit
    edit_target = created_messages[74]
    original_text_75 = edit_target["text"]
    edited_text_75 = f"Edited update: {original_text_75} (CORRECTED)"
    edit_ts = edit_target["timestamp"] + 180000  # 3 minutes later
    cursor.execute(
        "UPDATE message SET text_data = ? WHERE _id = ?",
        (edited_text_75, edit_target["row_id"]),
    )
    cursor.execute(
        """
        INSERT INTO message_edit_info (message_row_id, original_key_id, edit_type, original_timestamp)
        VALUES (?, ?, 1, ?)
        """,
        (edit_target["row_id"], edit_target["key_id"], edit_target["timestamp"]),
    )
    messages_manifest[74].body = edited_text_75
    messages_manifest[74].flags.append("edited")

    edits_manifest.append(
        WAEditEntry(
            message_row_id=edit_target["row_id"],
            original_key_id=edit_target["key_id"],
            edited_ts=edit_ts,
            original_body=original_text_75,
            edited_body=edited_text_75,
        )
    )

    # Scenario 3: Freelist Deleted (Tier 3: Multi-page deletion moving pages to freelist)
    # Insert 40 messages with large text (600 bytes each) filling ~6 leaf pages, then delete them all
    marker_freelist = rng.unique_marker("FREELIST_DELETED")
    freelist_ids = []
    for f_idx in range(40):
        f_key = f"KEY_FL_{f_idx:03d}"
        f_payload = f"Sensitive transaction ledger {f_idx}: {marker_freelist} " + ("#" * 500)
        cursor.execute(
            """
            INSERT INTO message (
                chat_row_id, from_me, key_id, sender_jid_row_id, status,
                timestamp, message_type, text_data
            ) VALUES (?, 1, ?, ?, 13, ?, 0, ?)
            """,
            (
                chat_priya_id,
                primary_jid_id,
                f_key,
                current_ts_ms + 2000 + f_idx * 10,
                f_payload,
            ),
        )
        freelist_ids.append(cursor.lastrowid)
    conn.commit()

    # Delete all 40 rows: moves leaf pages to SQLite freelist
    cursor.execute(
        f"DELETE FROM message WHERE _id BETWEEN {freelist_ids[0]} AND {freelist_ids[-1]}"
    )
    conn.commit()

    deletions_manifest.append(
        WADeletionEntry(
            case_id="del_03_freelist",
            method="freelist_deleted",
            expected_recoverable=True,
            expected_tier="tier_3",
            marker=marker_freelist,
            original_message_row_id=freelist_ids[0],
            original_key_id="KEY_FL_000",
            original_body=f"Sensitive transaction ledger: {marker_freelist}",
            notes="Tier 3 recoverable from SQLite freelist trunk/leaf pages.",
        )
    )

    # Scenario 4: Benign Gap Control (Tier 4 / weak hint)
    # Jump primary key sequence ahead by 10 to simulate natural autoincrement jump
    # without any actual deletion occurring
    cursor.execute("SELECT MAX(_id) FROM message")
    max_id = cursor.fetchone()[0] or 1000
    cursor.execute(
        """
        INSERT INTO message (
            _id, chat_row_id, from_me, key_id, sender_jid_row_id, status,
            timestamp, message_type, text_data
        ) VALUES (?, ?, 1, 'KEY_GAP_POST', ?, 13, ?, 0, 'Message after sequence jump')
        """,
        (max_id + 11, chat_vikram_id, primary_jid_id, current_ts_ms + 3000),
    )
    conn.commit()

    deletions_manifest.append(
        WADeletionEntry(
            case_id="del_04_benign_gap",
            method="benign_gap",
            expected_recoverable=False,
            expected_tier="tier_4",
            marker="KEY_GAP_POST",
            original_message_row_id=max_id + 1,
            original_key_id=None,
            original_body=None,
            notes="Benign autoincrement ID gap; must NOT be reported as deletion above weak_hint (confidence <= 0.30).",
        )
    )

    # Scenario 5: Slack Deleted (Tier 3: Freeblock inside page)
    # Insert a message into chat 1, commit, then delete only that row.
    # Done as the last operation before WAL mode so no subsequent inserts reclaim this free space.
    marker_slack = rng.unique_marker("SLACK_DELETED")
    cursor.execute(
        """
        INSERT INTO message (
            chat_row_id, from_me, key_id, sender_jid_row_id, status,
            timestamp, message_type, text_data
        ) VALUES (?, 1, 'KEY_SLACK_01', ?, 13, ?, 0, ?)
        """,
        (
            chat_rohan_id,
            primary_jid_id,
            current_ts_ms + 1000,
            f"Confidential slack notes: {marker_slack}",
        ),
    )
    conn.commit()
    slack_row_id = cursor.lastrowid
    cursor.execute("DELETE FROM message WHERE _id = ?", (slack_row_id,))
    conn.commit()

    deletions_manifest.append(
        WADeletionEntry(
            case_id="del_05_slack",
            method="slack_deleted",
            expected_recoverable=True,
            expected_tier="tier_3",
            marker=marker_slack,
            original_message_row_id=slack_row_id,
            original_key_id="KEY_SLACK_01",
            original_body=f"Confidential slack notes: {marker_slack}",
            notes="Tier 3 recoverable from intrapage freeblock / unallocated space.",
        )
    )

    # Manifest control entries
    deletions_manifest.append(
        WADeletionEntry(
            case_id="ctrl_06_vacuumed",
            method="vacuumed_control",
            expected_recoverable=False,
            expected_tier="unrecoverable",
            marker=marker_vacuum_ctrl,
            original_message_row_id=None,
            original_key_id="CTRL_VAC_KEY_01",
            original_body=f"Control message before vacuum: {marker_vacuum_ctrl}",
            notes="Vacuumed control: deleted then VACUUMed; must be reported as not recovered.",
        )
    )
    deletions_manifest.append(
        WADeletionEntry(
            case_id="ctrl_07_secure_delete",
            method="secure_delete_control",
            expected_recoverable=False,
            expected_tier="unrecoverable",
            marker=marker_sec_del_ctrl,
            original_message_row_id=None,
            original_key_id="CTRL_SEC_DEL_KEY_01",
            original_body=f"Control message secure delete: {marker_sec_del_ctrl}",
            notes="Secure delete control: deleted with secure_delete=ON; zero-filled, not recoverable.",
        )
    )

    # -------------------------------------------------------------------------
    # 6. WAL-Resident Scenario (Tier 2) & Uncheckpointed Snapshot
    # -------------------------------------------------------------------------
    # Switch to WAL mode to generate msgstore.db-wal with prior frame version
    cursor.execute("PRAGMA journal_mode = WAL")
    marker_wal = rng.unique_marker("WAL_RESIDENT")

    # Insert message in WAL mode
    cursor.execute(
        """
        INSERT INTO message (
            chat_row_id, from_me, key_id, sender_jid_row_id, status,
            timestamp, message_type, text_data
        ) VALUES (?, 1, 'KEY_WAL_01', ?, 13, ?, 0, ?)
        """,
        (
            chat_rohan_id,
            primary_jid_id,
            current_ts_ms + 4000,
            f"Uncheckpointed WAL draft: {marker_wal}",
        ),
    )
    conn.commit()
    wal_msg_id = cursor.lastrowid

    # Overwrite/update the message in WAL mode: leaves original version in an earlier WAL frame
    cursor.execute(
        """
        UPDATE message
        SET text_data = 'Updated text replacing WAL draft'
        WHERE _id = ?
        """,
        (wal_msg_id,),
    )
    conn.commit()

    # Snapshot temp_db_path and temp_db_path-wal to final output_dir BEFORE closing connection
    # to preserve uncheckpointed WAL frames (R20 / 02_GROUND_TRUTH_DATASETS.md)
    temp_wal_path = temp_dir / "msgstore.db-wal"
    shutil.copy2(temp_db_path, db_path)
    shutil.copy2(temp_wal_path, wal_path)
    wal_salt1 = rng.randint(0x10000000, 0xFFFFFFFF)
    wal_salt2 = rng.randint(0x10000000, 0xFFFFFFFF)
    _normalize_wal_salts(wal_path, wal_salt1, wal_salt2)

    # Close the temp connection and clean temp directory
    conn.close()
    shutil.rmtree(temp_dir, ignore_errors=True)

    deletions_manifest.append(
        WADeletionEntry(
            case_id="del_08_wal_resident",
            method="wal_resident",
            expected_recoverable=True,
            expected_tier="tier_2",
            marker=marker_wal,
            original_message_row_id=wal_msg_id,
            original_key_id="KEY_WAL_01",
            original_body=f"Uncheckpointed WAL draft: {marker_wal}",
            notes="Tier 2 recoverable from uncheckpointed Write-Ahead Log frame prior to checkpoint.",
        )
    )

    # -------------------------------------------------------------------------
    # 7. Self-Verification by Raw-Byte Search (B1.5)
    # -------------------------------------------------------------------------
    raw_db = db_path.read_bytes()
    raw_wal = wal_path.read_bytes()

    # Verify Freelist marker
    fl_offsets = _find_byte_offsets(raw_db, marker_freelist.encode("utf-8"))
    if not fl_offsets:
        raise RuntimeError(f"Self-verification failed (B1.5): Freelists marker {marker_freelist} not found in msgstore.db raw bytes!")

    # Verify Slack marker
    slack_offsets = _find_byte_offsets(raw_db, marker_slack.encode("utf-8"))
    if not slack_offsets:
        raise RuntimeError(f"Self-verification failed (B1.5): Slack marker {marker_slack} not found in msgstore.db raw bytes!")

    # Verify WAL marker in WAL file
    wal_offsets = _find_byte_offsets(raw_wal, marker_wal.encode("utf-8"))
    if not wal_offsets:
        raise RuntimeError(f"Self-verification failed (B1.5): WAL marker {marker_wal} not found in msgstore.db-wal raw bytes!")

    # Verify Vacuumed Control is STRICTLY ABSENT
    vac_db_offsets = _find_byte_offsets(raw_db, marker_vacuum_ctrl.encode("utf-8"))
    vac_wal_offsets = _find_byte_offsets(raw_wal, marker_vacuum_ctrl.encode("utf-8"))
    if vac_db_offsets or vac_wal_offsets:
        raise RuntimeError(f"Self-verification failed (B1.5): Vacuumed control marker {marker_vacuum_ctrl} found in raw bytes!")

    # Verify Secure Delete Control is STRICTLY ABSENT
    sec_db_offsets = _find_byte_offsets(raw_db, marker_sec_del_ctrl.encode("utf-8"))
    sec_wal_offsets = _find_byte_offsets(raw_wal, marker_sec_del_ctrl.encode("utf-8"))
    if sec_db_offsets or sec_wal_offsets:
        raise RuntimeError(f"Self-verification failed (B1.5): Secure delete control marker {marker_sec_del_ctrl} found in raw bytes!")

    # Store discovered byte offsets and page numbers in manifest
    for entry in deletions_manifest:
        if entry.case_id == "del_05_slack":
            entry.byte_offsets = slack_offsets
            entry.page_numbers = [offset // 4096 + 1 for offset in slack_offsets]
        elif entry.case_id == "del_03_freelist":
            entry.byte_offsets = fl_offsets
            entry.page_numbers = [offset // 4096 + 1 for offset in fl_offsets]
        elif entry.case_id == "del_08_wal_resident":
            entry.byte_offsets = wal_offsets
            entry.page_numbers = [offset // 4096 + 1 for offset in wal_offsets]

    # -------------------------------------------------------------------------
    # 8. Compile Manifest & Record Hashes (B1.1, B4.3)
    # -------------------------------------------------------------------------
    files_list = []
    # Primary files
    for p in (db_path, wal_path, wa_db_path):
        sha, sz = _compute_file_sha256(p)
        files_list.append(DatasetFileInfo(path=p.name, sha256=sha, size=sz))

    # Media files
    for mf in generated_media:
        m_path = output_dir / mf.relative_path
        sha, sz = _compute_file_sha256(m_path)
        files_list.append(DatasetFileInfo(path=mf.relative_path, sha256=sha, size=sz))

    chats_manifest = [
        WAChatEntry(
            chat_jid="919876540001@s.whatsapp.net",
            subject=None,
            is_group=False,
            participant_jids=[PRIMARY_USER.jid, "919876540001@s.whatsapp.net"],
            message_count=sum(1 for m in messages_manifest if m.chat_jid == "919876540001@s.whatsapp.net"),
        ),
        WAChatEntry(
            chat_jid="919876540002@s.whatsapp.net",
            subject=None,
            is_group=False,
            participant_jids=[PRIMARY_USER.jid, "919876540002@s.whatsapp.net"],
            message_count=sum(1 for m in messages_manifest if m.chat_jid == "919876540002@s.whatsapp.net"),
        ),
        WAChatEntry(
            chat_jid="919876540003@s.whatsapp.net",
            subject=None,
            is_group=False,
            participant_jids=[PRIMARY_USER.jid, "919876540003@s.whatsapp.net"],
            message_count=sum(1 for m in messages_manifest if m.chat_jid == "919876540003@s.whatsapp.net"),
        ),
        WAChatEntry(
            chat_jid=TEST_GROUP.jid,
            subject=TEST_GROUP.subject,
            is_group=True,
            participant_jids=[PRIMARY_USER.jid, "919876540001@s.whatsapp.net", "919876540002@s.whatsapp.net", "919876540003@s.whatsapp.net", "919876540004@s.whatsapp.net"],
            message_count=sum(1 for m in messages_manifest if m.chat_jid == TEST_GROUP.jid),
        ),
        # Empty chat (0 messages)
        WAChatEntry(
            chat_jid="919876540005@s.whatsapp.net",
            subject=None,
            is_group=False,
            participant_jids=[PRIMARY_USER.jid, "919876540005@s.whatsapp.net"],
            message_count=0,
        ),
    ]

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "pillow": PIL.__version__,
        },
        files=files_list,
        whatsapp={
            "contacts": [c.__dict__ for c in contacts_manifest],
            "chats": [c.__dict__ for c in chats_manifest],
            "messages": [m.__dict__ for m in messages_manifest],
            "deletions": [d.__dict__ for d in deletions_manifest],
            "edits": [e.__dict__ for e in edits_manifest],
        },
        telegram=None,
        shared_entities=[],
        decoys=[],
        controls=[
            {"type": "empty_chat", "chat_jid": "919876540005@s.whatsapp.net", "expected_messages": 0},
            {"type": "vacuumed_control", "marker": marker_vacuum_ctrl, "expected_in_raw_bytes": False},
            {"type": "secure_delete_control", "marker": marker_sec_del_ctrl, "expected_in_raw_bytes": False},
            {"type": "benign_gap", "description": "autoincrement gap with no row deleted", "expected_tier": "tier_4"},
        ],
        encryption=None,
        modelled_vs_observed={
            "wa_schema": "modelled",
            "wa_timestamps": "modelled",
            "wa_deletions": "modelled",
        },
    )

    manifest_path = output_dir / "manifest.json"
    manifest.save(manifest_path)

    return manifest
