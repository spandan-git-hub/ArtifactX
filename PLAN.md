# ArtifactX Implementation Plan

## 1. Context

ArtifactX is a forensic analysis platform that analyzes acquired evidence from WhatsApp databases, Telegram databases, media files, and ZIP evidence packages. It does not perform rooting or phone hacking — it only parses and analyzes uploaded evidence files.

Technology: React + JavaScript + Tailwind CSS (Frontend), FastAPI + Python (Backend), SQLite (Database).

## 2. Phase Overview

| Phase | Name | Purpose | Dependent On |
|---|---|---|---|
| 0 | Foundation | Project structure, dev environment, DB scaffold | None |
| 1 | Case Management | CRUD for cases | 0 |
| 2 | Evidence Management | Upload, store, hash, inventory | 1 |
| 3 | WhatsApp Analysis | Parse WhatsApp databases | 2 |
| 4 | Telegram Analysis | Parse Telegram databases | 2 |
| 5 | Timeline Reconstruction | Normalize and build timeline | 3, 4 |
| 6 | Deleted Message Detection | Detect deletions | 3, 4 |
| 7 | Media Analysis | EXIF, orphan detection | 2 |
| 8 | Evidence Correlation | Cross-link entities | 3, 4, 7 |
| 9 | Search & Filtering | Full-text + filters | 3, 4, 7 |
| 10 | Dashboard | Stats, graphs, timeline view | 5, 7, 8, 9 |
| 11 | Reporting | PDF generation | 5, 6, 9 |
| 12 | Logging & Audit | Structured logging | All |

## 3. Dependencies

```
Phase 0 --▶ Phase 1 --▶ Phase 2 --▶ Phase 3 (+ Phase 4)
  └─ DB configured    Case CRUD    Upload/Hash    DB parsers
                                │                      │
Phase 12 (Logging)   Phase 6 (Deleted)       Phase 7 (Media)
                                │                      │
Phase 5 (Timeline) ◀── Phase 3, 4              Phase 8 (Correlation)
  │                                                 │
Phase 11 (Reporting) ◀── Phase 5, 6, 9     Phase 9 (Search)
  │                                                 │
Phase 10 (Dashboard) ◀── Phase 5, 7, 8, 9
```

## 4. Module Breakdown

### Backend (`backend/`)

| Module | Purpose |
|--------|---------|
| `backend/app/` | FastAPI entry point, configuration, CORS, database init |
| `backend/api/` | FastAPI routers (cases, evidence, analysis, search, reports, logs) |
| `backend/models/` | SQLAlchemy ORM models (cases, evidence, messages, timeline, media, logs) |
| `backend/schemas/` | Pydantic request/response validation schemas |
| `backend/services/` | Business logic (case, evidence, analysis, report, search) |
| `backend/repositories/` | Data access layer over SQLAlchemy |
| `backend/utils/` | SHA-256 computation, file storage, logging config |

### Forensic Engine (`forensic/`)

| Module | Purpose |
|--------|---------|
| `forensic/whatsapp/` | WhatsApp DB detection, message/contact/group extraction |
| `forensic/telegram/` | Telegram DB detection, message/contact/group extraction |
| `forensic/timeline/` | Timestamp normalization, event collection and building |
| `forensic/deleted/` | Sequence gap detection, confidence scoring |
| `forensic/media/` | MIME detection, EXIF metadata, orphan media detection |
| `forensic/correlation/` | Cross-app contact matching, evidence graph building |

### Frontend (`frontend/`)

| Module | Purpose |
|--------|---------|
| `frontend/src/components/` | Reusable UI (cases, evidence, messages, timeline, dashboard, search, reports) |
| `frontend/src/pages/` | Page-level components (CaseList, CaseDetail, Dashboard, etc.) |
| `frontend/src/hooks/` | React hooks for data fetching |
| `frontend/src/services/` | API client functions |
| `frontend/src/context/` | Global state (active case) |

### Tests (`tests/`)

| Module | Purpose |
|--------|---------|
| `tests/api/` | API endpoint integration tests |
| `tests/forensic/` | Forensic parser unit tests |
| `tests/services/` | Service logic tests |
| `tests/fixtures/` | Sample databases, media, ZIP files |

## 5. Database Schema

