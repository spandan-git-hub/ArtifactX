# ArtifactX — Backend: Complete Specification & Audit

> **What this file is:** The definitive truth of the backend — what exists, what is broken, what must be written or rewritten.  
> Every section states the **current state** and the **required state** if they differ.  
> An AI reading this file should be able to fix every hole without needing any other context.

---

## 1. Stack

| Component | Current | Required |
|-----------|---------|----------|
| Framework | FastAPI ✅ | FastAPI |
| Language | Python 3.13 ✅ | Python 3.13 |
| ORM | SQLAlchemy 2.0 ✅ | SQLAlchemy 2.0 |
| DB | PostgreSQL (Neon cloud) via `.env` ✅ | PostgreSQL |
| Validation | Pydantic v2 ✅ | Pydantic v2 |
| PDF Engine | ReportLab (In-Memory Court PDF Generator) ✅ | ReportLab |
| Logging | structlog ✅ | structlog |
| Image EXIF | Pillow + ExifRead ✅ | Pillow + ExifRead |
| Hashing | hashlib (SHA-256, MD5, SHA-1) ✅ | hashlib |
| PYTHONPATH | Must be set to project root | `$env:PYTHONPATH = "D:\ArtifactX"` |

---

## 2. Entry Point — `backend/app/main.py`

**Current state:** Working. CORS, lifespan, all routers registered, `ErrorLoggingMiddleware` applied. Health endpoint works.

**CORS Fix Required:** Ensure CORS `allow_origins` includes port 5174 (used when Vite port 5173 is occupied).

```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
],
```

---

## 3. Configuration — `backend/app/config.py`

Reads `.env` from project root using `pydantic-settings`.

```
DATABASE_URL=postgresql://neondb_owner:...@neon.tech/neondb?sslmode=require&channel_binding=require
DEMO_MODE=true
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=1073741824
```

---

## 4. Database Models — `backend/models/models.py`

All database tables and their forensic purpose:

| Table | Forensic Purpose | Status |
|-------|------------------|--------|
| `cases` | Case metadata, investigator name, legal reference | ✅ Correct |
| `evidence` | Ingested evidence containers, original archive names, root hashes | ✅ Correct |
| `evidence_files` | Per-file manifest: relative path, size, MIME, SHA-256, MD5, SHA-1 | ✅ Correct |
| `analysis_results` | Forensic parser run records and execution status | ✅ Correct |
| `wa_messages` | Extracted WhatsApp messages (body, timestamp, JIDs, media, deletion tags) | ✅ Correct |
| `wa_contacts` | WhatsApp contact book (JID, display name, phone number, status) | ✅ Correct |
| `wa_groups` | WhatsApp group chats (JID, subject, creator, creation date) | ✅ Correct |
| `tg_messages` | Extracted Telegram messages (message ID, sender ID, text, date, media) | ✅ Correct |
| `tg_contacts` | Telegram contacts (user ID, first/last name, phone, handle) | ✅ Correct |
| `tg_groups` | Telegram channels & chat groups | ✅ Correct |
| `timeline_events` | Normalized multi-app chronological timeline event records | ✅ Correct |
| `deleted_messages` | Detected sequence/timestamp gaps, missing message counts, confidence | ✅ Correct |
| `media_items` | Extracted media attachments, EXIF data (GPS, camera, creation date) | ✅ Correct |
| `correlation_edges` | Cross-platform entity links & cross-app message correlation nodes | ✅ Correct |
| `generated_reports` | **In-App Report History Tracker**: tracks generated report ID, case ID, report type, analyst, timestamp, size bytes, and SHA-256 verification hash | 🆕 New Model |
| `analysis_logs` | Deep diagnostic logs during evidence parsing runs | ✅ Correct |
| `activity_logs` | **Chain-of-Custody Audit Log** (ingest, hash verify, parse, report export events) | ✅ Correct |
| `error_logs` | System exception logs and stack traces | ✅ Correct |

---

## 5. API Layer Specifications — `backend/api/`

### 5.1 `evidence.py` — Ingestion & Cryptographic Integrity
- **Multipart Upload:** Supports `.zip`, `.db`, `.sqlite`, `.tar.gz`.
- **Cryptographic Hashing:** Computes SHA-256, MD5, and SHA-1 for every file during extraction.
- **`POST /api/evidence/{id}/verify-hashes`:** Re-calculates on-disk file hashes and compares against recorded `EvidenceFile` manifest. Returns integrity report (`VERIFIED_INTACT` or list of mismatched files).
- **`GET /api/evidence/{id}/exif`:** Extracts and returns EXIF metadata for image/video files (GPS coordinates, camera model, date taken).

### 5.2 `demo.py` — Realistic Workstation Demo Ingestion
- Accepts `DemoData`: `{ case_name, has_whatsapp: true, has_telegram: true, message_count: 100, contact_count: 15 }`.
- **DEMO_MODE Guard:** `if not settings.demo_mode: raise HTTPException(403)`.
- Generates complete dataset: `Case`, `Evidence`, `WhatsAppMessage`, `TelegramMessage`, `TimelineEvent` records (1 per message), and `DeletedMessage` records (2-3 realistic gaps).

