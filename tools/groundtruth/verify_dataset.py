"""Dataset verification utility.

Follows master.md R1, R20, and 02_GROUND_TRUTH_DATASETS.md §5:
- Validates manifest schema and internal consistency.
- Recomputes SHA-256 and byte sizes of all files against manifest.
- For plaintext DBs, connects read-only, checks table structures, and compares counts/rows.
- Re-verifies deletion markers and control absences in raw bytes.
- Returns 0 if all verified, non-zero with error list if any mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _compute_sha256(path: Path) -> Tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def verify_dataset(dataset_dir: Path) -> Tuple[bool, List[str]]:
    """Verify a dataset directory against its manifest.
    
    Returns (is_valid, list_of_error_strings).
    """
    errors: List[str] = []
    dataset_dir = Path(dataset_dir)

    if not dataset_dir.is_dir():
        return False, [f"Dataset directory does not exist: {dataset_dir}"]

    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.is_file():
        return False, [f"manifest.json missing in dataset directory: {manifest_path}"]

    try:
        manifest_data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"manifest.json is not valid JSON: {e}"]

    # 1. Basic schema checks
    required_keys = ["dataset_id", "variant", "seed", "generator_version", "origin", "files", "modelled_vs_observed"]
    for k in required_keys:
        if k not in manifest_data:
            errors.append(f"Missing required manifest key: {k}")

    if errors:
        return False, errors

    # 2. File hash & existence checks
    files_list = manifest_data.get("files", [])
    if not files_list:
        errors.append("Manifest files array is empty.")

    for f_info in files_list:
        rel_path = f_info.get("path")
        expected_sha = f_info.get("sha256")
        expected_size = f_info.get("size")

        target_file = dataset_dir / rel_path
        if not target_file.is_file():
            errors.append(f"Expected file missing: {rel_path}")
            continue

        actual_sha, actual_size = _compute_sha256(target_file)
        if actual_size != expected_size:
            errors.append(f"File size mismatch for {rel_path}: expected {expected_size}, got {actual_size}")
        if actual_sha.lower() != expected_sha.lower():
            errors.append(f"SHA-256 mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")

    # 3. WhatsApp Plain DB Content Verification
    wa_data = manifest_data.get("whatsapp")
    if wa_data:
        db_path = dataset_dir / "msgstore.db"
        if db_path.is_file():
            try:
                conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
                cursor = conn.cursor()

                # Verify expected tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0].lower() for row in cursor.fetchall()}
                expected_tables = {"jid", "chat", "message", "message_media", "message_location", "message_quoted", "message_revoked", "message_edit_info"}
                missing_tables = expected_tables - tables
                if missing_tables:
                    errors.append(f"msgstore.db missing tables: {missing_tables}")

                # Verify total messages
                manifest_messages = wa_data.get("messages", [])
                cursor.execute("SELECT COUNT(*) FROM message")
                actual_msg_count = cursor.fetchone()[0]

                # Note: DB count includes messages plus any non-deleted rows
                if actual_msg_count < len(manifest_messages):
                    errors.append(f"msgstore.db message count ({actual_msg_count}) less than manifest messages ({len(manifest_messages)})")

                # Verify revoked messages
                cursor.execute("SELECT message_row_id, revoked_key_id FROM message_revoked")
                revoked_rows = cursor.fetchall()
                manifest_deletions = wa_data.get("deletions", [])
                expected_revoked = [d for d in manifest_deletions if d.get("method") == "revoked"]
                if len(revoked_rows) < len(expected_revoked):
                    errors.append(f"msgstore.db message_revoked count ({len(revoked_rows)}) less than expected ({len(expected_revoked)})")

                # Verify empty chat has 0 messages
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM message m
                    JOIN chat c ON m.chat_row_id = c._id
                    JOIN jid j ON c.jid_row_id = j._id
                    WHERE j.user = '919876540005'
                    """
                )
                empty_chat_msgs = cursor.fetchone()[0]
                if empty_chat_msgs != 0:
                    errors.append(f"Empty chat control failed: expected 0 messages for 919876540005, got {empty_chat_msgs}")

                conn.close()
            except sqlite3.Error as sqle:
                errors.append(f"SQLite verification failed on msgstore.db: {sqle}")

        # Check wa.db if present
        wa_db_path = dataset_dir / "wa.db"
        if wa_db_path.is_file():
            try:
                conn_wa = sqlite3.connect(f"file:{wa_db_path.resolve()}?mode=ro", uri=True)
                cursor_wa = conn_wa.cursor()
                cursor_wa.execute("SELECT COUNT(*) FROM wa_contacts")
                contact_count = cursor_wa.fetchone()[0]
                if contact_count < 4:
                    errors.append(f"wa.db wa_contacts count ({contact_count}) unexpectedly low (< 4)")
                conn_wa.close()
            except sqlite3.Error as sqle:
                errors.append(f"SQLite verification failed on wa.db: {sqle}")

        # 4. Raw-byte self-verification checks (B1.5)
        raw_db = db_path.read_bytes() if db_path.is_file() else b""
        wal_path = dataset_dir / "msgstore.db-wal"
        raw_wal = wal_path.read_bytes() if wal_path.is_file() else b""

        for deletion in manifest_deletions:
            method = deletion.get("method")
            marker = deletion.get("marker", "").encode("utf-8")
            expected_rec = deletion.get("expected_recoverable", False)

            if method in ("freelist_deleted", "slack_deleted") and expected_rec:
                if marker not in raw_db:
                    errors.append(f"Recoverability verification failed: {method} marker {deletion.get('marker')} not in msgstore.db raw bytes")
            elif method == "wal_resident" and expected_rec:
                if marker not in raw_wal:
                    errors.append(f"Recoverability verification failed: wal_resident marker {deletion.get('marker')} not in msgstore.db-wal raw bytes")
            elif method in ("vacuumed_control", "secure_delete_control"):
                if marker in raw_db or marker in raw_wal:
                    errors.append(f"Control failure: {method} marker {deletion.get('marker')} FOUND in raw bytes (must be absent)")

    # 4. Telegram Plain DB Content Verification (B3)
    tg_data = manifest_data.get("telegram")
    if tg_data:
        tg_db_path = dataset_dir / "cache4.db"
        tg_wal_path = dataset_dir / "cache4.db-wal"

        if tg_db_path.is_file():
            try:
                conn_tg = sqlite3.connect(f"file:{tg_db_path.resolve()}?mode=ro", uri=True)
                cursor_tg = conn_tg.cursor()

                # Verify expected tables exist
                cursor_tg.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0].lower() for row in cursor_tg.fetchall()}
                expected_tg_tables = {
                    "messages_v2", "dialogs", "users", "chats", "contacts",
                    "media_v4", "chat_settings_v2", "user_settings", "enc_chats",
                    "messages_holes", "scheduled_messages_v2", "params"
                }
                missing_tg_tables = expected_tg_tables - tables
                if missing_tg_tables:
                    errors.append(f"cache4.db missing expected tables: {missing_tg_tables}")

                # Verify PRAGMA user_version == 155
                cursor_tg.execute("PRAGMA user_version")
                db_ver = cursor_tg.fetchone()[0]
                if db_ver != 155:
                    errors.append(f"cache4.db user_version mismatch: expected 155, got {db_ver}")

                # Verify total messages
                manifest_tg_msgs = tg_data.get("messages", [])
                cursor_tg.execute("SELECT COUNT(*) FROM messages_v2")
                actual_tg_count = cursor_tg.fetchone()[0]
                if actual_tg_count < len(manifest_tg_msgs):
                    errors.append(f"cache4.db message count ({actual_tg_count}) less than manifest messages ({len(manifest_tg_msgs)})")

                # Verify empty chat control (uid 1005 has 0 messages)
                cursor_tg.execute("SELECT COUNT(*) FROM messages_v2 WHERE uid = 1005")
                empty_tg_msgs = cursor_tg.fetchone()[0]
                if empty_tg_msgs != 0:
                    errors.append(f"Empty dialog control failed: expected 0 messages for uid 1005, got {empty_tg_msgs}")

                # Verify Telethon re-reading 100% of well-formed blobs (B3.4)
                cursor_tg.execute("SELECT mid, data FROM messages_v2")
                db_blobs = {row[0]: row[1] for row in cursor_tg.fetchall()}

                from telethon.extensions import BinaryReader

                telethon_read_ok = 0
                telethon_read_targets = 0

                for m in manifest_tg_msgs:
                    m_id = m.get("mid")
                    m_variant = m.get("blob_variant", "exact")
                    m_text = m.get("text")
                    blob = db_blobs.get(m_id)

                    if blob is None:
                        continue

                    reader = BinaryReader(blob)
                    if m_variant in ("exact", "trailing_bytes"):
                        telethon_read_targets += 1
                        try:
                            parsed_tl = reader.tgread_object()
                            if parsed_tl.id != m_id:
                                errors.append(f"Telethon re-read ID mismatch for mid {m_id}: got {parsed_tl.id}")
                            elif m_text is not None and parsed_tl.message != m_text:
                                errors.append(f"Telethon re-read text mismatch for mid {m_id}: got '{parsed_tl.message}', expected '{m_text}'")
                            else:
                                telethon_read_ok += 1
                        except Exception as e:
                            errors.append(f"Telethon failed to re-read well-formed blob mid {m_id} ({m_variant}): {e}")
                    elif m_variant == "unknown_constructor":
                        try:
                            reader.tgread_object()
                            errors.append(f"Unknown constructor mid {m_id} unexpectedly parsed without error")
                        except Exception:
                            pass  # Expected failure
                    elif m_variant == "older_layer":
                        try:
                            reader.tgread_object()
                            errors.append(f"Older layer constructor mid {m_id} unexpectedly parsed without error")
                        except Exception:
                            pass  # Expected failure

                if telethon_read_targets > 0 and telethon_read_ok != telethon_read_targets:
                    errors.append(f"Telethon re-read accuracy failed: {telethon_read_ok}/{telethon_read_targets} (expected 100%)")

                conn_tg.close()
            except sqlite3.Error as sqle:
                errors.append(f"SQLite verification failed on cache4.db: {sqle}")

        # Raw-byte self-verification checks for Telegram
        raw_tg_db = tg_db_path.read_bytes() if tg_db_path.is_file() else b""
        raw_tg_wal = tg_wal_path.read_bytes() if tg_wal_path.is_file() else b""
        tg_deletions = tg_data.get("deletions", [])

        for deletion in tg_deletions:
            method = deletion.get("method")
            marker = deletion.get("marker", "").encode("utf-8")
            expected_rec = deletion.get("expected_recoverable", False)

            if method in ("freelist_deleted", "slack_deleted") and expected_rec:
                if marker not in raw_tg_db:
                    errors.append(f"Telegram recoverability check failed: {method} marker {deletion.get('marker')} not in cache4.db raw bytes")
            elif method == "wal_resident" and expected_rec:
                if marker not in raw_tg_wal:
                    errors.append(f"Telegram recoverability check failed: wal_resident marker {deletion.get('marker')} not in cache4.db-wal raw bytes")
            elif method in ("vacuumed_control", "secure_delete_control"):
                if marker in raw_tg_db or marker in raw_tg_wal:
                    errors.append(f"Telegram control failure: {method} marker {deletion.get('marker')} FOUND in raw bytes (must be absent)")

    # 5. Encryption & Cryptographic Fixtures Verification (B2)
    enc_data = manifest_data.get("encryption")
    if enc_data:
        enc_format = enc_data.get("format")
        keys_dir = dataset_dir / "keys"
        if keys_dir.is_dir():
            readme = keys_dir / "README.md"
            if not readme.is_file():
                errors.append("keys/README.md is missing in encrypted dataset")
            elif "Test Keys" not in readme.read_text(encoding="utf-8"):
                errors.append("keys/README.md does not contain required fictitious disclaimer (R5, R14)")

        if enc_format == "crypt14":
            key_path = dataset_dir / enc_data.get("key_ref", "keys/key")
            enc_file = dataset_dir / "msgstore.db.crypt14"
            if not key_path.is_file():
                errors.append(f"crypt14 key file missing: {key_path}")
            if not enc_file.is_file():
                errors.append(f"crypt14 encrypted file missing: {enc_file}")

            # Reference round-trip check
            if key_path.is_file() and enc_file.is_file():
                try:
                    import subprocess
                    import tempfile
                    with tempfile.TemporaryDirectory() as td:
                        dec_test = Path(td) / "decrypted.db"
                        res = subprocess.run(
                            [sys.executable, "-m", "wa_crypt_tools.wadecrypt", str(key_path), str(enc_file), str(dec_test), "-y"],
                            capture_output=True,
                            text=True,
                        )
                        if res.returncode != 0:
                            errors.append(f"Reference decrypt failed for crypt14: {res.stderr}")
                        else:
                            dec_sha, _ = _compute_sha256(dec_test)
                            expected_sha = enc_data.get("plaintext_sha256")
                            if expected_sha and dec_sha.lower() != expected_sha.lower():
                                errors.append(f"crypt14 decrypted SHA-256 ({dec_sha}) != manifest plaintext_sha256 ({expected_sha})")
                except Exception as ex:
                    errors.append(f"Error during reference decrypt verification: {ex}")

        elif enc_format == "crypt15":
            key_path = dataset_dir / enc_data.get("key_ref", "keys/encrypted_backup.key")
            hex_path = dataset_dir / enc_data.get("hex_key_ref", "keys/root_key.hex")
            enc_file = dataset_dir / "msgstore.db.crypt15"
            if not key_path.is_file():
                errors.append(f"crypt15 encrypted_backup.key missing: {key_path}")
            if not hex_path.is_file():
                errors.append(f"crypt15 root_key.hex missing: {hex_path}")
            if not enc_file.is_file():
                errors.append(f"crypt15 encrypted file missing: {enc_file}")

            if key_path.is_file() and hex_path.is_file() and enc_file.is_file():
                try:
                    import subprocess
                    import tempfile
                    hex_key = hex_path.read_text(encoding="utf-8").strip()
                    with tempfile.TemporaryDirectory() as td:
                        # 1. Verify with key file
                        dec_test_1 = Path(td) / "dec1.db"
                        res1 = subprocess.run(
                            [sys.executable, "-m", "wa_crypt_tools.wadecrypt", str(key_path), str(enc_file), str(dec_test_1), "-y"],
                            capture_output=True,
                            text=True,
                        )
                        if res1.returncode != 0:
                            errors.append(f"Reference decrypt with encrypted_backup.key failed: {res1.stderr}")
                        else:
                            dec1_sha, _ = _compute_sha256(dec_test_1)
                            expected_sha = enc_data.get("plaintext_sha256")
                            if expected_sha and dec1_sha.lower() != expected_sha.lower():
                                errors.append(f"crypt15 dec1 SHA-256 ({dec1_sha}) != manifest plaintext_sha256 ({expected_sha})")

                        # 2. Verify with 64-hex string
                        dec_test_2 = Path(td) / "dec2.db"
                        res2 = subprocess.run(
                            [sys.executable, "-m", "wa_crypt_tools.wadecrypt", hex_key, str(enc_file), str(dec_test_2), "-y"],
                            capture_output=True,
                            text=True,
                        )
                        if res2.returncode != 0:
                            errors.append(f"Reference decrypt with 64-hex string failed: {res2.stderr}")
                        else:
                            dec2_sha, _ = _compute_sha256(dec_test_2)
                            expected_sha = enc_data.get("plaintext_sha256")
                            if expected_sha and dec2_sha.lower() != expected_sha.lower():
                                errors.append(f"crypt15 dec2 SHA-256 ({dec2_sha}) != manifest plaintext_sha256 ({expected_sha})")
                except Exception as ex:
                    errors.append(f"Error during crypt15 reference decrypt verification: {ex}")

        elif enc_format == "crypt15_negatives":
            expected_outcomes = enc_data.get("expected_outcomes", [])
            if not expected_outcomes:
                errors.append("DS-04 manifest encryption.expected_outcomes is empty")
            for item in expected_outcomes:
                fixture_rel = item.get("fixture")
                fixture_file = dataset_dir / fixture_rel
                if not fixture_file.is_file():
                    errors.append(f"Negative fixture file missing: {fixture_rel}")
                if not item.get("expected_outcome"):
                    errors.append(f"Missing expected_outcome for negative fixture: {fixture_rel}")

    is_valid = len(errors) == 0
    return is_valid, errors



def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an ArtifactX ground-truth dataset against its manifest.")
    parser.add_argument("path", type=str, help="Path to dataset directory (e.g. testdata/DS-01-dev)")
    args = parser.parse_args()

    dataset_path = Path(args.path)
    print(f"Verifying dataset: {dataset_path} ...")
    is_valid, errors = verify_dataset(dataset_path)

    if is_valid:
        print(f"[PASS] Dataset at {dataset_path} is valid and intact.")
        return 0
    else:
        print(f"[FAIL] Dataset at {dataset_path} has {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