```python
# Core Models
Case(id, name, description, investigator, status, created_at, updated_at)
Evidence(id, case_id, original_filename, storage_path, sha256, content_type,
         evidence_type, metadata, extracted_path, uploaded_at, analyzed_at)
EvidenceFile(id, evidence_id, relative_path, sha256, file_size, mime_type,
             metadata, is_media, media_type)
AnalysisResult(id, evidence_id, analysis_type, status, results,
               started_at, completed_at)

# WhatsApp
WhatsAppMessage(id, evidence_id, message_id, key_remote_jid, sender_jid,
                participant_jid, body, timestamp, media_type, media_path, message_type, status)
WhatsAppContact(id, evidence_id, jid, display_name, phone_number, status)
WhatsAppGroup(id, evidence_id, group_jid, subject, creator_jid, creation_timestamp)

# Telegram
TelegramMessage(id, evidence_id, message_id, dialog_id, sender_id, body,
                timestamp, media_type, media_path, message_type)
TelegramContact(id, evidence_id, user_id, first_name, last_name, username, phone)
TelegramGroup(id, evidence_id, group_id, title, username, type)

# Timeline & Analysis
TimelineEvent(id, case_id, evidence_id, event_type, source_app, timestamp,
              normalized_timestamp, entity_id, entity_type, description, metadata)
DeletedMessage(id, case_id, evidence_id, source_app, chat_jid, gap_start,
               gap_end, missing_count, confidence_score, detection_method, detected_at)
MediaItem(id, case_id, evidence_id, file_path, sha256, mime_type, media_type,
          file_size, width, height, duration, exif_data, is_orphan, linked_message_id)
CorrelationEdge(id, case_id, source_type, target_type, source_id, target_id,
                relation_type, metadata)

# Logging
AnalysisLog(id, evidence_id, log_type, message, details, timestamp)
ActivityLog(id, case_id, action, description, timestamp)
```

## 6. API Endpoints

### Cases
- `POST /api/cases` — Create case
- `GET /api/cases` — List cases
- `GET /api/cases/{id}` — Get case details
- `DELETE /api/cases/{id}` — Delete case (cascade)

### Evidence
- `POST /api/evidence` — Upload evidence (ZIP/file)
- `GET /api/evidence/{id}` — Get evidence metadata
- `DELETE /api/evidence/{id}` — Remove evidence
- `GET /api/evidence/{id}/files` — List extracted files
- `GET /api/evidence/{id}/files/{file_id}` — Download file

### WhatsApp Analysis
- `POST /api/evidence/{id}/analyze/whatsapp` — Run WhatsApp analysis
- `GET /api/evidence/{id}/wa-messages` — Extracted messages
- `GET /api/evidence/{id}/wa-contacts` — Extracted contacts
- `GET /api/evidence/{id}/wa-groups` — Extracted groups
- `GET /api/evidence/{id}/wa-media` — Media references

### Telegram Analysis
- `POST /api/evidence/{id}/analyze/telegram` — Run Telegram analysis
- `GET /api/evidence/{id}/tg-messages` — Extracted messages
- `GET /api/evidence/{id}/tg-contacts` — Extracted contacts
- `GET /api/evidence/{id}/tg-groups` — Extracted groups
- `GET /api/evidence/{id}/tg-media` — Media references

### Timeline
- `POST /api/cases/{id}/timeline/build` — Build timeline
- `GET /api/cases/{id}/timeline` — Get timeline events
- `POST /api/cases/{id}/timeline/filter` — Filter timeline

### Deleted Messages
- `POST /api/cases/{id}/deleted/detect` — Detect deletions
- `GET /api/cases/{id}/deleted` — Get deleted messages

### Search
- `GET /api/search` — Global search
- `GET /api/search/messages` — Search messages
- `GET /api/search/contacts` — Search contacts
- `GET /api/search/media` — Search media

### Dashboard
- `GET /api/cases/{id}/stats` — Case statistics
- `GET /api/cases/{id}/overview` — Overview data

### Reporting
- `POST /api/cases/{id}/reports` — Generate PDF report
- `GET /api/cases/{id}/reports` — List reports
- `GET /api/reports/{report_id}` — Download report
- `POST /api/cases/{id}/reports/summary` — Evidence summary
- `POST /api/cases/{id}/reports/timeline` — Timeline summary
- `POST /api/cases/{id}/reports/deleted` — Deleted message summary

### Logs
- `GET /api/logs/analysis` — Analysis logs
- `GET /api/logs/errors` — Error logs
- `GET /api/logs/activity` — Activity logs

## 7. Testing Strategy

### Backend Tests (pytest)

| Phase | Test File | Coverage |
|---|---|---|
| 0 | `test_database.py` | SQLAlchemy engine, all models insert/select |
| 1 | `test_api_cases.py` | Case CRUD, validation, cascade delete |
| 2 | `test_api_evidence.py` | Upload, ZIP extraction, SHA-256, inventory |
| 3 | `test_whatsapp_parser.py` | DB detection, message/contact/group extraction |
| 4 | `test_telegram_parser.py` | DB detection, message/contact/group extraction |
| 5 | `test_timeline.py` | Timestamp normalization, event ordering, filtering |
| 6 | `test_deleted_detection.py` | Gap detection, confidence scoring |
| 7 | `test_media_analysis.py` | MIME detection, EXIF, orphan flagging |
| 8 | `test_correlation.py` | Edge creation, graph, cross-app matching |
| 9 | `test_search.py` | Full-text, date range, app filter |
| 10 | `test_stats.py` | Aggregation counts |
| 11 | `test_pdf_generation.py` | Report generation, content validation |
| 12 | `test_logging.py` | Log entries, structured output |

### Frontend Tests (Vitest)

| Component | Coverage |
|---|---|
| `CaseListPage` | Loading, create, delete |
| `EvidenceUploader` | Drag-drop, progress, error |
| `TimelineViewer` | Event rendering, filtering |
| `SearchBar` | Input, debounce, results |
| `DashboardPage` | Stat cards, charts display |

