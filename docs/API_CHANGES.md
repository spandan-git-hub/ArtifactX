# ArtifactX — API Changes Log

Maintained per `master.md` §1 and §6. Tracks all backend API contract changes so the frontend can be updated accordingly.

---

## 2026-10-13 A2 — GET /api/health
- **Old contract (per specification/legacy design):** Included `demo_mode: bool` field in health check response:
  ```json
  {
    "status": "ok",
    "app": "ArtifactX",
    "version": "1.0.0",
    "demo_mode": false
  }
  ```
- **New contract (verified in A0 & enforced in A2):** `demo_mode` field is removed. Only application status, name, and version are returned:
  ```json
  {
    "status": "ok",
    "app": "ArtifactX",
    "version": "1.0.0"
  }
  ```
- **Demo routes status:** No `/api/demo` routes exist (returns 404). All demo endpoints and schemas are absent.

## 2026-10-13 A4 — GET /api/cases/{case_id} & POST /api/cases/{case_id}/reports
- **Endpoint:** `GET /api/cases/{case_id}`
  - **Old contract:** Analysis stage 4 was named `"Court Export"` with description `"Forensic audit complete; ready for court PDF report export."`:
    ```json
    {
      "analysis_stage": {
        "stage_number": 4,
        "stage_name": "Court Export",
        "description": "Forensic audit complete; ready for court PDF report export."
      }
    }
    ```
  - **New contract:** Stage 4 renamed to `"Report Export"` with description `"Forensic audit complete; ready for report export."`:
    ```json
    {
      "analysis_stage": {
        "stage_number": 4,
        "stage_name": "Report Export",
        "description": "Forensic audit complete; ready for report export."
      }
    }
    ```
- **Endpoint:** `POST /api/cases/{case_id}/reports`
  - Route path remains unchanged (`/api/cases/{case_id}/reports`).
  - Function renamed internally from `generate_court_report` to `generate_report`.
  - Filename in `Content-Disposition` header changed from `ArtifactX_CourtReport_Case{case_id}_{type}_{timestamp}.pdf` to `ArtifactX_ForensicReport_Case{case_id}_{type}_{timestamp}.pdf`.
  - Response error messages on generation failure sanitized from `"Failed to generate court report: ..."` to `"Failed to generate forensic report: ..."`.
## 2026-10-13 A5 — Zero-Disk Storage & Legacy Row Fallbacks
- **Endpoint:** `POST /api/evidence/{evidence_id}/verify-hashes`
  - **Old contract:** Attempted to read from disk (`storage_path` or `UPLOADS_DIR / storage_path`) when `content_bytes` was NULL.
  - **New contract:** Strictly in-memory verification. For legacy rows lacking binary content in database, returns `verification_status="LEGACY_UNVERIFIABLE"`, `is_valid=false`, and `main_file.actual_sha256="LEGACY_UNVERIFIABLE"`.
  - Added field: `"integrity_state": "OK" | "LEGACY_UNVERIFIABLE"`.
  - Sample response for legacy row:
    ```json
    {
      "evidence_id": 1,
      "case_id": 1,
      "filename": "legacy_msgstore.db",
      "verification_status": "LEGACY_UNVERIFIABLE",
      "integrity_state": "LEGACY_UNVERIFIABLE",
      "is_valid": false,
      "verified_at": "2026-10-13T22:00:00.000000",
      "main_file": {
        "storage_path": "uploads/legacy_msgstore.db",
        "expected_sha256": "e3b0c44298fc...",
        "actual_sha256": "LEGACY_UNVERIFIABLE",
        "expected_md5": null,
        "actual_md5": "LEGACY_UNVERIFIABLE",
        "expected_sha1": null,
        "actual_sha1": "LEGACY_UNVERIFIABLE",
        "is_intact": false
      },
      "extracted_files_summary": {
        "total": 0,
        "matched": 0,
        "mismatched": 0
      },
      "files": []
    }
    ```
- **Endpoint:** `GET /api/cases/{case_id}/workspace`
  - Added `legacy_unverifiable_count` to `summary_counts`.
  - Added `integrity_state` to each item in `active_evidence[]`.
- **Endpoint:** `GET /api/cases/{case_id}/reports/summary`
  - Added `legacy_unverifiable_count` integer count field to `EvidenceSummary`.
- **Endpoint:** `GET /api/evidence` & `GET /api/evidence/{evidence_id}`
  - Added `integrity_state` to `EvidenceRead` response schema.
- **Endpoint:** `GET /api/evidence/{evidence_id}/files/{file_id}`
  - Returns in-memory binary response (`Response(content=...)`) directly from database storage instead of disk file (`FileResponse`). Returns 404 if bytes are unavailable on legacy rows.