### 5.3 `whatsapp.py` & `telegram.py` — Artifact Extraction APIs
- `POST /api/whatsapp/evidence/{id}/analyze/whatsapp`: Executes WhatsApp sqlite parser on extracted `.db` files.
- `POST /api/telegram/evidence/{id}/analyze/telegram`: Executes Telegram `cache4.db` parser.

### 5.4 `timeline.py` — Timeline Reconstruction API
- `POST /api/timeline/cases/{id}/timeline/build`: Triggers `TimelineBuilder` to aggregate and normalize all message and media events into `timeline_events`.
- `GET /api/timeline/cases/{id}/timeline`: Queries reconstructed timeline with filters (`start_date`, `end_date`, `app`, `query`).

### 5.5 `deleted.py` — Deleted Message Detection API
- `POST /api/deleted/cases/{id}/deleted/detect`: Triggers gap detection engine.
- `GET /api/deleted/cases/{id}/deleted`: Returns detected deletion records with gap range, confidence score, and explanation.

### 5.6 `correlation.py` — Evidence Correlation Engine API
- `POST /api/correlation/cases/{id}/correlation/build`: Runs cross-platform entity resolution and message time-window matching.
- `GET /api/correlation/cases/{id}/correlation`: Returns correlated entity nodes and edge lists.

### 5.7 `reports.py` — Forensic Court PDF Generator & Report Tracker API
- **Zero Workspace Disk Storage Rule:** PDF reports are generated in-memory (`io.BytesIO`) and streamed directly to the HTTP response (`StreamingResponse`) as an attachment download (`Content-Disposition: attachment; filename="..."`). PDF files MUST NOT be stored in `reports/` inside the project workspace directory.
- `POST /api/cases/{id}/reports`: Generates official court PDF into memory buffer, calculates SHA-256 hash of PDF bytes, logs entry in `generated_reports` table & `activity_logs` chain of custody, and returns `StreamingResponse`.
- `GET /api/cases/{id}/reports/history`: Returns historical log of generated reports for the case (Report ID, Type, Lead Analyst, Generation Date, Verification SHA-256 Hash of report bytes, Total Pages, Size Bytes).
- `GET /api/cases/{id}/reports/summary`: Returns summary metrics for report preview.

---

## 6. Service Layer Specifications — `backend/services/`

### 6.1 `whatsapp_service.py` & `telegram_service.py`
- Calls forensic parser modules in `forensic/`.
- Saves extracted messages, contacts, groups, and media to database.
- Records chain-of-custody entry in `activity_logs`.
- Stack trace error handling: uses `traceback.format_exc()` for all log calls.

### 6.2 `timeline_service.py`
- Invokes `TimelineBuilder.build_timeline_for_case()`.
- Generates `normalized_timestamp` datetime objects for timezone-aware chronological sorting.

### 6.3 `deleted_service.py`
- Invokes `DeletedDetector.detect_deletions()`.
- Handles sequence gap analysis for Telegram integer IDs.
- Performs timestamp gap analysis for WhatsApp.

### 6.4 `correlation_service.py`
- Converts ORM objects to matcher dataclasses.
- Discovers cross-platform entity links (phone number matching, handle matching).
- Generates `CorrelationEdge` records.

### 6.5 `report_service.py` — In-Memory Court PDF Generator Engine
Constructs formal legal PDF documents using ReportLab `SimpleDocTemplate` targetting an in-memory `io.BytesIO` buffer:
1. **In-Memory Generation:** Compiles PDF into `io.BytesIO()` memory buffer. Computes SHA-256 hash of output bytes.
2. **In-App Database Record:** Creates a `GeneratedReport` database record capturing `case_id`, `report_type`, `lead_analyst`, `created_at`, `size_bytes`, and `sha256_hash`.
3. **Cover Page:** Official header, seal, case reference, investigator details, report verification hash.
4. **Chain of Custody Manifest:** Table listing all evidence files, upload timestamps, SHA-256, MD5, SHA-1 hashes, and verification status.
5. **Executive Summary:** High-level case statistics and analyst notes.
6. **Artifact Analysis:** Detailed breakdown of extracted WhatsApp & Telegram messages, contacts, and media.
7. **Reconstructed Chronological Timeline:** Formatted timeline table.
8. **Deletion & Anomaly Log:** Gap analysis table with confidence ratings.
9. **Correlated Entities Matrix:** Cross-platform identity links.
10. **Legal Declaration & Sign-off Block:** Formal sworn statement of forensic integrity, signature line, analyst title, agency stamp, and document SHA-256 verification signature.

---

## 7. Forensic Engine — `forensic/`

