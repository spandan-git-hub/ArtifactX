"""Telegram ground-truth dataset generator (DS-05).

Generates realistic cache4.db (+ -wal, -shm) with genuine MTProto TL blobs,
realistic tables verified per MessagesStorage.java (R20), documented blob variants,
SQLite deletion scenarios (freelist, slack, WAL-resident), and controls.

Follows master.md R1, R6, R11, R14, R20, and 02_GROUND_TRUTH_DATASETS.md §4.
"""

from __future__ import annotations

import datetime
import os
import shutil
import sqlite3
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from telethon import __version__ as telethon_version
from telethon.extensions import BinaryReader
from telethon.tl import types
from telethon.tl.alltlobjects import LAYER as TELETHON_LAYER

from tools.groundtruth.entities import TEST_LOCATIONS

from tools.groundtruth.manifest import (
    DatasetFileInfo,
    DatasetManifest,
    TGBlobVariantEntry,
    TGChatEntry,
    TGDeletionEntry,
    TGEditEntry,
    TGMessageEntry,
    TGUserEntry,
)
from tools.groundtruth.rng import DeterministicRNG


# Telethon / MTProto Constructor Constants
CONSTRUCTOR_UNKNOWN = 0xDEADBEEF
CONSTRUCTOR_LAYER133_MESSAGE = 0x38114EE2


def _find_byte_offsets(data: bytes, pattern: bytes) -> List[int]:
    """Find all byte offset occurrences of pattern in data."""
    offsets: List[int] = []
    idx = 0
    while True:
        pos = data.find(pattern, idx)
        if pos == -1:
            break
        offsets.append(pos)
        idx = pos + 1
    return offsets


def _normalize_wal_salts(wal_path: Path, salt1: int, salt2: int) -> None:
    """Normalize SQLite WAL salts and recompute checksums for byte-level determinism (R11, DEC-022)."""
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


