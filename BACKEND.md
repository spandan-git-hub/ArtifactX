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
| AI / Sentiment Engine | Rule-based & NLP keyword sentiment engine ✅ | Rule-based & NLP keyword sentiment engine |
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
| `generated_reports` | **In-App Report History Tracker**: tracks generated report ID, case ID, report type, analyst, timestamp, size bytes, and SHA-256 verification hash | ✅ Correct |
| `analysis_logs` | Deep diagnostic logs during evidence parsing runs | ✅ Correct |
| `activity_logs` | **Chain-of-Custody Audit Log** (ingest, hash verify, parse, report export events) | ✅ Correct |
| `error_logs` | System exception logs and stack traces | ✅ Correct |

---

## 5. API Layer Specifications — `backend/api/`

### 5.1 `evidence.py` — Ingestion & Cryptographic Integrity
- Multipart Upload with SHA-256, MD5, and SHA-1 calculation.
- `POST /api/evidence/{id}/verify-hashes`: On-disk hash verification.
- `GET /api/evidence/{id}/exif`: EXIF metadata extraction.

### 5.2 `demo.py` — Realistic Workstation Demo Ingestion
- Generates complete demo case with messages, timeline events, and deletion gap records.

### 5.3 `whatsapp.py` & `telegram.py` — Artifact Extraction APIs
- WhatsApp `msgstore.db` and Telegram `cache4.db` sqlite parsers.

### 5.4 `timeline.py` — Timeline Reconstruction API
- Multiapp timeline reconstruction and density queries.

### 5.5 `deleted.py` — Deleted Message Detection API
- Sequence and timestamp gap detection.

### 5.6 `correlation.py` — Evidence Correlation Engine API
- Cross-platform entity resolution and time-window correlation matching.

### 5.7 `assistant.py` (NEW) — Investigative AI Copilot & Chat Sentiment API
- **`POST /api/cases/{id}/assistant/query`:** Accepts natural language investigator questions (e.g. *"Find threat keywords in suspect chats"*). Searches case messages, executes sentiment classification, and returns AI copilot analysis and relevant message citations.
- **`POST /api/cases/{id}/assistant/sentiment`:** Analyzes suspect chat threads or selected messages for sentiment classification (Aggressive, Suspicious, Deceptive, Urgent, Evasive, Neutral), intention markers (financial demand, coercion, deletion awareness), and calculates suspicion confidence scores (0% to 100%).
- **LEGAL COURT REPORT ISOLATION:** Copilot query results and sentiment scores are kept transient or in-memory for investigator UI display only — **they are strictly excluded from the PDF report generation engine**.

### 5.8 `reports.py` — Forensic Court PDF Generator & Report Tracker API
- **Zero Workspace Disk Storage:** PDF reports generated in-memory (`io.BytesIO`) and returned via `StreamingResponse`.
- **Strict Legal Exclusion:** Excludes all AI assistant responses and sentiment metrics to maintain judicial admissibility.

---

## 6. Service Layer Specifications — `backend/services/`

### 6.1 `assistant_service.py` (NEW) — Investigative AI & Sentiment Service
- Performs keyword-based NLP sentiment scoring, emotional tone detection, and suspicion score calculation on extracted WhatsApp and Telegram message text.
- Generates natural language summaries and highlights intent markers (e.g. monetary transactions, threat language, evasive behavior).
- Computes suspicion confidence ratings based on message frequency, sentiment intensity, and deletion gap proximity.

### 6.2 `report_service.py` — In-Memory Court PDF Generator Engine
- Compiles official court PDF report into `io.BytesIO()` memory buffer.
- Strictly parses deterministic evidence tables (`wa_messages`, `tg_messages`, `evidence_files`, `timeline_events`, `deleted_messages`, `correlation_edges`). **Excludes AI copilot output and sentiment scores**.

---

## 7. Forensic Engine — `forensic/`

### 7.1 `forensic/whatsapp/` & `forensic/telegram/`
- Schema-adaptive database parsers for WhatsApp and Telegram.

### 7.2 `forensic/deleted/detector.py`
- Sequence & timestamp gap detection for deleted messages.

### 7.3 `forensic/timeline/builder.py`
- Chronological event builder with UTC timestamp normalization.

### 7.4 `forensic/correlation/matcher.py`
- Entity resolution and cross-platform message matcher.

---

## 8. Repository Layer — `backend/repositories/`

- `dashboard_repo.py`, `report_repo.py`, `search_repo.py`.

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

---

## 10. Required Audit Tasks

| File | Verification Item |
|------|-------------------|
| `backend/api/assistant.py` | Endpoints `/query` and `/sentiment` exist and process case messages |
| `backend/services/assistant_service.py` | Performs sentiment classification (Aggressive, Suspicious, Deceptive, Urgent) and suspicion scoring |
| `backend/services/report_service.py` | Verifies that AI copilot data is strictly excluded from ReportLab PDF rendering |

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

## 12. Data Flow: Investigative AI Assistant vs. Court PDF Pipeline

```
Investigator Workflow:
  │
  ├──► Uses AI Assistant Drawer (ForensicAssistantDrawer.jsx)
  ├──► Sends Query / Triggers Chat Sentiment Analysis
  ├──► assistant_service.py computes sentiment tones, intent markers, suspicion confidence
  └──► UI displays copilot insights with badge: "Internal Investigative Aid Only — Excluded from Court Reports"

Court Report Export Pipeline:
  │
  ├──► POST /api/cases/{id}/reports
  ├──► report_service.py pulls ONLY deterministic evidence tables (Messages, EXIF, Hashes, Timeline, Deletions)
  ├──► Strictly EXCLUDES AI copilot chat responses & sentiment ratings
  └──► Streams signed, legally admissible court PDF to browser download
```