### Test Fixtures

- `tests/fixtures/whatsapp/` — msgstore.db, wa.db
- `tests/fixtures/telegram/` — cache4.db, messages
- `tests/fixtures/media/` — JPEG, MP4, OGG samples
- `tests/fixtures/zip/` — Sample evidence packages

## 8. File/Folder Structure

```
ArtifactX/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   └── database.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── cases.py
│   │   ├── evidence.py
│   │   ├── whatsapp.py
│   │   ├── telegram.py
│   │   ├── timeline.py
│   │   ├── deleted.py
│   │   ├── search.py
│   │   ├── dashboard.py
│   │   ├── reports.py
│   │   └── logs.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── case.py
│   │   ├── evidence.py
│   │   ├── message.py
│   │   ├── timeline.py
│   │   ├── search.py
│   │   └── report.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── case_service.py
│   │   ├── evidence_service.py
│   │   ├── analysis_service.py
│   │   ├── report_service.py
│   │   └── search_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── case_repo.py
│   │   ├── evidence_repo.py
│   │   └── analysis_repo.py
│   └── utils/
│       ├── __init__.py
│       ├── hashing.py
│       ├── file_storage.py
│       └── logging_config.py
├── forensic/
│   ├── __init__.py
│   ├── base.py
│   ├── whatsapp/
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── message_parser.py
│   │   ├── contact_parser.py
│   │   └── group_parser.py
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── message_parser.py
│   │   ├── contact_parser.py
│   │   └── group_parser.py
│   ├── timeline/
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   └── normalizer.py
│   ├── deleted/
│   │   ├── __init__.py
│   │   ├── gap_detector.py
│   │   └── confidence.py
│   ├── media/
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── metadata.py
│   │   └── orphan.py
│   └── correlation/
│       ├── __init__.py
│       ├── graph.py
│       └── matcher.py
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── cases/
│   │   │   ├── evidence/
│   │   │   ├── messages/
│   │   │   ├── contacts/
│   │   │   ├── timeline/
│   │   │   ├── dashboard/
│   │   │   ├── search/
│   │   │   └── reports/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── context/
│   │   └── utils/
│   ├── public/
│   ├── tests/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── reports/
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── forensic/
│   ├── api/
│   └── services/
├── .env.example
├── .gitignore
└── README.md
```

## 9. Dependencies

### Backend

| Library | Version | Purpose |
|---|---|---|
| fastapi | ^0.110 | Web framework |
| uvicorn | ^0.30 | ASGI server |
| sqlalchemy | ^2.0 | ORM |
| pydantic | ^2.0 | Validation |
| pydantic-settings | ^2.0 | Configuration |
| python-multipart | ^0.0.9 | File upload handling |
| reportlab | ^4.0 | PDF generation |
| structlog | ^24.0 | Structured logging |
| Pillow | ^10.0 | Image metadata/EXIF |
| aiosqlite | ^0.20 | Async SQLite |
| pytest | ^8.0 | Test runner |
| pytest-cov | ^5.0 | Coverage reporting |

### Frontend

| Package | Version | Purpose |
|---|---|---|
| react | ^18.3 | UI framework |
| react-router-dom | ^6.24 | Routing |
| vite | ^5.3 | Build tool |
| tailwindcss | ^3.4 | Styling |
| axios | ^1.7 | HTTP client |
| @tanstack/react-query | ^5.0 | Data fetching |
| chart.js / react-chartjs-2 | ^4.4 | Dashboard charts |
| vis-network | ^latest | Evidence graph |
| date-fns | ^3.0 | Date formatting |
| vitest | ^1.6 | Unit testing |
| @testing-library/react | ^16.0 | Component testing |
| lucide-react | ^0.400 | Icons |

## 10. Verification

### Test Commands

```bash
# Backend
pytest tests/ -v
pytest --cov=backend --cov-report=html

# Frontend
npm test
npm test -- --coverage
```

### Acceptance Criteria

| Requirement | Acceptance Criteria |
|---|---|
| Case Management | Create, list, view, delete cases. Cascade delete. |
| Evidence Management | Upload ZIP/files, list contents, view metadata (SHA-256, MIME). |
| WhatsApp | Detect DB, extract messages, contacts, groups, media refs. |
| Telegram | Detect DB, extract messages, contacts, groups, media refs. |
| Timeline | Normalize to UTC, display ordered, filter by date/type. |
| Deleted Messages | Detect sequence gaps and missing records with confidence. |
| Media Analysis | Identify image/video/audio, extract metadata, flag orphan media. |
| Correlation | Link messages to contacts, messages to media, cross-app contacts. Graph. |
| Search | Full-text search on messages, contacts, media. Date + app filters. |
| Dashboard | Case stats, message counts, timeline mini-view, evidence graph. |
| Reporting | Generate PDF with evidence, timeline, and_detections. |
| Logging | All analysis, errors, and activity logged to SQLite. |

### Completion Criteria

- All TASKS.md items checked
- pytest suite passes for every backend feature
- Frontend loads without errors
- Evidence is read-only (never modified)
- No fabricated data in any output
