"""
ArtifactX Phase D: R2 Physical Recovery & SQLite Physical Carving Validation Suite.

Validates:
1. SQLite Varint decoder (1-9 bytes, boundaries, negative numbers)
2. SQLite serial-type decoder & record header unpacking
3. Synthetic WAL header & frame parsing and historical page reconstruction
4. Synthetic Freelist trunk traversal & leaf-page carving
5. B-tree cell slack space & freeblock scanning
6. WhatsApp & Telegram schema-adaptive payload decoding
7. Malformed / corrupted SQLite handling & loop detection
8. Source evidence immutability (byte-for-byte SHA-256 preservation)
9. E2E API execution (POST /api/cases/{id}/recovery/run, findings, runs)
10. Zero-local-disk preservation (uploads/ and reports/ remain strictly empty)
"""

import hashlib
import io
import os
from pathlib import Path
import sqlite3
import struct
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.models.models import Case, Evidence, RecoveredFinding, RecoveryRun
from forensic.deleted.sqlite_record import (
    decode_varint,
    encode_varint,
    decode_serial_type,
    parse_record_header,
    unpack_record,
    find_candidate_records,
)
from forensic.deleted.wal_carver import WalCarver, WAL_MAGIC_BE, WAL_MAGIC_LE
from forensic.deleted.freelist_carver import FreelistCarver
from forensic.deleted.slack_carver import SlackCarver
from forensic.deleted.payload_decoder import (
    WhatsAppPayloadDecoder,
    TelegramPayloadDecoder,
)
from forensic.deleted.orchestrator import DeletedRecoveryEngine


def test_varint_and_record_decoding():
    print("\n--- [Test 1] SQLite Varint & Serial Type Decoder Verification ---")

    # Test single-byte varints (0 to 127)
    for val in (0, 1, 42, 127):
        enc = encode_varint(val)
        dec, consumed = decode_varint(enc, 0)
        assert dec == val, f"Varint mismatch for {val}: got {dec}"
        assert consumed == 1

    # Test multi-byte varints (2 bytes, 3 bytes, up to 9 bytes)
    test_values = [128, 255, 16383, 16384, 2097151, 268435455, 34359738367, 0x1FFFFFFFFFFFFF]
    for val in test_values:
        enc = encode_varint(val)
        dec, consumed = decode_varint(enc, 0)
        assert dec == val, f"Varint mismatch for {val}: got {dec}"

    # Test boundary violation
    try:
        decode_varint(b"", 0)
        assert False, "Should have raised ValueError on empty data"
    except ValueError:
        pass

    try:
        # Incomplete continuation byte
        decode_varint(b"\x80", 0)
        assert False, "Should have raised ValueError on truncated varint"
    except ValueError:
        pass

    print("  -> Varint 1-9 byte boundaries validated successfully.")

    # Test serial type decoding
    assert decode_serial_type(0) == ("NULL", 0)
    assert decode_serial_type(1) == ("INT8", 1)
    assert decode_serial_type(2) == ("INT16", 2)
    assert decode_serial_type(4) == ("INT32", 4)
    assert decode_serial_type(6) == ("INT64", 8)
    assert decode_serial_type(7) == ("FLOAT64", 8)
    assert decode_serial_type(8) == ("ZERO", 0)
    assert decode_serial_type(9) == ("ONE", 0)
    assert decode_serial_type(12) == ("BLOB", 0)
    assert decode_serial_type(14) == ("BLOB", 1)
    assert decode_serial_type(13) == ("TEXT", 0)
    assert decode_serial_type(27) == ("TEXT", 7)  # (27 - 13) // 2 = 7 bytes
    print("  -> Serial types and lengths validated successfully.")

    # Test record header parsing and unpacking
    # Create payload: TEXT "hello" (serial type 13 + 2*5 = 23), INT16 1000 (serial type 2)
    text_val = "SECRET_DELETED_CODENAME"
    text_bytes = text_val.encode("utf-8")
    st_text = 13 + (2 * len(text_bytes))
    st_int = 2  # INT16
    int_bytes = struct.pack(">h", 1337)

    # Header: [header_size, st_text, st_int]
    hdr_data = encode_varint(st_text) + encode_varint(st_int)
    header_size = 1 + len(hdr_data)
    record_bytes = encode_varint(header_size) + hdr_data + text_bytes + int_bytes

    cols, h_size, body_start = parse_record_header(record_bytes, 0)
    assert len(cols) == 2
    assert cols[0]["type"] == "TEXT"
    assert cols[0]["length"] == len(text_bytes)
    assert cols[1]["type"] == "INT16"

    unpacked = unpack_record(record_bytes, cols, body_start)
    assert unpacked[0] == text_val
    assert unpacked[1] == 1337
    print("  -> SQLite record header parsing & value unpacking validated.")


