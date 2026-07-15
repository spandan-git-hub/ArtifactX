# ArtifactX Plan

> Consolidated project documentation. Last updated: 2026-06-26

---

## 1. Overview

ArtifactX is a forensic analysis platform that analyzes acquired evidence from:
- WhatsApp Databases
- Telegram Databases
- Media Files
- ZIP Evidence Packages

**Scope:** ArtifactX analyzes uploaded evidence files and generates forensic findings. It does NOT perform rooting, phone hacking, or device exploitation.

---

## 2. Technology Stack

### Frontend
- React
- JavaScript
- Tailwind CSS

### Backend
- FastAPI
- Python
- PostgreSQL (application database)
- SQLite (used only by forensic parsers to read evidence files)

### Database
- PostgreSQL

---

## 3. Requirements

### Case Management
- Create Case
- View Cases
- Case Details
- Delete Case

### Evidence Management
- Upload ZIP/File
- File Inventory
- Evidence Metadata
- SHA-256 Hashing

### WhatsApp Analysis
- Database Detection
- Message Extraction
- Contact Extraction
- Group Extraction
- Media Reference Extraction

### Telegram Analysis
- Database Detection
- Message Extraction
- Contact Extraction
- Group/Channel Extraction
- Media Reference Extraction

### Timeline Reconstruction
- Timestamp Normalization
- Event Collection
- Timeline Generation
- Timeline Filtering

### Deleted Message Detection
- Sequence Gap Detection
- Missing Record Detection
- Confidence Scoring

### Media Analysis
- Image Detection
- Video Detection
- Audio Detection
- Media Metadata Extraction
- Orphan Media Detection

### Evidence Correlation
- Message ↔ Contact Correlation
- Message ↔ Media Correlation
- Cross-App Correlation
- Evidence Graph Generation

### Search & Filtering
- Message Search
- Contact Search
- Media Search
- Date Filter
- App Filter

### Visualization Dashboard
- Case Overview
- Statistics Charts
- Timeline View
- Evidence Graph View

### Reporting
- PDF Report Generation
- Evidence Summary
- Timeline Summary
- Deleted Message Summary

### Logging & Audit
- Analysis Logs
- Error Logs
- Activity Logs

---

## 4. Phase Overview

| Phase | Name | Purpose | Status |
|-------|------|---------|--------|
| 0 | Foundation | Project structure, dev environment, DB scaffold | Complete |
| 1 | Case Management | CRUD for cases | Complete |
| 2 | Evidence Management | Upload, store, hash, inventory | Complete |
| 3 | WhatsApp Analysis | Parse WhatsApp databases | Complete |
| 4 | Telegram Analysis | Parse Telegram databases | Complete |
| 5 | Timeline Reconstruction | Normalize and build timeline | Complete |
| 6 | Deleted Message Detection | Detect deletions | Complete |
| 7 | Media Analysis | EXIF, orphan detection | Complete |
| 8 | Evidence Correlation | Cross-link entities | Complete |
| 9 | Search & Filtering | Full-text + filters | Complete |
| 10 | Dashboard | Stats, graphs, timeline view | Complete |
| 11 | Reporting | PDF generation | Complete |
| 12 | Logging & Audit | Structured logging | Complete |

---

## 5. Module Architecture

### Backend (`backend/`)

| Module | Purpose |
|--------|---------|
| `backend/app/` | FastAPI entry point, configuration, CORS, database init |
| `backend/api/` | FastAPI routers (cases, evidence, analysis, search, reports, logs) |
| `backend/models/` | SQLAlchemy ORM models |
| `backend/schemas/` | Pydantic request/response validation schemas |
| `backend/services/` | Business logic |
| `backend/repositories/` | Data access layer |
| `backend/utils/` | SHA-256 hashing, file storage, logging config |

### Forensic Engine (`forensic/`)

| Module | Purpose |
|--------|---------|
| `forensic/whatsapp/` | WhatsApp DB detection, message/contact/group extraction |
| `forensic/telegram/` | Telegram DB detection, message/contact/group extraction |
| `forensic/timeline/` | Timestamp normalization, event collection |
| `forensic/deleted/` | Sequence gap detection, confidence scoring |
| `forensic/media/` | MIME detection, EXIF metadata, orphan detection |
| `forensic/correlation/` | Cross-app contact matching, evidence graph |

### Frontend (`frontend/`)

| Module | Purpose |
|--------|---------|
| `frontend/src/components/` | Reusable UI components |
| `frontend/src/pages/` | Page-level components |
| `frontend/src/hooks/` | React hooks for data fetching |
| `frontend/src/services/` | API client functions |
| `frontend/src/context/` | Global state (active case) |

---

## 6. Database Schema

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

---

## 7. API Endpoints

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

---

## 8. File Structure

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
│   │   ├── index.css
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── context/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── reports/
├── .env.example
├── .gitignore
└── README.md
```

---

## 9. Dependencies

### Backend

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.110 | Web framework |
| uvicorn | ^0.30 | ASGI server |
| sqlalchemy | ^2.0 | ORM |
| psycopg2-binary | ^2.9 | PostgreSQL adapter |
| pydantic | ^2.0 | Validation |
| pydantic-settings | ^2.0 | Configuration |
| python-multipart | ^0.0.9 | File upload |
| reportlab | ^4.0 | PDF generation |
| structlog | ^24.0 | Structured logging |
| Pillow | ^10.0 | Image EXIF |
| sqlite3 | (stdlib) | Reads evidence files (WhatsApp/Telegram databases) |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.3 | UI framework |
| react-router-dom | ^6.24 | Routing |
| vite | ^5.3 | Build tool |
| tailwindcss | ^3.4 | Styling |
| axios | ^1.7 | HTTP client |
| @tanstack/react-query | ^5.0 | Data fetching |
| chart.js / react-chartjs-2 | ^4.4 | Charts |
| vis-network | latest | Evidence graph |
| date-fns | ^3.0 | Date formatting |
| lucide-react | ^0.400 | Icons |

---

## 10. Completion Status

All 12 phases are complete. Every requirement has been implemented.

### Phase 13: Refinements & Demo Mode (2026-07-15)

- [x] Fixed `DeletedMessage` import error in `deleted_service.py`
- [x] Populated `forensic/__init__.py` with proper exports
- [x] Added demo mode API endpoints (`backend/api/demo.py`)
- [x] Added demo mode frontend service and UI
- [x] Fixed frontend null checks in DashboardPage
- [x] Fixed date formatting safety in CaseListPage
- [x] Added common UI components (ErrorBoundary, LoadingSpinner, EmptyState)
- [x] Updated health endpoint with version and demo_mode status
- [x] Added PostgreSQL migration guidelines to REFINEMENT.md
- [x] Created database setup scripts for PostgreSQL

**Last updated:** 2026-07-15