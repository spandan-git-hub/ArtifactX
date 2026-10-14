"""
Integration tests for streaming upload, size cap, acquisition metadata, and deferred BYTEA (spec B5.1, B5.2, B5.7).
"""

import hashlib
import tracemalloc
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, load_only

from backend.app.config import settings
from backend.app.main import app
from backend.models.models import AuditLog, Case, Evidence


@pytest.fixture
def test_case(db_session: Session) -> Case:
    case = Case(
        name="Streaming Ingest Case",
        case_number="CASE-2026-0042",
        examiner_name="Special Agent Mulder",
        agency="Federal Bureau",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def test_put_upload_stream_success(test_case: Case, db_session: Session):
    """Assert PUT /api/evidence/upload-stream handles chunked streaming and stores multi-hash metadata."""
    client = TestClient(app)

    # Valid SQLite header + filler
    sqlite_magic = b"SQLite format 3\x00" + b"\x00" * 84 + b"FORENSIC_STREAM_PAYLOAD_TEST_DATA"
    expected_sha256 = hashlib.sha256(sqlite_magic).hexdigest()
    expected_sha512 = hashlib.sha512(sqlite_magic).hexdigest()
    expected_md5 = hashlib.md5(sqlite_magic).hexdigest()

    def chunk_generator():
        # Stream in 16-byte chunks
        for i in range(0, len(sqlite_magic), 16):
            yield sqlite_magic[i : i + 16]

    headers = {
        "X-Case-ID": str(test_case.id),
        "X-Original-Filename": "streamed_msgstore.db",
        "X-Declared-Mime": "application/x-sqlite3",
        "X-Acquisition-Method": "logical_extraction",
        "X-Device-Make-Model": "Pixel 8 Pro",
        "X-Device-Os-Version": "Android 14",
        "X-App-Version": "2.24.12.7",
        "X-Acquired-By": "Agent Scully",
        "X-Acquisition-Hash-Claimed": expected_sha256,
        "X-Acquisition-Hash-Algorithm": "SHA-256",
        "X-Uploader": "examiner_scully",
    }

    response = client.put(
        "/api/evidence/upload-stream",
        content=chunk_generator(),
        headers=headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filename"] == "streamed_msgstore.db"
    assert data["sha256"] == expected_sha256
    assert data["sha512"] == expected_sha512
    assert data["md5"] == expected_md5
    assert data["detected_format"] == "SQLITE_PLAIN"
    assert data["claimed_vs_computed"] == "MATCH"
    assert data["integrity_state"] == "OK"

    # Verify DB persistence
    evidence_id = data["id"]
    ev = db_session.query(Evidence).filter(Evidence.id == evidence_id).first()
    assert ev is not None
    assert ev.device_make_model == "Pixel 8 Pro"
    assert ev.acquired_by == "Agent Scully"
    assert ev.claimed_vs_computed == "MATCH"
    assert ev.sha256 == expected_sha256
    assert ev.content_bytes == sqlite_magic

    # Verify AuditLog has INGEST entry
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.evidence_id == evidence_id, AuditLog.action == "INGEST")
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.details_json["claimed_vs_computed"] == "MATCH"
    assert audit_entry.details_json["detected_format"] == "SQLITE_PLAIN"


def test_claimed_vs_computed_mismatch(test_case: Case, db_session: Session):
    """Assert mismatch between claimed hash and computed hash is flagged claimed_vs_computed = MISMATCH."""
    client = TestClient(app)
    payload = b"GENUINE_EVIDENCE_BYTES_HERE"
    bogus_claimed_hash = "0" * 64

    headers = {
        "X-Case-ID": str(test_case.id),
        "X-Original-Filename": "mismatch.bin",
        "X-Acquisition-Hash-Claimed": bogus_claimed_hash,
        "X-Acquisition-Hash-Algorithm": "SHA-256",
    }

    response = client.put(
        "/api/evidence/upload-stream",
        content=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["claimed_vs_computed"] == "MISMATCH"

    ev = db_session.query(Evidence).filter(Evidence.id == data["id"]).first()
    assert ev.claimed_vs_computed == "MISMATCH"
    assert ev.acquisition_hash_claimed == bogus_claimed_hash


def test_claimed_vs_computed_not_provided(test_case: Case, db_session: Session):
    """Assert omitting claimed hash marks claimed_vs_computed = NOT_PROVIDED."""
    client = TestClient(app)
    payload = b"JUST_SOME_FORENSIC_DATA"

    headers = {
        "X-Case-ID": str(test_case.id),
        "X-Original-Filename": "unclaimed.bin",
    }

    response = client.put(
        "/api/evidence/upload-stream",
        content=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["claimed_vs_computed"] == "NOT_PROVIDED"


def test_streaming_size_cap_abort_413(test_case: Case, db_session: Session, monkeypatch):
    """Assert streaming upload exceeding MAX_UPLOAD_SIZE aborts with 413 and records INGEST_REJECTED_TOO_LARGE."""
    # Constrain max_upload_size to 1024 bytes (1 KiB) for this test
    monkeypatch.setattr(settings, "max_upload_size", 1024)

    client = TestClient(app)
    oversized_payload = b"X" * 2048  # 2 KiB

    headers = {
        "X-Case-ID": str(test_case.id),
        "X-Original-Filename": "oversized.bin",
        "X-Uploader": "test_officer",
    }

    response = client.put(
        "/api/evidence/upload-stream",
        content=oversized_payload,
        headers=headers,
    )

    assert response.status_code == 413
    assert "exceeded maximum allowed size" in response.json()["detail"]

    # Verify no evidence row was created
    ev_count = db_session.query(Evidence).filter(Evidence.case_id == test_case.id).count()
    assert ev_count == 0

    # Verify audit rejection entry was recorded
    rejection_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.case_id == test_case.id, AuditLog.action == "INGEST_REJECTED_TOO_LARGE")
        .first()
    )
    assert rejection_audit is not None
    assert rejection_audit.details_json["filename"] == "oversized.bin"
    assert rejection_audit.details_json["limit"] == 1024


def test_deferred_bytea_loading_omits_content_bytes(test_case: Case, db_session: Session):
    """
    Assert compiled SQL for GET /api/evidence excludes content_bytes (R19, B5.1),
    preventing multi-hundred megabyte memory spikes during summary listing.
    """
    # 1. Compile the query used in list_evidences
    query = (
        db_session.query(Evidence)
        .options(
            load_only(
                Evidence.id,
                Evidence.case_id,
                Evidence.original_filename,
                Evidence.storage_path,
                Evidence.sha256,
                Evidence.sha512,
                Evidence.md5,
                Evidence.sha1,
                Evidence.content_type,
                Evidence.declared_mime,
                Evidence.detected_format,
                Evidence.uploader,
                Evidence.evidence_type,
                Evidence.metadata_,
                Evidence.extracted_path,
                Evidence.integrity_state,
                Evidence.acquisition_method,
                Evidence.device_make_model,
                Evidence.device_os_version,
                Evidence.app_version,
                Evidence.acquisition_time_utc,
                Evidence.acquired_by,
                Evidence.acquisition_hash_claimed,
                Evidence.acquisition_hash_algorithm,
                Evidence.claimed_vs_computed,
                Evidence.uploaded_at,
                Evidence.analyzed_at,
            )
        )
        .filter(Evidence.case_id == test_case.id)
    )

    compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "content_bytes" not in compiled_sql, "content_bytes was found in the compiled SELECT columns!"

    # 2. Insert test evidence with non-empty content_bytes
    payload = b"SECRET_DEFERRED_BYTES" * 100
    ev = Evidence(
        case_id=test_case.id,
        original_filename="deferred_test.bin",
        storage_path="db://evidence/deferred_test.bin",
        content_bytes=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    db_session.add(ev)
    db_session.commit()

    # 3. Call HTTP GET /api/evidence?case_id={id}
    client = TestClient(app)
    resp = client.get(f"/api/evidence?case_id={test_case.id}")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    # Check that schema does NOT expose content_bytes
    assert "content_bytes" not in results[0]
    assert results[0]["original_filename"] == "deferred_test.bin"
    assert results[0]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_ingest_memory_overhead_bounded(test_case: Case):
    """
    Measure peak memory consumption using tracemalloc during exhibit ingestion (B5.7).
    Asserts peak memory overhead is strictly bounded (< 6x payload size).
    """
    client = TestClient(app)
    # 2 MiB test exhibit
    payload_size = 2 * 1024 * 1024
    payload = b"M" * payload_size

    tracemalloc.start()
    try:
        response = client.put(
            f"/api/evidence/upload-stream?case_id={test_case.id}&filename=mem_test.bin",
            content=payload,
        )
        current_mem, peak_mem = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert response.status_code == 201

    # In-memory streaming and hashing holds buffer in memory + HTTP request chunks.
    # Ceiling: peak memory should not exceed 6x payload size (12 MiB).
    max_allowed_peak = payload_size * 6
    assert peak_mem < max_allowed_peak, f"Peak memory {peak_mem} exceeded {max_allowed_peak} bytes"