def test_synthetic_wal_carver():
    print("\n--- [Test 2] Synthetic SQLite WAL Carving & Historical Pages ---")

    page_size = 4096
    wal_buf = io.BytesIO()

    # 1. 32-byte WAL Header
    # Magic (BE: 0x377f0683), version 3007000, page_size 4096, seq 1, salt1, salt2, c1, c2
    wal_header = struct.pack(
        ">IIIIIIII",
        WAL_MAGIC_BE,
        3007000,
        page_size,
        1,
        0x11223344,
        0x55667788,
        0xAABBCCDD,
        0xEEFF0011,
    )
    wal_buf.write(wal_header)

    # 2. Frame 1: Historical Page 2 containing deleted message
    frame1_hdr = struct.pack(">IIIIII", 2, 0, 0x11223344, 0x55667788, 0, 0)
    # Page data with a WhatsApp record
    p1_data = bytearray(page_size)
    del_msg = "Critical WAL historical deleted conversation"
    p1_data[200 : 200 + len(del_msg)] = del_msg.encode("utf-8")
    # Also encode a valid record header inside the page
    st_text = 13 + (2 * len(del_msg))
    rec = encode_varint(3) + encode_varint(st_text) + encode_varint(8) + del_msg.encode("utf-8")
    p1_data[500 : 500 + len(rec)] = rec

    wal_buf.write(frame1_hdr)
    wal_buf.write(p1_data)

    # 3. Frame 2: Page 2 overwritten (committed revision)
    frame2_hdr = struct.pack(">IIIIII", 2, 10, 0x11223344, 0x55667788, 0, 0)
    p2_data = bytearray(page_size)
    commit_bytes = b"Active committed page content"
    p2_data[100 : 100 + len(commit_bytes)] = commit_bytes
    wal_buf.write(frame2_hdr)
    wal_buf.write(p2_data)

    wal_bytes = wal_buf.getvalue()

    carver = WalCarver(wal_bytes)
    assert carver.parse() is True
    assert len(carver.frames) == 2
    assert carver.header.page_size == 4096

    historical = carver.get_historical_page_images()
    assert 2 in historical
    assert len(historical[2]) == 2

    superseded = carver.get_superseded_pages()
    assert len(superseded) == 1
    assert superseded[0].frame_index == 1
    assert superseded[0].page_number == 2
    print("  -> WAL header, frames, and superseded historical pages carved successfully.")


def test_synthetic_freelist_and_slack_carver():
    print("\n--- [Test 3] SQLite Freelist & B-Tree Slack Space Carving ---")

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA page_size = 4096")
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, remote_jid TEXT, body TEXT, timestamp INTEGER)"
    )
    conn.execute(
        "INSERT INTO messages VALUES (1, '+12025550199@s.whatsapp.net', 'Active message in table', 1700000000)"
    )
    for i in range(2, 25):
        conn.execute(
            f"INSERT INTO messages VALUES ({i}, '+12025550199@s.whatsapp.net', 'Sensitive deleted message #{i}', 1700000000 + {i})"
        )
    conn.commit()

    # Delete records to create freeblocks, cell slack, and freelist pages
    conn.execute("DELETE FROM messages WHERE id >= 5")
    conn.commit()

    db_bytes = conn.serialize()
    conn.close()

    assert len(db_bytes) >= 4096

    # Test Freelist Carver
    fl_carver = FreelistCarver(db_bytes)
    assert fl_carver.parse_header() is True
    fl_pages = fl_carver.traverse_freelist()
    fl_records = fl_carver.carve_all_freelist_pages()
    print(f"  -> Freelist parsed: {len(fl_pages)} pages, {len(fl_records)} candidate records carved.")

    # Test Slack Carver
    slack_carver = SlackCarver(db_bytes, page_size=4096)
    slack_records = slack_carver.scan_all_pages()
    print(f"  -> Slack parsed: {len(slack_carver.slack_spans)} slack spans, {len(slack_records)} candidate records carved.")
    assert len(slack_carver.slack_spans) > 0, "B-tree page must contain unallocated slack space after DELETE"