## 2026-10-13 A6 — Remove / Demote Unvalidated Decryptors
- **Endpoint:** `POST /api/evidence/{evidence_id}/decryption/run`
  - **Old contract:** Accepted `passcode` (Telegram PIN), dispatched to unvalidated engines (Telegram SQLCipher, Telegram MTProto, WhatsApp .enc media, legacy Crypt12/14/15), attempted in-memory decryption.
  - **New contract:**
    - `passcode` field removed from `DecryptionRunRequest`. Key input is strictly `key_material: Optional[str]`.
    - Telegram SQLCipher, Telegram MTProto, and WhatsApp .enc media engines removed.
    - Legacy WhatsApp `crypt12/14/15` classes unregistered from orchestrator pending independent validated implementations in Phase B6.
    - When called without a registered validated plugin, returns HTTP 200 with typed state `status="DECRYPTOR_NOT_AVAILABLE"` and `error_message` describing demotion.
    - Example response:
      ```json
      {
        "operation_id": 1,
        "case_id": 1,
        "evidence_id": 1,
        "file_id": null,
        "format": "crypt14",
        "status": "DECRYPTOR_NOT_AVAILABLE",
        "input_sha256": "aabbccddeeff...",
        "output_sha256": null,
        "derived_artifact_id": null,
        "validation": {},
        "parameters": {},
        "error_message": "Decryptor for format 'crypt14' is not available. Unvalidated decryptors were demoted pending Phase B6.",
        "created_at": "2026-10-13T22:30:00.000000",
        "completed_at": "2026-10-13T22:30:00.000000"
      }
      ```
- **Endpoint:** `POST /api/evidence/{evidence_id}/decryption/detect`
  - Excludes known high-entropy containers (ZIP, GZIP, JPEG, PNG, MP4/MOV, 7z, RAR, PDF) by magic bytes from being flagged as encrypted ciphertext (`is_encrypted=false`, `format=null`).
  - Never claims `sqlcipher`, `mtproto`, or `whatsapp_enc`.
  - Reports unknown high-entropy inputs (>7.5 bits/byte without recognized container or crypt markers) honestly as `UNKNOWN_ENCRYPTED_KEY_REQUIRED` with no format claim.

## 2026-10-14 B5 — Ingest, Integrity & Audit Chain (spec: 03_INGEST_INTEGRITY_AUDIT.md)

- **New Endpoint:** `PUT /api/evidence/upload-stream` (B5.1, DEC-012)
  - **Purpose:** Pure in-memory streaming upload endpoint that bypasses FastAPI/Starlette `tempfile.SpooledTemporaryFile` disk spooling, strictly enforcing Rule R4 (zero disk writes).
  - **Query Parameters / Headers:**
    - `case_id` (query) or `X-Case-ID` (header) [required]
    - `filename` (query) or `X-Original-Filename` (header)
    - `X-Declared-Mime` (header)
    - `X-Acquisition-Method` (header, e.g. `logical_extraction`, `physical_extraction`, `cloud_export`)
    - `X-Device-Make-Model` (header, e.g. `Google Pixel 8 Pro`)
    - `X-Device-Os-Version` (header, e.g. `Android 14 (UP1A.231105.003)`)
    - `X-App-Version` (header, e.g. `2.24.12.7`)
    - `X-Acquired-By` (header, examiner / technician identifier)
    - `X-Acquisition-Hash-Claimed` (header, pre-acquisition hex hash)
    - `X-Acquisition-Hash-Algorithm` (header, e.g. `SHA-256`, `MD5`)
    - `X-Uploader` (header, analyst / user identifier)
  - **Status Codes:**
    - `201 Created`: Exhibit ingested, multi-hashed, format-detected, and verified against claimed hash.
    - `400 Bad Request`: Empty stream (0 bytes), invalid ZIP path traversal, or missing case ID.
    - `404 Not Found`: Target case ID does not exist.
    - `413 Content Too Large`: Stream exceeded `MAX_UPLOAD_SIZE` (default 256 MiB). Rejection is recorded as `INGEST_REJECTED_TOO_LARGE` in the audit log; 0 bytes persisted.
  - **Sample Response (201 Created):**
    ```json
    {
      "id": 42,
      "filename": "msgstore.db",
      "sha256": "4b971a823e...",
      "sha512": "7f098a...",
      "md5": "a3b1...",
      "sha1": "c9d2...",
      "size": 1048576,
      "evidence_type": "file",
      "detected_format": "SQLITE_PLAIN",
      "claimed_vs_computed": "MATCH",
      "integrity_state": "OK",
      "is_zip": false,
      "extracted_files_count": 0
    }
    ```

- **New Endpoint:** `GET /api/audit/verify` (B5.5)
  - **Purpose:** Cryptographically verifies the unbroken hash chain of the append-only `audit_log` table from genesis to head.
  - **Query Parameters:** `case_id: Optional[int]`
  - **Response (200 OK):**
    ```json
    {
      "ok": true,
      "checked": 128,
      "head_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "first_bad_seq": null,
      "error_detail": null
    }
    ```
  - **Tamper Response (when discrepancy detected):**
    ```json
    {
      "ok": false,
      "checked": 45,
      "head_hash": "...",
      "first_bad_seq": 46,
      "error_detail": "Entry hash mismatch at seq 46: recomputed != stored"
    }
    ```

- **Updated Endpoint:** `GET /api/evidence` & `GET /api/evidence/{id}` (B5.1, B5.2, R19)
  - `EvidenceRead` schema updated to expose acquisition metadata and multi-hashes:
    - `sha512`, `md5`, `sha1`
    - `declared_mime`, `detected_format`, `uploader`
    - `acquisition_method`, `device_make_model`, `device_os_version`, `app_version`
    - `acquisition_time_utc`, `acquired_by`, `acquisition_hash_claimed`, `acquisition_hash_algorithm`
    - `claimed_vs_computed` (`"MATCH"` | `"MISMATCH"` | `"NOT_PROVIDED"`)
  - **Deferred BYTEA Query Optimization (R19):** `GET /api/evidence` strictly excludes `content_bytes` from the SQL column list via `load_only`, preventing memory spikes during exhibit listing.



