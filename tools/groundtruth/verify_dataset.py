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