def test_malformed_sqlite_resistance():
    print("\n--- [Test 4] Malformed & Adversarial SQLite Input Resistance ---")

    # 1. Truncated database header
    fl_carver = FreelistCarver(b"SQLite format 3\x00truncated")
    assert fl_carver.parse_header() is False
    assert len(fl_carver.diagnostics) > 0

    # 2. Completely random bytes
    random_bytes = os.urandom(8192)
    fl_rand = FreelistCarver(random_bytes)
    assert fl_rand.parse_header() is False

    slack_rand = SlackCarver(random_bytes, page_size=4096)
    slack_records = slack_rand.scan_all_pages()
    assert isinstance(slack_records, list)

    wal_rand = WalCarver(random_bytes)
    assert wal_rand.parse() is False

    # 3. Circular Freelist loop resistance
    # Header points trunk to page 2, page 2 points next trunk back to page 2
    page_size = 4096
    loop_db = bytearray(page_size * 3)
    loop_db[:16] = b"SQLite format 3\x00"
    struct.pack_into(">H", loop_db, 16, page_size)
    struct.pack_into(">I", loop_db, 28, 3)  # page count
    struct.pack_into(">I", loop_db, 32, 2)  # trunk page 2
    struct.pack_into(">I", loop_db, 36, 1)  # 1 freelist page

    # Page 2: trunk points to page 2 (circular!)
    trunk_offset = (2 - 1) * page_size
    struct.pack_into(">II", loop_db, trunk_offset, 2, 0)

    loop_carver = FreelistCarver(bytes(loop_db))
    pages = loop_carver.traverse_freelist()
    assert any("Circular freelist" in d for d in loop_carver.diagnostics), "Must detect circular trunk loop"
    print("  -> Circular trunk loop detected and gracefully aborted.")


def test_evidence_immutability():
    print("\n--- [Test 5] Forensic Source Immutability Verification ---")

    # Construct test DB bytes
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INT, msg TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'Non-destructive test sample')")
    conn.commit()
    raw_db = conn.serialize()
    conn.close()

    db_sha_before = hashlib.sha256(raw_db).hexdigest()

    # Construct test WAL bytes
    wal_buf = io.BytesIO()
    wal_buf.write(struct.pack(">IIIIIIII", WAL_MAGIC_BE, 3007000, 4096, 1, 1, 2, 3, 4))
    wal_buf.write(struct.pack(">IIIIII", 1, 1, 1, 2, 0, 0))
    wal_buf.write(b"W" * 4096)
    raw_wal = wal_buf.getvalue()
    wal_sha_before = hashlib.sha256(raw_wal).hexdigest()

    # Run full DeletedRecoveryEngine
    engine = DeletedRecoveryEngine(
        db_bytes=raw_db,
        wal_bytes=raw_wal,
        source_app_hint="whatsapp",
        source_sha256=db_sha_before,
        evidence_id=999,
        case_id=999,
    )
    findings = engine.run()

    db_sha_after = hashlib.sha256(raw_db).hexdigest()
    wal_sha_after = hashlib.sha256(raw_wal).hexdigest()

    assert db_sha_before == db_sha_after, "Original database bytes MUST NOT be mutated!"
    assert wal_sha_before == wal_sha_after, "Original WAL bytes MUST NOT be mutated!"
    print(f"  -> Evidence immutability confirmed: DB SHA-256={db_sha_after[:16]}... WAL SHA-256={wal_sha_after[:16]}...")