### 7.1 `forensic/whatsapp/`
- `detector.py`: Detects legacy (`messages`, `wa_contacts`) and modern (`message`, `jid`, `chat`) WhatsApp database schemas.
- `message_parser.py`: Schema-adaptive SQL query builder. Parses text, timestamps, sender/receiver JIDs, media paths, and deleted message flags.
- `contact_parser.py`, `group_parser.py`, `media_parser.py`: Extracts contact book, group metadata, and media attachment references.

### 7.2 `forensic/telegram/`
- `detector.py`: Detects Telegram `cache4.db` database schemas (`messages`, `users`, `dialogs`, `chats`).
- `message_parser.py`: Parses Telegram message IDs, user IDs, text, dates, media references.
- `contact_parser.py`, `group_parser.py`: Parses Telegram user directory and group channels.

### 7.3 `forensic/deleted/detector.py`
- `_get_expected_next_id()`: Sequence gap detection for Telegram sequential integer IDs. Returns `None` for WhatsApp hex IDs.
- Calculates deletion confidence scores (0.0 to 1.0) based on gap size and time deltas.

### 7.4 `forensic/timeline/builder.py`
- `build_timeline_for_case()`: Merges WA messages, TG messages, EXIF media creation dates into normalized `TimelineEvent` records with ISO-8601 UTC timestamps.

### 7.5 `forensic/correlation/matcher.py`
- Matches contacts across platforms via normalized phone numbers (E.164 format) and handles.
- Matches cross-app messages exchanged within configurable time windows.

---

## 8. Repository Layer — `backend/repositories/`

- `dashboard_repo.py`: Aggregates case statistics, message volumes, app splits.
- `report_repo.py`: Fetches formatted data blocks for PDF report generation.
- `search_repo.py`: Multi-field full-text search across messages, contacts, files, and timeline. Fix: `_get_evidence_ids` filters by `metadata_["app"]` when app filter is specified.

---

## 9. Complete Bug Register

| ID | Severity | File | Description | Fix |
|----|----------|------|-------------|-----|
| B1 | HIGH | `main.py` L38 | CORS missing port 5174 | Add `"http://localhost:5174"` to `allow_origins` |
| B2 | HIGH | `demo.py` | Demo missing `TimelineEvent` and `DeletedMessage` records | Generate timeline events & deletion records in demo builder |
| B3 | HIGH | `demo.py` L21 | `has_telegram` defaults to `False` | Change default to `True` |
| B4 | MEDIUM | `demo.py` | Missing `DEMO_MODE` guard | Add `if not settings.demo_mode: raise HTTPException(403)` |
| B5 | MEDIUM | `whatsapp_service.py`, `telegram_service.py`, `timeline_service.py`, `deleted_service.py`, `correlation_service.py` | `str(e.__traceback__)` stringification | Replace with `import traceback; traceback.format_exc()` |
| B6 | MEDIUM | `search_repo.py` L444 | `_get_evidence_ids` ignores `app` filter | Filter by `Evidence.metadata_["app"].astext == app` |
| B7 | HIGH | `forensic/deleted/detector.py` L84 | WhatsApp hex ID gap detection produces invalid results | Return `None` for WhatsApp IDs; gap analysis valid for Telegram sequential integer IDs |
| B8 | LOW | `forensic/whatsapp/message_parser.py` | Silent `sqlite3.Error` swallows parsing failures | Add logger output before returning empty list |

---

## 10. Required Audit Tasks

| File | Verification Item |
|------|-------------------|
| `forensic/whatsapp/contact_parser.py` | Schema-adaptive query returning `WhatsAppContact` dicts |
| `forensic/whatsapp/group_parser.py` | Schema-adaptive query returning `WhatsAppGroup` dicts |
| `forensic/telegram/detector.py` | Correctly identifies Telegram `cache4.db` tables |
| `forensic/telegram/message_parser.py` | Parses Telegram messages and returns dicts matching `TelegramMessage` |
| `forensic/timeline/builder.py` | Returns `normalized_timestamp` as Python `datetime` object |
| `backend/services/log_service.py` | `log_analysis` with `evidence_id=None` does not violate FK constraint |

---

## 11. Run Commands

```powershell
# Must set PYTHONPATH so Python can find 'backend.*' and 'forensic.*' packages
$env:PYTHONPATH = "D:\ArtifactX"
$env:PATH = "C:\Users\Spandan\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts;$env:PATH"

cd D:\ArtifactX\backend
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

---

## 12. Data Flow: In-Memory Evidence PDF Generation to Download

```
User triggers "Export Court-Ready PDF Report":
  │
  ├──► POST /api/cases/{id}/reports (with ReportConfig)
  ├──► report_service.py -> ReportLab Engine compiles PDF into io.BytesIO() in-memory buffer
  ├──► Compute SHA-256 hash signature of generated PDF bytes
  ├──► Save metadata entry to DB `generated_reports` table & `activity_logs` Chain-of-Custody
  └──► FastAPI returns StreamingResponse(io.BytesIO, media_type="application/pdf")
  │
User Browser:
  ├──► Receives binary stream with header `Content-Disposition: attachment; filename="..."`
  └──► Browser triggers instant file download — zero PDF files written to project workspace directory
```
