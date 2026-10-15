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
      "head_hash": "e3b0c44298fc...7852b855",
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

## 2026-10-15 B6 — WhatsApp Decryption & Key Security (spec: 04_WHATSAPP_DECRYPTION.md)

- **Updated Endpoint:** `POST /api/evidence/{id}/decryption/run` (B6.1, B6.2, B6.6, DEC-028)
  - **Purpose:** Decrypts WhatsApp Crypt14 or Crypt15 encrypted SQLite containers (`msgstore.db.crypt14`, `msgstore.db.crypt15`) using verified, independent decryptors with 100% byte-identical parity to reference tools.
  - **Pre-Stage Verification:** Invokes `ensure_integrity()` before reading ciphertext to cryptographically verify exhibit hash.
  - **Request Body (`DecryptionRunRequest`):**
    - `key_type`: Optional enum string:
      - `"crypt14_keyfile"`: Base64-encoded or raw Java-serialized 158-byte `key` file.
      - `"crypt15_hex"`: 64-character hexadecimal root encryption key.
      - `"crypt15_keyfile"`: Base64-encoded or raw Java-serialized 59-byte `encrypted_backup.key` file.
    - `key_data`: Optional `SecretStr` containing the key string/base64 payload.
    - Legacy `key_material`: Optional `SecretStr` accepted for backward compatibility.
    - Note: Passphrases for `.crypt15` are rejected with HTTP 200 `status="FAILED"` and typed error code `PASSPHRASE_NOT_SUPPORTED` (DEC-002).
  - **R5 Key Security (Radioactive Key Handling):**
    - Request models use Pydantic `SecretStr` and `repr=False`.
    - `ErrorLoggingMiddleware` strictly excludes path `/decryption/run` from logging request bodies or queries.
    - Custom FastAPI `RequestValidationError` handler strips the raw `input` field to ensure key material is never echoed back in HTTP 422 responses.
    - Keys are never persisted to the database, never written to disk, and never recorded in the audit log.
  - **Provenance & Persistence:**
    - On success, decrypted plaintext is validated across 5 verification tiers (GCM auth, zlib safety cap, SQLite header magic, in-memory `PRAGMA integrity_check`, WhatsApp schema family check).
    - Persisted as a separate `DerivedArtifact` row with `BYTEA` content (never overwrites evidence, R3).
    - Immutable audit event `DECRYPTION_SUCCESS` appended with provenance metadata (source evidence ID, source SHA-256, method, tool version, output SHA-256, and validation report).
  - **Sample Success Response (200 OK):**
    ```json
    {
      "operation_id": 1,
      "case_id": 1,
      "evidence_id": 2,
      "file_id": null,
      "format": "crypt14",
      "status": "SUCCESS",
      "input_sha256": "47a3...",
      "output_sha256": "81c3...",
      "derived_artifact_id": 1,
      "validation": {
        "gcm_auth_ok": true,
        "zlib_ok": true,
        "sqlite_header_ok": true,
        "integrity_check_ok": true,
        "whatsapp_schema_ok": true,
        "schema_family": "modern",
        "checksum_ok": true,
        "table_count": 28,
        "message_count": 380,
        "error_message": null
      },
      "parameters": {
        "key_type": "crypt14_keyfile",
        "key_fingerprint": "82a88463"
      },
      "error_message": null,
      "created_at": "2026-10-15T10:00:00.000000",
      "completed_at": "2026-10-15T10:00:00.250000"
    }
    ```
  - **Sample Failure Response (200 OK with typed status):**
    ```json
    {
      "operation_id": 2,
      "case_id": 1,
      "evidence_id": 2,
      "file_id": null,
      "format": "crypt14",
      "status": "FAILED",
      "input_sha256": "47a3...",
      "output_sha256": null,
      "derived_artifact_id": null,
      "validation": {},
      "parameters": {
        "key_type": "crypt14_keyfile",
        "error_code": "AUTH_FAILED"
      },
      "error_message": "Authentication tag mismatch: wrong key OR modified/corrupted data",
      "created_at": "2026-10-15T10:00:01.000000",
      "completed_at": "2026-10-15T10:00:01.050000"
## 2026-10-15 B7 — WhatsApp Parsing API & Forensic Endpoints (spec B7.5)
- **Endpoint:** `POST /api/whatsapp/parse/{evidence_id}`
  - **New route:** Primary forensic parsing route for WhatsApp plaintext `msgstore.db` evidence or decrypted SQLite artifacts.
  - Query parameter: `derived_artifact_id: Optional[str]` — when parsing from a decrypted derived artifact (B6).
  - Pre-flight integrity: runs `ensure_integrity` before parsing (R3).
  - Audit: appends hash-chained audit log entry (`action="whatsapp_parse"`).
  - Idempotency: replaces existing messages, chats, revocations, and edits for the evidence in a single transaction.
  - Response contract:
    ```json
    {
      "status": "success",
      "evidence_id": 1,
      "schema_family": "modern",
      "messages_count": 381,
      "chats_count": 5,
      "contacts_count": 5,
      "revocations_count": 1,
      "edits_count": 1,
      "limitations": []
    }
    ```
- **Endpoint:** `POST /api/whatsapp/evidence/{evidence_id}/analyze/whatsapp`
  - Backwards-compatible alias for existing frontend workflow, delegates to `parse_evidence_sync`.
- **Endpoint:** `GET /api/whatsapp/evidence/{evidence_id}/wa-messages`
  - Additive fields added to `MessageRead` response schema:
    - `key_id: Optional[str]`
    - `chat_row_id: Optional[int]`
    - `message_type_code: Optional[int]`
    - `message_type_name: Optional[str]`
    - `ts_raw: Optional[int]`
    - `ts_unit: Optional[str] = "ms"`
    - `ts_utc_ms: Optional[int]`
    - `received_ts_raw: Optional[int]`
    - `source_table: Optional[str] = "message"`
    - `source_row_id: Optional[int]`
    - `derived_artifact_id: Optional[str]`
    - `evidence_sha256: Optional[str]`
    - `quoted_row_id: Optional[int]`
    - `location_lat: Optional[float]`
    - `location_lon: Optional[float]`
    - `is_revoked: Optional[bool]`
    - `is_edited: Optional[bool]`
    - `flags: Optional[List[str]]`
- **Endpoint:** `GET /api/whatsapp/evidence/{evidence_id}/wa-chats`
  - New endpoint returning extracted chat threads, subject, participant JIDs, and provenance.
- **Endpoint:** `GET /api/whatsapp/evidence/{evidence_id}/wa-revocations`
  - New endpoint returning Tier-1 explicit message revocation findings (`message_revoked` rows) with deterministic strength, confidence score 1.0, and provenance.
- **Endpoint:** `GET /api/whatsapp/evidence/{evidence_id}/wa-edits`
  - New endpoint returning message edit history findings (`message_edit_info` rows) with deterministic strength, confidence score 1.0, and provenance.

## 2026-10-15 B9 — Telegram TDS/TL Parsing API & Forensic Endpoints (spec B9.6)
- **Endpoint:** `POST /api/telegram/parse/{evidence_id}`
  - **New route:** Primary forensic parsing route for Telegram `cache4.db` plain SQLite databases.
  - Multi-view extraction: parses both `main_view` and `post_wal_view` in-memory with zero disk writes (R4).
  - Pre-flight integrity: runs `ensure_integrity` before parsing (R3).
  - Audit: appends hash-chained audit log entry (`action="STAGE_COMPLETED"`).
  - Idempotency: replaces existing messages, dialogs, users, chats, and unparsed blobs for the evidence in a single transaction.
  - Response contract:
    ```json
    {
      "status": "success",
      "evidence_id": 1,
      "evidence_sha256": "888bb836...",
      "schema_family": "android_cache4",
      "messages_count": 33,
      "dialogs_count": 2,
      "users_count": 2,
      "chats_count": 1,
      "unparsed_blobs_count": 2,
      "views_parsed": ["main_view", "post_wal_view"],
      "limitations": []
    }
    ```
- **Endpoint:** `POST /api/telegram/evidence/{evidence_id}/analyze/telegram`
  - Backwards-compatible alias for existing frontend workflow, delegates to synchronous parser execution.
- **Endpoint:** `GET /api/telegram/evidence/{evidence_id}/tg-messages`
  - Additive fields added to `TelegramMessageRead` response schema:
    - `mid: Optional[int]`
    - `date_raw: Optional[int]`
    - `date_unit: Optional[str] = "seconds"`
    - `date_utc_ms: Optional[int]`
    - `view: Optional[str] = "main_view" | "post_wal_view"`
    - `source_table: Optional[str] = "messages_v2"`
    - `source_row_id: Optional[int]`
    - `finding_id: Optional[str]`
    - `confidence_score: Optional[float] = 1.0`
    - `strength: Optional[str] = "deterministic"`
    - `provenance: Optional[dict]`
    - `limitations: Optional[list]`
    - `trailing_bytes_info: Optional[dict]`
- **Endpoint:** `GET /api/telegram/evidence/{evidence_id}/tg-dialogs`
  - New endpoint returning extracted Telegram dialogs (`TelegramDialogRead`):
    - `dialog_id`, `peer_kind`, `peer_id`, `title`, `last_mid`, `unread_count`, `pinned`, `finding_id`, `provenance`, `limitations`.
- **Endpoint:** `GET /api/telegram/evidence/{evidence_id}/tg-users`
  - New endpoint returning extracted Telegram users (`TelegramUserRead`):
    - `uid`, `first_name`, `last_name`, `username`, `phone`, `is_self`, `contact`, `deleted`, `bot`, `finding_id`, `provenance`.
- **Endpoint:** `GET /api/telegram/evidence/{evidence_id}/tg-chats`
  - New endpoint returning extracted Telegram basic chats and channels (`TelegramChatRead`):
    - `did`, `chat_id`, `title`, `is_channel`, `is_group`, `participants_count`, `participant_uids`, `finding_id`, `provenance`.
- **Endpoint:** `GET /api/telegram/evidence/{evidence_id}/tg-unparsed-blobs`
  - New endpoint returning unparsed TL blobs (`TelegramUnparsedBlobRead`) with container column metadata, maintaining the `parsed + unparsed == rows_seen` invariant:
    - `table`, `row_id`, `mid`, `uid`, `constructor_id_hex`, `length`, `sha256`, `reason`, `container_metadata`, `finding_id`, `provenance`.

## 2026-10-15 B10 — Physical Deleted Data Recovery API (spec: 08_DELETED_DATA_RECOVERY.md)
- **Endpoint:** `POST /api/cases/{case_id}/recovery/run`
  - Pure in-memory physical carving and temporal recovery across case evidence (WAL historical versions, SQLite freelist, and intra-page slack spans).
  - Pre-flight integrity verification (`ensure_integrity()`).
  - Idempotent re-run: clears previous recovery records for evidence being re-analyzed before persisting.
  - Audit: appends hash-chained audit log entries `RECOVER_START` and `RECOVER_COMPLETE` (containing execution counts and hashes, zero message content per privacy/integrity rules).
  - Response: `RecoveryRunResponse`.
- **Endpoint:** `GET /api/cases/{case_id}/recovery/findings`
  - Additive query filter parameters:
    - `tier: Optional[int]` (1, 2, 3, 4)
    - `strength: Optional[str]` ("deterministic", "strong", "moderate", "weak_hint")
    - `kind: Optional[str]` ("revocation", "edit", "wal_resident", "freelist", "slack", "id_gap")
    - `validation_status: Optional[str]` ("FULL_RECORD_VALID", "PARTIAL", "DUPLICATE_OF_LIVE", "DUPLICATE_OF_OTHER_TIER", "INVALID_REJECTED")
  - Additive fields in `RecoveredFindingResponse`:
    - `finding_id: Optional[str]`
    - `tier: Optional[int]`
    - `kind: Optional[str]`
    - `strength: Optional[str]`
    - `confidence_score: Optional[float]`
    - `table_name: Optional[str]`
    - `frame_index: Optional[int]`
    - `recovered_fields: Dict[str, Any]`
    - `view: Optional[str]`
    - `evidence_sha256: Optional[str]`
    - `candidate_original_text: Optional[str]`