def generate_telegram_dataset(
    output_dir: Path,
    dataset_id: str = "DS-05",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate the complete Telegram ground-truth dataset (DS-05)."""
    if seed is None:
        seed = 20261015 if variant == "dev" else 876543210

    rng = DeterministicRNG(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "cache4.db"
    wal_path = output_dir / "cache4.db-wal"
    shm_path = output_dir / "cache4.db-shm"

    # Temporary directory for building WAL state before snapshot
    temp_dir = output_dir / "_temp_build"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_db_path = temp_dir / "cache4.db"

    # Clean previous output files
    for p in (db_path, wal_path, shm_path, temp_db_path):
        if p.is_file():
            p.unlink()

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Disable secure_delete so deleted records remain in freelist/slack
    cursor.execute("PRAGMA secure_delete = OFF")
    cursor.execute("PRAGMA page_size = 4096")
    cursor.execute("PRAGMA user_version = 155")  # MessagesStorage.LAST_DB_VERSION

    # -------------------------------------------------------------------------
    # 1. Realistic Schema Creation (verified per MessagesStorage.java)
    # -------------------------------------------------------------------------
    cursor.executescript(
        """
        -- Messages v2 (Primary message storage)
        CREATE TABLE messages_v2 (
            mid INTEGER,
            uid INTEGER,
            read_state INTEGER,
            send_state INTEGER,
            date INTEGER,
            data BLOB,
            out INTEGER,
            ttl INTEGER,
            media INTEGER,
            replydata BLOB,
            imp INTEGER,
            mention INTEGER,
            forwards INTEGER,
            replies_data BLOB,
            thread_reply_id INTEGER,
            is_channel INTEGER,
            reply_to_message_id INTEGER,
            custom_params BLOB,
            group_id INTEGER,
            reply_to_story_id INTEGER,
            PRIMARY KEY(mid, uid)
        );
        CREATE INDEX IF NOT EXISTS uid_mid_read_out_idx_messages_v2 ON messages_v2(uid, mid, read_state, out);
        CREATE INDEX IF NOT EXISTS uid_date_mid_idx_messages_v2 ON messages_v2(uid, date, mid);
        CREATE INDEX IF NOT EXISTS mid_out_idx_messages_v2 ON messages_v2(mid, out);
        CREATE INDEX IF NOT EXISTS reply_to_idx_messages_v2 ON messages_v2(mid, reply_to_message_id);

        -- Dialogs (Conversation index)
        CREATE TABLE dialogs (
            did INTEGER PRIMARY KEY,
            date INTEGER,
            unread_count INTEGER,
            last_mid INTEGER,
            inbox_max INTEGER,
            outbox_max INTEGER,
            last_mid_i INTEGER,
            unread_count_i INTEGER,
            pts INTEGER,
            date_i INTEGER,
            pinned INTEGER,
            flags INTEGER,
            folder_id INTEGER,
            data BLOB,
            unread_reactions INTEGER,
            last_mid_group INTEGER,
            ttl_period INTEGER
        );
        CREATE INDEX IF NOT EXISTS date_idx_dialogs ON dialogs(date);
        CREATE INDEX IF NOT EXISTS last_mid_idx_dialogs ON dialogs(last_mid);

        -- Users & Contacts
        CREATE TABLE users (
            uid INTEGER PRIMARY KEY,
            name TEXT,
            status INTEGER,
            data BLOB
        );
        CREATE TABLE contacts (
            uid INTEGER PRIMARY KEY,
            mutual INTEGER
        );
        CREATE TABLE user_contacts_v7 (
            key TEXT PRIMARY KEY,
            uid INTEGER,
            fname TEXT,
            sname TEXT,
            imported INTEGER
        );
        CREATE TABLE user_phones_v7 (
            key TEXT,
            phone TEXT,
            sphone TEXT,
            deleted INTEGER,
            PRIMARY KEY (key, phone)
        );

        -- Chats (Groups & Channels)
        CREATE TABLE chats (
            uid INTEGER PRIMARY KEY,
            name TEXT,
            data BLOB
        );
        CREATE TABLE chat_settings_v2 (
            uid INTEGER PRIMARY KEY,
            info BLOB,
            pinned INTEGER,
            online INTEGER,
            inviter INTEGER,
            links INTEGER,
            participants_count INTEGER
        );
        CREATE TABLE user_settings (
            uid INTEGER PRIMARY KEY,
            info BLOB,
            pinned INTEGER
        );

        -- Media v4
        CREATE TABLE media_v4 (
            mid INTEGER,
            uid INTEGER,
            date INTEGER,
            type INTEGER,
            data BLOB,
            PRIMARY KEY(mid, uid, type)
        );
        CREATE INDEX IF NOT EXISTS uid_mid_type_date_idx_media_v4 ON media_v4(uid, mid, type, date);

        -- Auxiliary tables
        CREATE TABLE enc_chats (
            uid INTEGER PRIMARY KEY,
            user INTEGER,
            name TEXT,
            data BLOB,
            g BLOB,
            authkey BLOB,
            ttl INTEGER,
            layer INTEGER,
            seq_in INTEGER,
            seq_out INTEGER,
            use_count INTEGER,
            exchange_id INTEGER,
            key_date INTEGER,
            fprint INTEGER,
            fauthkey BLOB,
            khash BLOB,
            in_seq_no INTEGER,
            admin_id INTEGER,
            mtproto_seq INTEGER
        );
        CREATE TABLE messages_holes (
            uid INTEGER,
            start INTEGER,
            end INTEGER,
            PRIMARY KEY(uid, start)
        );
        CREATE TABLE scheduled_messages_v2 (
            mid INTEGER,
            uid INTEGER,
            send_state INTEGER,
            date INTEGER,
            data BLOB,
            ttl INTEGER,
            replydata BLOB,
            reply_to_message_id INTEGER,
            PRIMARY KEY(mid, uid)
        );
        CREATE TABLE search_recent (
            did INTEGER PRIMARY KEY,
            date INTEGER
        );
        CREATE TABLE params (
            id INTEGER PRIMARY KEY,
            seq INTEGER,
            pts INTEGER,
            date INTEGER,
            qts INTEGER,
            lsv INTEGER,
            sg INTEGER,
            pbytes BLOB
        );
        INSERT INTO params VALUES(1, 100, 500, 1726000000, 50, 0, 0, NULL);

        -- Modelled search remnant (flagged in manifest as modelled, not observed)
        CREATE TABLE messages_search (
            mid INTEGER PRIMARY KEY,
            body TEXT
        );
        """
    )
    conn.commit()

    # -------------------------------------------------------------------------
    # 2. Plant Controls (Vacuumed & Secure Delete) in Delete-Journal Mode
    # -------------------------------------------------------------------------
    marker_vacuum_ctrl = rng.unique_marker("VACUUM_CTRL")
    marker_sec_del_ctrl = rng.unique_marker("SEC_DEL_CTRL")

    # Insert vacuumed control row
    cursor.execute(
        """
        INSERT INTO messages_v2 (
            mid, uid, read_state, send_state, date, data, out, ttl, media
        ) VALUES (99901, 1002, 1, 0, 1726000100, ?, 1, 0, 0)
        """,
        (f"Pre-vacuum control payload: {marker_vacuum_ctrl}".encode("utf-8"),),
    )
    conn.commit()
    cursor.execute("DELETE FROM messages_v2 WHERE mid = 99901")
    conn.commit()
    cursor.execute("VACUUM")

    # Insert secure-delete control row
    cursor.execute("PRAGMA secure_delete = ON")
    cursor.execute(
        """
        INSERT INTO messages_v2 (
            mid, uid, read_state, send_state, date, data, out, ttl, media
        ) VALUES (99902, 1002, 1, 0, 1726000200, ?, 1, 0, 0)
        """,
        (f"Secure delete control payload: {marker_sec_del_ctrl}".encode("utf-8"),),
    )
    conn.commit()
    cursor.execute("DELETE FROM messages_v2 WHERE mid = 99902")
    conn.commit()
    cursor.execute("PRAGMA secure_delete = OFF")

    # -------------------------------------------------------------------------
    # 3. Users, Contacts and Groups Generation (Real TL Objects)
    # -------------------------------------------------------------------------
    # Self account owner (User 1001)
    self_user = types.User(
        id=1001,
        is_self=True,
        contact=True,
        first_name="Arjun",
        last_name="Mehta",
        username="arjun_mehta",
        phone="919876550001",
    )
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, 1, ?)",
        (self_user.id, "Arjun Mehta", bytes(self_user)),
    )

    # 3 Contacts + 1 Empty Chat Contact
    contacts_meta: List[Dict[str, Any]] = [
        {
            "uid": 1002,
            "first_name": "Priya",
            "last_name": "Sharma",
            "username": "priya_s",
            "phone": "919876550002",
        },
        {
            "uid": 1003,
            "first_name": "Rohan",
            "last_name": "Verma",
            "username": "rohan_v",
            "phone": "919876550003",
        },
        {
            "uid": 1004,
            "first_name": "Ananya",
            "last_name": "Deshmukh",
            "username": "ananya_d",
            "phone": "919876550004",
        },
        # Empty chat contact (control: 0 messages)
        {
            "uid": 1005,
            "first_name": "Vikram",
            "last_name": "Singhania",
            "username": "vikram_s",
            "phone": "919876550005",
        },
    ]

    users_manifest: List[TGUserEntry] = [
        TGUserEntry(
            uid=self_user.id,
            first_name="Arjun",
            last_name="Mehta",
            username="arjun_mehta",
            phone="919876550001",
            is_self=True,
        )
    ]

    for c in contacts_meta:
        tl_u = types.User(
            id=c["uid"],
            is_self=False,
            contact=True,
            first_name=c["first_name"],
            last_name=c["last_name"],
            username=c["username"],
            phone=c["phone"],
        )
        full_name = f"{c['first_name']} {c['last_name']}"
        cursor.execute("INSERT INTO users VALUES (?, ?, 1, ?)", (c["uid"], full_name, bytes(tl_u)))
        cursor.execute("INSERT INTO contacts VALUES (?, 1)", (c["uid"],))
        cursor.execute(
            "INSERT INTO user_contacts_v7 VALUES (?, ?, ?, ?, 1)",
            (str(c["uid"]), c["uid"], c["first_name"], c["last_name"]),
        )
        cursor.execute(
            "INSERT INTO user_phones_v7 VALUES (?, ?, ?, 0)",
            (str(c["uid"]), c["phone"], c["phone"]),
        )
        users_manifest.append(
            TGUserEntry(
                uid=c["uid"],
                first_name=c["first_name"],
                last_name=c["last_name"],
                username=c["username"],
                phone=c["phone"],
                is_self=False,
            )
        )

    # 1 Group Chat (Chat 2001)
    group_chat = types.Chat(
        id=2001,
        title="ArtifactX TG Taskforce",
        photo=types.ChatPhotoEmpty(),
        participants_count=4,
        date=datetime.datetime(2026, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        version=1,
    )
    group_did = -2001  # Telegram convention for group dialog IDs
    cursor.execute(
        "INSERT INTO chats VALUES (?, ?, ?)",
        (2001, "ArtifactX TG Taskforce", bytes(group_chat)),
    )
    cursor.execute(
        "INSERT INTO chat_settings_v2 VALUES (?, NULL, 0, 4, 1001, 0, 4)",
        (2001,),
    )

    chats_manifest: List[TGChatEntry] = [
        TGChatEntry(
            did=group_did,
            title="ArtifactX TG Taskforce",
            is_channel=False,
            is_group=True,
            participants_count=4,
            participant_uids=[1001, 1002, 1003, 1004],
        )
    ]

    # Create dialog rows for contacts and group
    dialog_uids = [1002, 1003, 1004, 1005, group_did]
    for d_uid in dialog_uids:
        cursor.execute(
            """
            INSERT INTO dialogs (
                did, date, unread_count, last_mid, inbox_max, outbox_max,
                last_mid_i, unread_count_i, pts, date_i, pinned, flags,
                folder_id, data, unread_reactions, last_mid_group, ttl_period
            ) VALUES (?, 1726000000, 0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, NULL, 0, 0, 0)
            """,
            (d_uid,),
        )
    conn.commit()

    # -------------------------------------------------------------------------
    # 4. Message Generation (300-450 Messages, Real TL Blobs)
    # -------------------------------------------------------------------------
    messages_manifest: List[TGMessageEntry] = []
    blob_variants_manifest: List[TGBlobVariantEntry] = []
    created_messages: List[Dict[str, Any]] = []

    # Start timestamp: 2026-09-01 08:00:00 UTC (1725177600)
    base_ts = 1725177600
    current_ts = base_ts
    active_dialogs = [1002, 1003, 1004, group_did]  # 1005 left empty

    total_target_messages = 350
    # Reserve specific indices for documented blob variants (B3.2):
    # - mid 50: trailing_bytes
    # - mid 80: unknown_constructor
    # - mid 120: older_layer
    special_variant_mids = {50: "trailing_bytes", 80: "unknown_constructor", 120: "older_layer"}

    for mid in range(1, total_target_messages + 1):
        # Realistic time step: 10 mins to 4 hours, daily rhythm
        time_step = rng.randint(300, 7200)
        current_ts += time_step
        current_dt = datetime.datetime.fromtimestamp(current_ts, tz=datetime.timezone.utc)
        current_utc_ms = current_ts * 1000

        target_dialog = rng.choice(active_dialogs)
        is_group = (target_dialog == group_did)

        # Sender & out flag
        if is_group:
            sender_id = rng.choice([1001, 1002, 1003, 1004])
            out = 1 if sender_id == 1001 else 0
            peer_obj = types.PeerChat(chat_id=2001)
            from_peer = types.PeerUser(user_id=sender_id)
        else:
            out = rng.choice([0, 1])
            sender_id = 1001 if out else target_dialog
            peer_obj = types.PeerUser(user_id=target_dialog)
            from_peer = None

        # Message Type distribution: 75% text, 10% photo, 5% audio/doc, 5% geo, 5% reply
        type_roll = rng.randint(1, 100)
        media_code = 0
        media_type_str: Optional[str] = None
        media_ref: Optional[str] = None
        reply_to_mid: Optional[int] = None
        tl_media = None
        reply_header = None
        flags: List[str] = []

        # Plain text with mixed Latin, Hindi/Marathi, and Emoji
        text_samples = [
            f"Telegram status update for node {mid}.",
            f"नमस्ते, यह टेलीग्राम संदेश संख्या {mid} है।",
            f"Meeting rendezvous confirmed at checkpoint #{mid} 📍👍",
            f"Reviewing forensic cache4.db artifact payload: {mid}.",
            f"Data packet transmission complete for batch {mid} 🚀",
            f"कृपया तात्काळ संपर्क साधा (Priority notice {mid}).",
        ]
        msg_text = rng.choice(text_samples)

        if type_roll <= 70:
            pass  # Standard text
        elif type_roll <= 80:
            # Photo Media
            media_code = 1
            media_type_str = "image"
            media_ref = f"tg_photo_{mid:04d}.jpg"
            photo_obj = types.Photo(
                id=90000 + mid,
                access_hash=rng.randint(10000, 99999),
                file_reference=f"photo_ref_{mid}".encode("utf-8"),
                date=current_dt,
                sizes=[types.PhotoSize(type="m", w=320, h=240, size=18500)],
                dc_id=2,
            )
            tl_media = types.MessageMediaPhoto(photo=photo_obj)
            flags.append("photo")
        elif type_roll <= 87:
            # Audio/Voice Document
            media_code = 2
            media_type_str = "audio"
            media_ref = f"tg_audio_{mid:04d}.ogg"
            doc_obj = types.Document(
                id=80000 + mid,
                access_hash=rng.randint(10000, 99999),
                file_reference=f"doc_ref_{mid}".encode("utf-8"),
                date=current_dt,
                mime_type="audio/ogg",
                size=14200,
                dc_id=2,
                attributes=[types.DocumentAttributeAudio(voice=True, duration=28)],
            )
            tl_media = types.MessageMediaDocument(document=doc_obj)
            flags.append("audio")
        elif type_roll <= 93:
            # Location / GeoPoint
            media_code = 5
            media_type_str = "location"
            loc = rng.choice(TEST_LOCATIONS)
            geo_obj = types.GeoPoint(lat=loc.latitude, long=loc.longitude, access_hash=0)
            tl_media = types.MessageMediaGeo(geo=geo_obj)
            media_ref = f"{loc.latitude},{loc.longitude}"
            flags.append("location")
        else:
            # Quoted / Reply message
            if mid > 2:
                reply_to_mid = mid - 1
                reply_header = types.MessageReplyHeader(reply_to_msg_id=reply_to_mid)
                flags.append("reply")

        # Instantiate authentic Telethon Message object
        tl_message = types.Message(
            id=mid,
            peer_id=peer_obj,
            from_id=from_peer,
            date=current_dt,
            message=msg_text,
            out=bool(out),
            media=tl_media,
            reply_to=reply_header,
        )

        # Documented Blob Variants handling (B3.2)
        variant_name = special_variant_mids.get(mid, "exact")
        if variant_name == "exact":
            raw_blob = bytes(tl_message)
            expected_outcome = "parse_success"
            constructor_hex = hex(tl_message.CONSTRUCTOR_ID)
            variant_notes = f"Standard Telethon serialized TL bytes (Layer {TELETHON_LAYER})."
        elif variant_name == "trailing_bytes":
            # Valid TL object + 8 bytes of trailing flags / local bookkeeping
            raw_blob = bytes(tl_message) + b"\x00\x00\x00\x01\xaa\xbb\xcc\xdd"
            expected_outcome = "parse_success"
            constructor_hex = hex(tl_message.CONSTRUCTOR_ID)
            variant_notes = "Valid TL Message followed by 8 trailing local flag bytes; Telethon parses cleanly."
        elif variant_name == "unknown_constructor":
            # 4-byte little endian 0xDEADBEEF + dummy payload
            raw_blob = struct.pack("<I", CONSTRUCTOR_UNKNOWN) + (b"\x11" * 32)
            expected_outcome = "unparsed_blob"
            constructor_hex = hex(CONSTRUCTOR_UNKNOWN)
            variant_notes = "Unknown TL constructor ID 0xDEADBEEF; tests UNPARSED_BLOB handling."
        elif variant_name == "older_layer":
            # 4-byte little endian Layer 133 Message constructor + dummy payload
            raw_blob = struct.pack("<I", CONSTRUCTOR_LAYER133_MESSAGE) + (b"\x22" * 32)
            expected_outcome = "layer_mismatch"
            constructor_hex = hex(CONSTRUCTOR_LAYER133_MESSAGE)
            variant_notes = "Legacy Layer 133 Message constructor 0x38114EE2; tests layer mismatch handling."
        else:
            raw_blob = bytes(tl_message)
            expected_outcome = "parse_success"
            constructor_hex = hex(tl_message.CONSTRUCTOR_ID)
            variant_notes = "Exact bytes"

        # Insert into messages_v2
        cursor.execute(
            """
            INSERT INTO messages_v2 (
                mid, uid, read_state, send_state, date, data, out, ttl,
                media, replydata, imp, mention, forwards, replies_data,
                thread_reply_id, is_channel, reply_to_message_id,
                custom_params, group_id, reply_to_story_id
            ) VALUES (?, ?, 1, 0, ?, ?, ?, 0, ?, NULL, 0, 0, 0, NULL, 0, 0, ?, NULL, 0, 0)
            """,
            (mid, target_dialog, current_ts, raw_blob, out, media_code, reply_to_mid or 0),
        )

        # Insert standalone media in media_v4 if media is present
        if tl_media is not None:
            cursor.execute(
                """
                INSERT INTO media_v4 (mid, uid, date, type, data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (mid, target_dialog, current_ts, media_code, bytes(tl_media)),
            )

        # Also insert into modelled search index table
        cursor.execute(
            "INSERT INTO messages_search (mid, body) VALUES (?, ?)",
            (mid, msg_text),
        )

        # Record in manifest
        msg_entry = TGMessageEntry(
            mid=mid,
            uid=target_dialog,
            from_id=sender_id,
            date_raw=current_ts,
            date_utc_ms=current_utc_ms,
            text=msg_text if variant_name in ("exact", "trailing_bytes") else None,
            media_type=media_type_str,
            media_ref=media_ref,
            reply_to_mid=reply_to_mid,
            out=out,
            blob_variant=variant_name,
            flags=flags,
        )
        messages_manifest.append(msg_entry)

        if variant_name != "exact":
            blob_variants_manifest.append(
                TGBlobVariantEntry(
                    mid=mid,
                    uid=target_dialog,
                    variant=variant_name,
                    constructor_hex=constructor_hex,
                    expected_outcome=expected_outcome,
                    notes=variant_notes,
                )
            )

        created_messages.append(
            {
                "mid": mid,
                "uid": target_dialog,
                "date": current_ts,
                "text": msg_text,
                "raw_blob": raw_blob,
                "variant": variant_name,
            }
        )

    # Update dialogs table with last_mid and date
    for d_uid in dialog_uids:
        cursor.execute(
            """
            SELECT mid, date FROM messages_v2
            WHERE uid = ?
            ORDER BY mid DESC LIMIT 1
            """,
            (d_uid,),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE dialogs SET last_mid = ?, date = ? WHERE did = ?",
                (row[0], row[1], d_uid),
            )
    conn.commit()

    # -------------------------------------------------------------------------
    # 5. Deletion & Modification Scenarios (B3.3)
    # -------------------------------------------------------------------------
    deletions_manifest: List[TGDeletionEntry] = []
    edits_manifest: List[TGEditEntry] = []

    # Scenario 1: Freelist Deleted (Tier 3: Multi-page deletion moving pages to freelist)
    # Insert 40 large messages (600 bytes each) filling ~6 leaf pages, then delete them all
    marker_freelist = rng.unique_marker("TG_FREELIST_DELETED")
    fl_mids: List[int] = []
    for f_idx in range(40):
        f_mid = 1000 + f_idx
        f_payload = f"Sensitive operational log {f_idx}: {marker_freelist} " + ("#" * 500)
        # Create valid TL message for this row
        tl_fl = types.Message(
            id=f_mid,
            peer_id=types.PeerUser(user_id=1002),
            date=datetime.datetime.fromtimestamp(current_ts + 100 + f_idx, tz=datetime.timezone.utc),
            message=f_payload,
            out=True,
        )
        cursor.execute(
            """
            INSERT INTO messages_v2 (
                mid, uid, read_state, send_state, date, data, out, ttl, media
            ) VALUES (?, 1002, 1, 0, ?, ?, 1, 0, 0)
            """,
            (f_mid, current_ts + 100 + f_idx, bytes(tl_fl)),
        )
        fl_mids.append(f_mid)
    conn.commit()

    # Delete all 40 rows: moves leaf pages to SQLite freelist
    cursor.execute(
        f"DELETE FROM messages_v2 WHERE mid BETWEEN {fl_mids[0]} AND {fl_mids[-1]}"
    )
    conn.commit()

    deletions_manifest.append(
        TGDeletionEntry(
            case_id="del_01_freelist",
            method="freelist_deleted",
            expected_recoverable=True,
            expected_tier="tier_3",
            marker=marker_freelist,
            original_mid=fl_mids[0],
            original_text=f"Sensitive operational log: {marker_freelist}",
            notes="Tier 3 recoverable from SQLite freelist trunk/leaf pages.",
        )
    )

    # Scenario 2: Benign Gap Control (Tier 4 / weak hint)
    # Jump message sequence ahead by 10 to simulate sequence jump without deletion
    cursor.execute("SELECT MAX(mid) FROM messages_v2")
    max_mid = cursor.fetchone()[0] or total_target_messages
    gap_post_mid = max_mid + 11
    tl_gap = types.Message(
        id=gap_post_mid,
        peer_id=types.PeerUser(user_id=1002),
        date=datetime.datetime.fromtimestamp(current_ts + 300, tz=datetime.timezone.utc),
        message="Message after sequence jump",
        out=True,
    )
    cursor.execute(
        """
        INSERT INTO messages_v2 (
            mid, uid, read_state, send_state, date, data, out, ttl, media
        ) VALUES (?, 1002, 1, 0, ?, ?, 1, 0, 0)
        """,
        (gap_post_mid, current_ts + 300, bytes(tl_gap)),
    )
    conn.commit()

    deletions_manifest.append(
        TGDeletionEntry(
            case_id="del_02_benign_gap",
            method="benign_gap",
            expected_recoverable=False,
            expected_tier="tier_4",
            marker="KEY_GAP_POST",
            original_mid=max_mid + 1,
            original_text=None,
            notes="Benign autoincrement ID gap; must NOT be reported as deletion above weak_hint (confidence <= 0.30).",
        )
    )

    # Scenario 3: Slack Deleted (Tier 3: Freeblock inside page)
    # Insert an isolated message into contact 1003, commit, then delete only that row.
    # Done as the last operation before WAL mode so no subsequent inserts reclaim this free space.
    marker_slack = rng.unique_marker("TG_SLACK_DELETED")
    slack_mid = max_mid + 20
    tl_slack = types.Message(
        id=slack_mid,
        peer_id=types.PeerUser(user_id=1003),
        date=datetime.datetime.fromtimestamp(current_ts + 200, tz=datetime.timezone.utc),
        message=f"Confidential meeting agenda: {marker_slack}",
        out=True,
    )
    cursor.execute(
        """
        INSERT INTO messages_v2 (
            mid, uid, read_state, send_state, date, data, out, ttl, media
        ) VALUES (?, 1003, 1, 0, ?, ?, 1, 0, 0)
        """,
        (slack_mid, current_ts + 200, bytes(tl_slack)),
    )
    conn.commit()
    cursor.execute("DELETE FROM messages_v2 WHERE mid = ?", (slack_mid,))
    conn.commit()

    deletions_manifest.append(
        TGDeletionEntry(
            case_id="del_03_slack",
            method="slack_deleted",
            expected_recoverable=True,
            expected_tier="tier_3",
            marker=marker_slack,
            original_mid=slack_mid,
            original_text=f"Confidential meeting agenda: {marker_slack}",
            notes="Tier 3 recoverable from intrapage freeblock / unallocated space.",
        )
    )


    # Manifest control entries
    deletions_manifest.append(
        TGDeletionEntry(
            case_id="ctrl_04_vacuumed",
            method="vacuumed_control",
            expected_recoverable=False,
            expected_tier="unrecoverable",
            marker=marker_vacuum_ctrl,
            original_mid=99901,
            original_text=f"Pre-vacuum control payload: {marker_vacuum_ctrl}",
            notes="Vacuumed control: deleted then VACUUMed; must be reported as not recovered.",
        )
    )
    deletions_manifest.append(
        TGDeletionEntry(
            case_id="ctrl_05_secure_delete",
            method="secure_delete_control",
            expected_recoverable=False,
            expected_tier="unrecoverable",
            marker=marker_sec_del_ctrl,
            original_mid=99902,
            original_text=f"Secure delete control payload: {marker_sec_del_ctrl}",
            notes="Secure delete control: deleted with secure_delete=ON; zero-filled, not recoverable.",
        )
    )

    # -------------------------------------------------------------------------
    # 6. WAL-Resident Scenario (Tier 2) & Uncheckpointed Snapshot
    # -------------------------------------------------------------------------
    cursor.execute("PRAGMA journal_mode = WAL")
    marker_wal = rng.unique_marker("TG_WAL_RESIDENT")
    wal_mid = 3001

    # Insert message in WAL mode
    tl_wal = types.Message(
        id=wal_mid,
        peer_id=types.PeerUser(user_id=1004),
        date=datetime.datetime.fromtimestamp(current_ts + 400, tz=datetime.timezone.utc),
        message=f"Uncheckpointed WAL telegram draft: {marker_wal}",
        out=True,
    )
    cursor.execute(
        """
        INSERT INTO messages_v2 (
            mid, uid, read_state, send_state, date, data, out, ttl, media
        ) VALUES (?, 1004, 1, 0, ?, ?, 1, 0, 0)
        """,
        (wal_mid, current_ts + 400, bytes(tl_wal)),
    )
    conn.commit()

    # Overwrite the message in WAL mode: leaves original version in an earlier WAL frame
    tl_wal_updated = types.Message(
        id=wal_mid,
        peer_id=types.PeerUser(user_id=1004),
        date=datetime.datetime.fromtimestamp(current_ts + 420, tz=datetime.timezone.utc),
        message="Updated text replacing WAL telegram draft",
        out=True,
    )
    cursor.execute(
        "UPDATE messages_v2 SET data = ? WHERE mid = ?",
        (bytes(tl_wal_updated), wal_mid),
    )
    conn.commit()

    # Snapshot temp_db_path and temp_db_path-wal to final output_dir BEFORE closing connection
    temp_wal_path = temp_dir / "cache4.db-wal"
    shutil.copy2(temp_db_path, db_path)
    shutil.copy2(temp_wal_path, wal_path)
    wal_salt1 = rng.randint(0x10000000, 0xFFFFFFFF)
    wal_salt2 = rng.randint(0x10000000, 0xFFFFFFFF)
    _normalize_wal_salts(wal_path, wal_salt1, wal_salt2)

    # Close temp connection and remove temp directory
    conn.close()
    shutil.rmtree(temp_dir, ignore_errors=True)

    deletions_manifest.append(
        TGDeletionEntry(
            case_id="del_06_wal_resident",
            method="wal_resident",
            expected_recoverable=True,
            expected_tier="tier_2",
            marker=marker_wal,
            original_mid=wal_mid,
            original_text=f"Uncheckpointed WAL telegram draft: {marker_wal}",
            notes="Tier 2 recoverable from uncheckpointed Write-Ahead Log frame prior to checkpoint.",
        )
    )

    # -------------------------------------------------------------------------
    # 7. Self-Verification by Raw-Byte Search & Telethon Re-reading (B3.4)
    # -------------------------------------------------------------------------
    raw_db = db_path.read_bytes()
    raw_wal = wal_path.read_bytes()

    # Raw-byte search for claimed recoverable markers
    fl_offsets = _find_byte_offsets(raw_db, marker_freelist.encode("utf-8"))
    if not fl_offsets:
        raise RuntimeError(f"Self-verification failed: Freelist marker {marker_freelist} not found in cache4.db!")

    slack_offsets = _find_byte_offsets(raw_db, marker_slack.encode("utf-8"))
    if not slack_offsets:
        raise RuntimeError(f"Self-verification failed: Slack marker {marker_slack} not found in cache4.db!")

    wal_offsets = _find_byte_offsets(raw_wal, marker_wal.encode("utf-8"))
    if not wal_offsets:
        raise RuntimeError(f"Self-verification failed: WAL marker {marker_wal} not found in cache4.db-wal!")

    # Raw-byte search for strictly absent controls
    if _find_byte_offsets(raw_db, marker_vacuum_ctrl.encode("utf-8")) or _find_byte_offsets(raw_wal, marker_vacuum_ctrl.encode("utf-8")):
        raise RuntimeError(f"Self-verification failed: Vacuumed control marker {marker_vacuum_ctrl} found in raw bytes!")

    if _find_byte_offsets(raw_db, marker_sec_del_ctrl.encode("utf-8")) or _find_byte_offsets(raw_wal, marker_sec_del_ctrl.encode("utf-8")):
        raise RuntimeError(f"Self-verification failed: Secure delete marker {marker_sec_del_ctrl} found in raw bytes!")

    # Store discovered offsets
    for d_entry in deletions_manifest:
        if d_entry.case_id == "del_01_freelist":
            d_entry.byte_offsets = fl_offsets
        elif d_entry.case_id == "del_03_slack":
            d_entry.byte_offsets = slack_offsets
        elif d_entry.case_id == "del_06_wal_resident":
            d_entry.byte_offsets = wal_offsets


    # Telethon Blob Re-reading Verification (B3.4)
    # Must re-read 100% of well-formed blobs, and verify expected failures on unknown/older constructors
    re_read_success_count = 0
    re_read_target_count = 0

    for msg in created_messages:
        raw_blob = msg["raw_blob"]
        variant = msg["variant"]
        reader = BinaryReader(raw_blob)

        if variant in ("exact", "trailing_bytes"):
            re_read_target_count += 1
            try:
                parsed_obj = reader.tgread_object()
                assert parsed_obj.id == msg["mid"], f"Parsed ID mismatch: {parsed_obj.id} != {msg['mid']}"
                assert parsed_obj.message == msg["text"], f"Parsed text mismatch: {parsed_obj.message} != {msg['text']}"
                re_read_success_count += 1
            except Exception as e:
                raise RuntimeError(f"Telethon failed to re-read well-formed blob mid={msg['mid']}: {e}")
        elif variant == "unknown_constructor":
            try:
                reader.tgread_object()
                raise RuntimeError(f"Unknown constructor blob mid={msg['mid']} unexpectedly parsed without error!")
            except Exception:
                pass  # Expected failure
        elif variant == "older_layer":
            try:
                reader.tgread_object()
                raise RuntimeError(f"Older layer blob mid={msg['mid']} unexpectedly parsed without error!")
            except Exception:
                pass  # Expected failure

    assert re_read_success_count == re_read_target_count, (
        f"Telethon re-read rate not 100%: {re_read_success_count}/{re_read_target_count}"
    )

    # -------------------------------------------------------------------------
    # 8. Manifest Assembly & Saving
    # -------------------------------------------------------------------------
    files_info: List[DatasetFileInfo] = []
    import hashlib
    for f_path in (db_path, wal_path):
        f_bytes = f_path.read_bytes()
        files_info.append(
            DatasetFileInfo(
                path=f_path.name,
                sha256=hashlib.sha256(f_bytes).hexdigest(),
                size=len(f_bytes),
            )
        )

    telegram_manifest_data = {
        "users": [asdict_tg(u) for u in users_manifest],
        "chats": [asdict_tg(c) for c in chats_manifest],
        "messages": [asdict_tg(m) for m in messages_manifest],
        "deletions": [asdict_tg(d) for d in deletions_manifest],
        "edits": [asdict_tg(e) for e in edits_manifest],
        "blob_variants": [asdict_tg(b) for b in blob_variants_manifest],
        "telethon_layer": TELETHON_LAYER,
        "sqlite_user_version": 155,
    }

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "python": "3.14.6",
            "sqlite3": sqlite3.sqlite_version,
            "telethon": telethon_version,
            "telethon_layer": str(TELETHON_LAYER),
        },
        files=files_info,
        whatsapp={},
        telegram=telegram_manifest_data,
        shared_entities=[],
        decoys=[],
        controls=[],
        encryption=None,
        modelled_vs_observed={
            "schema": "observed from Telegram for Android MessagesStorage.java (v5.x-10.x)",
            "messages_search": "modelled (Telegram Android cache4.db does not maintain SQLite FTS tables; search is performed in-memory and via tag_message_id/tag tables; messages_search is synthetic for full-text carving evaluation)",
            "tl_layer": f"observed Telethon Layer {TELETHON_LAYER}",
            "encryption": "none (plain cache4.db)",
        },
    )

    manifest.save(output_dir / "manifest.json")
    return manifest


def asdict_tg(obj: Any) -> Dict[str, Any]:
    """Helper to convert dataclass instances to dict."""
    from dataclasses import asdict
    return asdict(obj)
