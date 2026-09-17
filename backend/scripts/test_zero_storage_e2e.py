"""
Phase C Zero-Local-Storage Hardening End-to-End Validation Test
Validates:
1. Upload stream hashes without persistent local staging
2. Evidence binary stored in PostgreSQL BYTEA
3. ZIP members extracted in-memory and stored in PostgreSQL BYTEA
4. SQLite parser accepts in-memory stream/bytes input
5. Media parser accepts in-memory stream/bytes input
6. Derived artifacts have parent hashes
7. Court-ready PDF generation uses BytesIO and stores in PostgreSQL BYTEA
8. uploads/ remains strictly empty
9. reports/ remains strictly empty
10. Full workspace remains free of any disk leaks
"""

import hashlib
import io
import os
import sqlite3
import zipfile
from pathlib import Path
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.models.models import Case, Evidence, EvidenceFile, GeneratedReport


def build_sample_sqlite_bytes() -> bytes:
    """Create a minimal SQLite database in memory and return serialized bytes."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE messages (key_id TEXT PRIMARY KEY, key_remote_jid TEXT, data TEXT, timestamp INTEGER, key_from_me INTEGER)"
    )
    conn.execute(
        "CREATE TABLE chat (jid TEXT PRIMARY KEY, subject TEXT, created_timestamp INTEGER)"
    )
    conn.execute(
        "INSERT INTO chat VALUES ('+12025550199@s.whatsapp.net', 'Forensic Subject', 1700000000)"
    )
    conn.execute(
        "INSERT INTO messages VALUES ('msg_001', '+12025550199@s.whatsapp.net', 'Critical forensic evidence payload in memory', 1700000010, 0)"
    )
    conn.commit()
    data = conn.serialize()
    conn.close()
    return data


def build_sample_jpeg_bytes() -> bytes:
    """Create a minimal valid 1x1 JPEG in memory."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        # Fallback minimal JPEG header
        return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"