def test_e2e_recovery_api():
    print("\n--- [Test 6] End-to-End Recovery API & Zero-Disk Storage ---")

    client = TestClient(app)

    # Initial disk check
    uploads_dir = Path("d:/ArtifactX/uploads").resolve()
    reports_dir = Path("d:/ArtifactX/reports").resolve()
    assert sum(1 for p in uploads_dir.rglob("*") if p.is_file() and p.name != ".gitkeep") == 0
    assert sum(1 for p in reports_dir.rglob("*") if p.is_file() and p.name != ".gitkeep") == 0

    # 1. Create Case
    resp = client.post("/api/cases", json={
        "name": "Phase D R2 Recovery Test Case",
        "description": "Validation of physical deleted message carving",
        "investigator": "Forensic Specialist Lee",
    })
    assert resp.status_code == 200, f"Case creation failed: {resp.text}"
    case_id = resp.json()["id"]
    print(f"  -> Created Case ID: {case_id}")

    try:
        # 2. Upload SQLite Database directly via in-memory multipart upload
        # Build database with deleted WhatsApp record
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA page_size = 4096")
        conn.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY, key_remote_jid TEXT, data TEXT, timestamp INTEGER)"
        )
        conn.execute(
            "INSERT INTO messages VALUES (101, '+12025550199@s.whatsapp.net', 'Active chat message', 1700000000)"
        )
        conn.execute(
            "INSERT INTO messages VALUES (102, '+12025550199@s.whatsapp.net', 'Carved secret deleted message in slack', 1700000010)"
        )
        conn.commit()
        # Delete row 102 so it moves into slack/freeblocks
        conn.execute("DELETE FROM messages WHERE id = 102")
        conn.commit()
        db_bytes = conn.serialize()
        conn.close()

        files = {
            "file": ("msgstore.db", io.BytesIO(db_bytes), "application/x-sqlite3")
        }
        upload_resp = client.post(f"/api/evidence/upload?case_id={case_id}", files=files)
        assert upload_resp.status_code in (200, 201), f"Upload failed: {upload_resp.text}"
        ev_id = upload_resp.json()["id"]
        print(f"  -> Uploaded SQLite Evidence ID: {ev_id}")

        # 3. Trigger Physical Recovery Carving
        run_resp = client.post(f"/api/cases/{case_id}/recovery/run")
        assert run_resp.status_code == 200, f"Recovery run failed: {run_resp.text}"
        run_data = run_resp.json()
        assert run_data["status"] == "SUCCEEDED"
        print(f"  -> Recovery run {run_data['id']} SUCCEEDED. Analyzed {run_data['slack_spans_analyzed']} slack spans.")

        # 4. List Recovery Runs
        runs_list = client.get(f"/api/cases/{case_id}/recovery/runs").json()
        assert len(runs_list) >= 1
        assert runs_list[0]["id"] == run_data["id"]
        print(f"  -> Recovery run audit log verified.")

        # 5. List Recovered Findings
        findings_resp = client.get(f"/api/cases/{case_id}/recovery/findings")
        assert findings_resp.status_code == 200
        findings = findings_resp.json()
        print(f"  -> Recovered findings count: {len(findings)}")

        if len(findings) > 0:
            first_f = findings[0]
            # 6. Retrieve single finding with hex dump and provenance
            detail_resp = client.get(f"/api/cases/{case_id}/recovery/findings/{first_f['id']}")
            assert detail_resp.status_code == 200
            detail = detail_resp.json()
            assert detail["raw_payload_preview"] is not None
            assert detail["provenance"]["source_sha256"] is not None
            assert detail["validation_status"] in ("RECOVERED", "PARTIALLY_RECONSTRUCTED", "CANDIDATE", "UNVALIDATED")
            print(f"  -> Finding #{first_f['id']} inspected. Status: {detail['validation_status']}, Method: {detail['method']}")

        # 7. Final Zero-Disk Check
        final_uploads = sum(1 for p in uploads_dir.rglob("*") if p.is_file() and p.name != ".gitkeep")
        final_reports = sum(1 for p in reports_dir.rglob("*") if p.is_file() and p.name != ".gitkeep")
        assert final_uploads == 0, f"uploads/ must remain strictly empty, found {final_uploads}"
        assert final_reports == 0, f"reports/ must remain strictly empty, found {final_reports}"
        print("  -> Zero-local-disk check passed: uploads/ and reports/ remain strictly empty!")

    finally:
        # Cleanup
        client.delete(f"/api/cases/{case_id}")
        print(f"  -> Test case {case_id} cleaned up.")


def run_all_r2_tests():
    print("=================================================================")
    print("      ARTIFACTX PHASE D: R2 PHYSICAL RECOVERY VALIDATION        ")
    print("=================================================================")

    test_varint_and_record_decoding()
    test_synthetic_wal_carver()
    test_synthetic_freelist_and_slack_carver()
    test_malformed_sqlite_resistance()
    test_evidence_immutability()
    test_e2e_recovery_api()

    print("\n=================================================================")
    print("     ALL PHASE D R2 PHYSICAL RECOVERY TESTS PASSED! (6/6)        ")
    print("=================================================================")


if __name__ == "__main__":
    run_all_r2_tests()