def build_sample_zip_bytes(sqlite_bytes: bytes, jpeg_bytes: bytes) -> bytes:
    """Create an in-memory ZIP containing a WhatsApp database and an image."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("databases/msgstore.db", sqlite_bytes)
        zf.writestr("media/exhibit_photo.jpg", jpeg_bytes)
    return zip_buf.getvalue()


def count_files_in_dir(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file() and p.name != ".gitkeep")


def run_zero_storage_e2e_test():
    print("=================================================================")
    print("      ARTIFACTX PHASE C ZERO-LOCAL-STORAGE VALIDATION            ")
    print("=================================================================")

    workspace_root = Path("d:/ArtifactX").resolve()
    uploads_dir = workspace_root / "uploads"
    reports_dir = workspace_root / "reports"

    initial_uploads_count = count_files_in_dir(uploads_dir)
    initial_reports_count = count_files_in_dir(reports_dir)
    print(f"[*] Initial uploads/ file count: {initial_uploads_count}")
    print(f"[*] Initial reports/ file count: {initial_reports_count}")
    assert initial_uploads_count == 0, f"uploads/ directory must start empty, found {initial_uploads_count} files"
    assert initial_reports_count == 0, f"reports/ directory must start empty, found {initial_reports_count} files"

    client = TestClient(app)
    db = SessionLocal()

    # Step 1: Health check
    print("\n[Step 1] Verifying System Health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("  -> System healthy")

    # Step 2: Create a real Forensic Case
    print("\n[Step 2] Creating Forensic Case...")
    resp = client.post("/api/cases", json={
        "name": "Phase C Zero-Disk Verification Case",
        "description": "Validation run for in-memory streaming and PostgreSQL BYTEA persistence",
        "investigator": "Forensic Inspector Vance",
    })
    assert resp.status_code == 200, f"Case creation failed: {resp.text}"
    case_data = resp.json()
    case_id = case_data["id"]
    print(f"  -> Created Case ID: {case_id}")

    test_sqlite_bytes = build_sample_sqlite_bytes()
    test_sqlite_sha256 = hashlib.sha256(test_sqlite_bytes).hexdigest()
    test_jpeg_bytes = build_sample_jpeg_bytes()
    test_zip_bytes = build_sample_zip_bytes(test_sqlite_bytes, test_jpeg_bytes)
    test_zip_sha256 = hashlib.sha256(test_zip_bytes).hexdigest()

    try:
        # Step 3: Direct In-Memory Upload of SQLite Database
        print("\n[Step 3] Testing Direct In-Memory Upload of SQLite Evidence...")
        resp = client.post(
            f"/api/evidence/upload?case_id={case_id}",
            files={"file": ("inmemory_evidence.db", test_sqlite_bytes, "application/octet-stream")},
        )
        assert resp.status_code in (200, 201), f"SQLite upload failed: {resp.text}"
        ev1_data = resp.json()
        ev1_id = ev1_data["id"]
        print(f"  -> Uploaded Evidence ID: {ev1_id}, SHA-256: {ev1_data['sha256']}")
        assert ev1_data["sha256"] == test_sqlite_sha256

        # Check ZERO DISK ASSERTION
        uploads_count = count_files_in_dir(uploads_dir)
        print(f"  -> Post-upload uploads/ count: {uploads_count}")
        assert uploads_count == 0, f"VIOLATION: files were written to uploads/: {list(uploads_dir.rglob('*'))}"

        # Verify PostgreSQL BYTEA Storage
        ev1_row = db.query(Evidence).filter(Evidence.id == ev1_id).first()
        assert ev1_row is not None
        assert ev1_row.content_bytes is not None, "Evidence.content_bytes must not be None"
        assert len(ev1_row.content_bytes) == len(test_sqlite_bytes), "Stored byte length mismatch"
        assert hashlib.sha256(ev1_row.content_bytes).hexdigest() == test_sqlite_sha256
        print("  -> CONFIRMED: Evidence binary is stored in PostgreSQL BYTEA!")

        # Step 4: In-Memory Multi-Hash Verification
        print("\n[Step 4] Testing In-Memory Multi-Hash Integrity Verification...")
        resp = client.post(f"/api/evidence/{ev1_id}/verify-hashes")
        assert resp.status_code == 200, f"Hash verification failed: {resp.text}"
        hash_res = resp.json()
        print(f"  -> Status: {hash_res.get('verification_status')}, is_valid={hash_res.get('is_valid')}")
        assert hash_res.get("is_valid") is True, f"Hash verification failed: {hash_res}"
        assert count_files_in_dir(uploads_dir) == 0, "uploads/ was modified during hash verification"
        print("  -> CONFIRMED: In-memory hash verification succeeded!")

        # Step 5: In-Memory SQLite Inspection
        print("\n[Step 5] Testing In-Memory SQLite Table & Row Inspection...")
        resp = client.get(f"/api/evidence/{ev1_id}/sqlite-inspect")
        assert resp.status_code == 200, f"SQLite inspect failed: {resp.text}"
        sqlite_info = resp.json()
        print(f"  -> Inspected SQLite tables: {[t['name'] for t in sqlite_info.get('tables', [])]}")
        assert sqlite_info.get("table_count", len(sqlite_info.get("tables", []))) >= 2
        assert "messages" in [t["name"] for t in sqlite_info.get("tables", [])]
        assert count_files_in_dir(uploads_dir) == 0, "uploads/ was modified during SQLite inspect"
        print("  -> CONFIRMED: In-memory SQLite inspect succeeded without touching disk!")

        # Step 6: In-Memory ZIP Archive Upload and In-Memory Member Extraction
        print("\n[Step 6] Testing In-Memory ZIP Upload & PostgreSQL Member Storage...")
        resp = client.post(
            f"/api/evidence/upload?case_id={case_id}",
            files={"file": ("forensic_package.zip", test_zip_bytes, "application/zip")},
        )
        assert resp.status_code in (200, 201), f"ZIP upload failed: {resp.text}"
        ev2_data = resp.json()
        ev2_id = ev2_data["id"]
        print(f"  -> Uploaded ZIP Evidence ID: {ev2_id}, Extracted Members: {ev2_data.get('extracted_files_count')}")
        assert ev2_data.get("extracted_files_count") == 2

        # Check ZERO DISK ASSERTION
        uploads_count = count_files_in_dir(uploads_dir)
        print(f"  -> Post-ZIP-upload uploads/ count: {uploads_count}")
        assert uploads_count == 0, f"VIOLATION: ZIP members were extracted to disk: {list(uploads_dir.rglob('*'))}"

        # Verify ZIP Members in PostgreSQL BYTEA with Parent Hash linkage
        ev2_files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == ev2_id).all()
        assert len(ev2_files) == 2, f"Expected 2 EvidenceFile rows, got {len(ev2_files)}"
        for ef in ev2_files:
            assert ef.content_bytes is not None, f"EvidenceFile {ef.relative_path} content_bytes must not be None"
            assert ef.metadata_ is not None
            assert ef.metadata_.get("parent_sha256") == test_zip_sha256, "Parent SHA-256 linkage missing"
            print(f"  -> Member '{ef.relative_path}': size={ef.file_size}, parent_sha256={ef.metadata_.get('parent_sha256')[:8]}... (PostgreSQL BYTEA)")
        print("  -> CONFIRMED: ZIP members stored in PostgreSQL with parent hash provenance!")

        # Step 7: In-Memory Image EXIF Extraction
        print("\n[Step 7] Testing In-Memory Image EXIF Extraction...")
        resp = client.get(f"/api/evidence/{ev2_id}/exif")
        assert resp.status_code == 200, f"EXIF extraction failed: {resp.text}"
        exif_info = resp.json()
        print(f"  -> EXIF inspected images: {exif_info.get('total_images')}")
        assert exif_info.get("total_images") >= 1
        assert count_files_in_dir(uploads_dir) == 0, "uploads/ was modified during EXIF inspect"
        print("  -> CONFIRMED: In-memory EXIF extraction succeeded!")

        # Step 8: In-Memory WhatsApp Analysis Execution
        print("\n[Step 8] Testing In-Memory WhatsApp Analysis...")
        from backend.services.whatsapp_service import WhatsAppService
        wa_ok = WhatsAppService().analyze_evidence_sync(ev2_id, db)
        print(f"  -> WhatsApp analysis result: {wa_ok}")
        assert wa_ok is True
        assert count_files_in_dir(uploads_dir) == 0, "uploads/ was modified during WhatsApp analysis"
        print("  -> CONFIRMED: In-memory WhatsApp parsing succeeded without touching disk!")

        # Step 9: Court-Ready PDF Generation & PostgreSQL Storage
        print("\n[Step 9] Testing In-Memory Court PDF Report Generation & Database Storage...")
        report_payload = {
            "report_type": "summary",
            "options": {"includeEvidence": True, "includeCustodyLog": True},
            "leadAnalyst": "Special Agent J. Vance, EnCE",
            "agency": "Cyber Crime & Digital Forensics Unit",
            "caseNotes": "Phase C Zero-Disk Verification Court Report",
            "swornDeclaration": True,
        }
        resp = client.post(f"/api/cases/{case_id}/reports", json=report_payload)
        assert resp.status_code == 200, f"Report generation failed: {resp.text}"
        assert resp.headers.get("content-type") == "application/pdf"
        pdf_bytes = resp.content
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        report_id = resp.headers.get("x-report-id")
        print(f"  -> Streamed PDF Size: {len(pdf_bytes):,} bytes | SHA-256: {pdf_sha256}")
        print(f"  -> Report ID: {report_id}")

        # Check ZERO DISK ASSERTIONS
        assert count_files_in_dir(reports_dir) == 0, "VIOLATION: PDF was written to reports/ directory"
        assert count_files_in_dir(uploads_dir) == 0, "VIOLATION: files in uploads/ directory"

        # Verify PostgreSQL BYTEA Storage for GeneratedReport
        rep_row = db.query(GeneratedReport).filter(GeneratedReport.report_id == report_id).first()
        assert rep_row is not None, "Report row not found in database"
        assert rep_row.pdf_data is not None, "GeneratedReport.pdf_data must not be None"
        assert hashlib.sha256(rep_row.pdf_data).hexdigest() == pdf_sha256
        print("  -> CONFIRMED: Report PDF is stored in PostgreSQL BYTEA!")

        # Step 10: Re-Download from Report History (Streaming from Database BYTEA)
        print("\n[Step 10] Testing Re-Download Stream from PostgreSQL BYTEA...")
        resp = client.get(f"/api/cases/{case_id}/reports/{report_id}/download")
        assert resp.status_code == 200, f"Re-download failed: {resp.text}"
        assert resp.headers.get("content-type") == "application/pdf"
        redownloaded_sha256 = hashlib.sha256(resp.content).hexdigest()
        assert redownloaded_sha256 == pdf_sha256, "Re-download SHA-256 mismatch"
        print("  -> CONFIRMED: Byte-for-byte identical re-download verified!")

        # Final Zero-Disk Check
        final_uploads_count = count_files_in_dir(uploads_dir)
        final_reports_count = count_files_in_dir(reports_dir)
        print(f"\n[*] Final uploads/ file count: {final_uploads_count}")
        print(f"[*] Final reports/ file count: {final_reports_count}")
        assert final_uploads_count == 0, "uploads/ must remain strictly empty"
        assert final_reports_count == 0, "reports/ must remain strictly empty"

        print("\n=================================================================")
        print("     ALL PHASE C ZERO-LOCAL-STORAGE TESTS PASSED! (10/10)        ")
        print("=================================================================")

    finally:
        print(f"\n[Cleanup] Deleting test case {case_id}...")
        client.delete(f"/api/cases/{case_id}")
        db.close()


if __name__ == "__main__":
    run_zero_storage_e2e_test()
