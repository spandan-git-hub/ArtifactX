# ArtifactX — Everything About The Project: Comprehensive Specification, Current State & Future Forensic Roadmap

> **Authoritative Project Compendium & Strategic Roadmap**  
> **Repository:** `ArtifactX`  
> **Target Audience:** Human Developers, Forensic Investigators, Systems Architects, and AI Agents  
> **Document Structure:**
> - **Part I: Current As-Built Implementation (Phases 0–15)** — Exhaustive documentation of the working code, database models, 15 API routers, frontend workstation, court PDF engine, and test records.
> - **Part II: Strategic Reorientation, Missing Gaps & Future Roadmap** — Crucial architectural realizations, planned excision of AI sentiment, evolution to physical deleted message carving, deep cross-platform correlation, and the comprehensive forensic analysis framework.

---

# Table of Contents

### PART I: CURRENT AS-BUILT IMPLEMENTATION
1. [Executive Summary & Original Design Intentions](#1-executive-summary--original-design-intentions)
2. [Core Forensic Principles & Legal Constraints](#2-core-forensic-principles--legal-constraints)
3. [System Architecture & Data Flow](#3-system-architecture--data-flow)
4. [Technology Stack](#4-technology-stack)
5. [Database Schema & Entity Relationship Model (17 Tables)](#5-database-schema--entity-relationship-model-17-tables)
6. [Forensic Parsing & Extraction Engine (`forensic/`)](#6-forensic-parsing--extraction-engine-forensic)
   - 6.1 [WhatsApp Extractor (`forensic/whatsapp/`)](#61-whatsapp-extractor-forensicwhatsapp)
   - 6.2 [Telegram Extractor (`forensic/telegram/`)](#62-telegram-extractor-forensictelegram)
   - 6.3 [Deletion Gap Anomaly Detector (`forensic/deleted/`)](#63-deletion-gap-anomaly-detector-forensicdeleted)
   - 6.4 [Chronological Timeline Engine (`forensic/timeline/`)](#64-chronological-timeline-engine-forensictimeline)
   - 6.5 [Cross-Platform Correlation Prototype (`forensic/correlation/`)](#65-cross-platform-correlation-prototype-forensiccorrelation)
   - 6.6 [Media & EXIF Metadata Inspector (`forensic/media/`)](#66-media--exif-metadata-inspector-forensicmedia)
7. [Backend Architecture & Complete REST API Reference (15 Routers)](#7-backend-architecture--complete-rest-api-reference-15-routers)
   - 7.1 [App Configuration & Database Session Management](#71-app-configuration--database-session-management)
   - 7.2 [Service Layer Deep-Dive](#72-service-layer-deep-dive)
   - 7.3 [Complete REST API Reference (All Endpoints)](#73-complete-rest-api-reference-all-endpoints)
8. [Frontend Forensic Workstation (`frontend/`)](#8-frontend-forensic-workstation-frontend)
   - 8.1 [Visual Identity & Design System](#81-visual-identity--design-system)
   - 8.2 [Navigation & 4-Stage Forensic Workflow](#82-navigation--4-stage-forensic-workflow)
   - 8.3 [Page-by-Page Specifications (All 11 Pages)](#83-page-by-page-specifications-all-11-pages)
   - 8.4 [Specialized Interactive Components & Drawers](#84-specialized-interactive-components--drawers)
   - 8.5 [Custom Hooks & Frontend Services](#85-custom-hooks--frontend-services)
9. [Court-Ready PDF Generation & In-App Report Tracker](#9-court-ready-pdf-generation--in-app-report-tracker)
   - 9.1 [In-Memory Streaming Pipeline (Zero Workspace Storage)](#91-in-memory-streaming-pipeline-zero-workspace-storage)
   - 9.2 [Judicial Report Structure & Standards](#92-judicial-report-structure--standards)
   - 9.3 [In-App Report History Tracker (`generated_reports`)](#93-in-app-report-history-tracker-generated_reports)
10. [AI Forensic Assistant & Chat Sentiment Analyzer (Phase 15 As-Built)](#10-ai-forensic-assistant--chat-sentiment-analyzer-phase-15-as-built)
11. [Complete Project Repository Map](#11-complete-project-repository-map)
12. [Current Implementation Tracker (Phases 0–15 Status)](#12-current-implementation-tracker-phases-015-status)
13. [Installation, Configuration & Execution Guide](#13-installation-configuration--execution-guide)
14. [Testing & Verification Records](#14-testing--verification-records)
15. [Credits, Academic Integrity & License](#15-credits-academic-integrity--license)

### PART II: STRATEGIC REORIENTATION, MISSING GAPS & FUTURE ROADMAP
16. [Strategic Critical Realization: What The Developer Must Know](#16-strategic-critical-realization-what-the-developer-must-know)
17. [Planned Excision: Decommissioning AI Sentiment & Copilot](#17-planned-excision-decommissioning-ai-sentiment--copilot)
18. [Future Flagship Pillar 1: True Deleted Message Recovery Engine (Physical Carving)](#18-future-flagship-pillar-1-true-deleted-message-recovery-engine-physical-carving)
19. [Future Flagship Pillar 2: Deep Cross-Platform Correlation Engine](#19-future-flagship-pillar-2-deep-cross-platform-correlation-engine)
20. [Filling The Void: Comprehensive Digital Forensics Analysis Framework](#20-filling-the-void-comprehensive-digital-forensics-analysis-framework)
21. [Strategic Engineering Roadmap (Phases R1–R4)](#21-strategic-engineering-roadmap-phases-r1r4)

---

# PART I: CURRENT AS-BUILT IMPLEMENTATION

---

## 1. Executive Summary & Original Design Intentions

**ArtifactX** is an end-to-end digital forensic analysis workstation and court reporting platform engineered for law enforcement agencies, cybercrime investigators, legal counsel, and judicial examiners.

Mobile devices present an overwhelming volume of fragmented data spread across proprietary messaging platforms (WhatsApp, Telegram), nested file structures, media caches, and deleted records. ArtifactX was conceived to bridge this gap: ingesting mobile filesystem extractions and database backups, extracting evidentiary artifacts, cross-correlating identities and messages, detecting deleted message sequence gaps, and compiling sworn, court-admissible PDF forensic reports.

### The Foundational Intentions of the Current System

The current system was architected under a deliberate set of forensic design intentions and engineering principles across Phases 0 through 15:

1. **The 4-Stage Forensic Workflow Intention:**  
   The workstation UI was intentionally structured around the standard legal lifecycle of digital evidence:
   - **Stage 1 (Ingestion & Hashing):** Intake of evidence packages with automatic SHA-256, MD5, and SHA-1 calculation, file inventorying, and chain-of-custody logging.
   - **Stage 2 (Parsing & Extraction):** Automated execution of schema-adaptive SQLite parsers for WhatsApp and Telegram, media extraction, and EXIF decoding.
   - **Stage 3 (Deep Analysis & Inspection):** Multi-app chronological timeline reconstruction, sequence gap deletion detection, cross-platform message correlation, and high-density chat thread viewing.
   - **Stage 4 (Verification & Court Export):** Re-hashing of on-disk evidence files to prove zero evidence tampering, compilation of sworn court-ready PDF reports, and in-app report history tracking.

2. **The Zero-Workspace Storage Intention:**  
   To prevent evidence spillage, cross-case contamination, and unauthenticated disk leakage, court PDF reports were intentionally designed to **never be written to the server's workspace disk**. Reports are generated dynamically in-memory (`io.BytesIO`) and streamed directly to the browser via HTTP `StreamingResponse`, with SHA-256 verification digests permanently recorded in the database.

3. **The Forensic Workstation UX Intention (Eliminating Redundancies):**  
   The UI was intentionally designed as a high-density, clinical forensic tool (`ForensicStudio`), not a generic SaaS app:
   - **No Redundant Navigation:** Header buttons replicating sidebar links were eliminated; navigation is context-aware (dynamically revealing active case tools only when inside a case).
   - **No Broken or Dummy Links:** All buttons point to valid routes or trigger modals; placeholder buttons and dummy query params (`?tab=timeline`) were eradicated.
   - **Data-Forward Density:** Interactive chat viewers, timeline density histograms, and SQLite hex/table inspectors are prioritized over decorative cards.

4. **The Evidence Integrity & Auditability Intention:**  
   Every ingested container and extracted file is stamped with cryptographic hashes upon arrival. The system maintains an immutable `activity_logs` ledger tracking who ingested evidence, who verified hashes, which parsers were run, and when reports were compiled.

5. **The Decoupled Forensic Engine Intention:**  
   The evidence extraction and parsing logic was intentionally segregated into a standalone `forensic/` package, completely decoupled from FastAPI and SQLAlchemy, ensuring that parsers operate in read-only mode and can be executed independently in CLI or batch scripts.

6. **The Realistic Demo Casework Intention:**  
   To enable rapid demonstration, forensic training, and automated verification without requiring live suspect mobile dumps, the platform incorporates a full-fidelity demo engine (`DemoModal.jsx` and `/api/demo`) capable of generating synthetic multi-app cases with realistic message sequences, contacts, timeline events, and deletion gaps tagged with `demo_mode=True`.

7. **The Legal Isolation Intention for AI (Phase 15):**  
   When the experimental AI Assistant and Sentiment Analyzer were added in Phase 15, they were intentionally bound by a strict legal firewall: AI insights are treated strictly as internal investigative aids and are **hard-coded to be excluded from official court PDF reports** to ensure judicial admissibility.

---

## 2. Core Forensic Principles & Legal Constraints

ArtifactX is governed by strict digital forensics and judicial rules:

1. **Forensic Soundness & ISO/IEC 27037 Compliance:**
   - Raw evidence files are treated as immutable read-only records.
   - Extracted SQLite databases are queried with read-only connection strings (`file:...?...&mode=ro` or direct read cursors).
   - Every ingested evidence container and individual extracted file is stamped with SHA-256, MD5, and SHA-1 cryptographic fingerprints.
2. **Zero Synthetic Artifacts:**
   - The application never invents or simulates forensic findings in live mode.
   - Demo mode data is rigorously isolated and tagged with `demo_mode=True`.
3. **Zero Workspace Storage for Reports:**
   - In accordance with production security standards, compiled PDF court reports **must never accumulate on workspace disks**.
   - All PDF reports are compiled in an in-memory buffer (`io.BytesIO`) and streamed directly to the browser via HTTP `StreamingResponse`. Report metadata and cryptographic output hashes are logged in the `generated_reports` table.
4. **The Legal Boundary: Strict AI Assistant Isolation:**
   - While AI-driven natural language queries and sentiment scores assist the human investigator during triage, modern judicial courts reject non-deterministic or subjective AI inferences.
   - Therefore, **AI Copilot outputs, sentiment tones, and suspicion scores are strictly excluded from generated court-ready PDF reports**. Court reports present only verifiable, deterministic facts.

---

## 3. System Architecture & Data Flow

```mermaid
flowchart TB
    subgraph Client["🖥️ FORENSIC WORKSTATION (React 18 + Vite)"]
        direction TB
        UI["Workstation Views\nCase Workspace · Evidence Inventory · Chat Thread Viewer\nTimeline Histogram · Entity Correlation · Deletions · Reports"]
        Components["Forensic Components\nWorkflowStepper · HashBadge · ExifDrawer · SqliteInspector\nReportPdfPreview · MessageCharts"]
        Hooks["Custom Hooks\nuseCases · useDashboard · useEvidence · useChat\nuseTimeline · useCorrelation · useReports · useLogs"]
        UI --> Components
        Components --> Hooks
    end

    subgraph API["⚙️ BACKEND API GATEWAY (FastAPI + Python 3.13)"]
        direction TB
        MW["Middleware\nCORS (5173/5174) · ErrorLoggingMiddleware (structlog)"]
        Routers["REST Routers (15 Routers)\n/cases · /chats · /evidence · /whatsapp · /telegram\n/timeline · /deleted · /correlation · /search · /dashboard · /reports · /logs · /demo · /assistant"]
        Services["Domain Services\nEvidenceService · ChatService · TimelineService\nCorrelationService · DeletedService · ReportService · LogService · AssistantService"]
        MW --> Routers --> Services
    end

    subgraph ForensicEngine["🔬 FORENSIC ENGINE (Pure Python, Independent Package)"]
        direction TB
        Parsers["Parsers\nWhatsApp (msgstore/wa) · Telegram (cache4)"]
        Detectors["Detectors\nDeletion Gap Detector · Media Metadata (EXIF/GPS)\nOrphan Media Detector"]
        Engines["Engines\nTimeline Normalizer & Builder · Entity Matcher & Graph"]
        Parsers --> Detectors --> Engines
    end

    subgraph Persistence["🗄️ PERSISTENCE & CLOUD STORAGE"]
        direction TB
        PG[("Neon Serverless Cloud PostgreSQL\n17 Relational Tables\nNullPool + SSL Require")]
        RawDisk[("Uploads Directory\nuploads/\nRaw Archives & SQLite DBs")]
        StreamBuf[("In-Memory Buffer\nio.BytesIO\nZero Workspace PDF Engine")]
    end

    Hooks -- "Axios HTTP (Port 8080)" --> MW
    Services --> ForensicEngine
    Services --> PG
    Services -- "Read Evidence" --> RawDisk
    Services -- "Stream PDF" --> StreamBuf
    StreamBuf -- "Direct Binary Stream" --> UI
```

---

## 4. Technology Stack

### Frontend Architecture
| Component | Technology | Version | Forensic Purpose |
|---|---|---|---|
| **Framework** | React | 18.3.0 | High-density workstation state & component tree |
| **Build System** | Vite | 5.3.0 | Module bundling, hot reloading, production rollup |
| **Styling** | Tailwind CSS | 3.4.0 | Clinical dark forensic palette (`forensic-950`) |
| **Navigation** | React Router DOM | 6.24.0 | Sub-route context-aware workstation routing |
| **HTTP Client** | Axios | 1.7.0 | REST API client with Blob streaming support |
| **Data Viz** | Chart.js + react-chartjs-2 | 4.5.1 / 5.3.1 | Timeline histograms, volume curves, app split |
| **Typography** | Inter & JetBrains Mono | Google Fonts | High readability UI & cryptographic monospace displays |

### Backend Architecture
| Component | Technology | Version | Forensic Purpose |
|---|---|---|---|
| **API Framework**| FastAPI | 0.115.8 | High-performance asynchronous REST API |
| **Runtime** | Python | 3.13 | Core processing environment |
| **ORM** | SQLAlchemy | 2.0.38 | Declarative data modeling, session management |
| **Database** | PostgreSQL (Neon Cloud) | Serverless | 17 relational tables with `NullPool` & SSL |
| **Validation** | Pydantic v2 | 2.10.6 | Strict input/output schema validation |
| **PDF Engine** | ReportLab Platypus | 4.3.1 | In-memory flowable court PDF generation |
| **Metadata** | Pillow + ExifRead | 11.1.0 | EXIF tags, camera hardware, decimal GPS |
| **Cryptography**| hashlib | Standard Lib | SHA-256, MD5, SHA-1 message digests |

---

## 5. Database Schema & Entity Relationship Model (17 Tables)

The relational schema in PostgreSQL consists of 17 tables structured for integrity, auditability, and forensic traceability:

```mermaid
erDiagram
    cases ||--o{ evidence : contains
    cases ||--o{ timeline_events : aggregates
    cases ||--o{ deleted_messages : identifies
    cases ||--o{ media_items : catalogs
    cases ||--o{ correlation_edges : links
    cases ||--o{ activity_logs : tracks
    cases ||--o{ generated_reports : records

    evidence ||--o{ evidence_files : unpacks
    evidence ||--o{ analysis_results : generates
    evidence ||--o{ wa_messages : extracts
    evidence ||--o{ wa_contacts : extracts
    evidence ||--o{ wa_groups : extracts
    evidence ||--o{ tg_messages : extracts
    evidence ||--o{ tg_contacts : extracts
    evidence ||--o{ tg_groups : extracts
    evidence ||--o{ analysis_logs : logs
```

### Complete Database Table Catalog

| # | Table Name | Key Columns | Forensic Description |
|---|---|---|---|
| 1 | `cases` | `id`, `name`, `description`, `investigator`, `status`, `created_at`, `updated_at` | Primary case registry record. Tracks legal reference and lead investigator. |
| 2 | `evidence` | `id`, `case_id`, `original_filename`, `storage_path`, `sha256`, `content_type`, `evidence_type`, `metadata_`, `extracted_path`, `uploaded_at` | Ingested evidence container (ZIP archive or direct database). Records primary intake hash. |
| 3 | `evidence_files` | `id`, `evidence_id`, `relative_path`, `sha256`, `file_size`, `mime_type`, `is_media`, `media_type`, `metadata_` | Per-file manifest of unpacked files. Tracks relative path, file size, MIME, and cryptographic SHA-256. |
| 4 | `analysis_results` | `id`, `evidence_id`, `analysis_type`, `status`, `results`, `started_at`, `completed_at` | Execution status and JSON metadata of forensic parser runs. |
| 5 | `wa_messages` | `id`, `evidence_id`, `message_id`, `key_remote_jid`, `sender_jid`, `participant_jid`, `body`, `timestamp`, `media_type`, `media_path`, `message_type`, `status` | Extracted WhatsApp messages with remote JID, timestamp in epoch ms, and media references. |
| 6 | `wa_contacts` | `id`, `evidence_id`, `jid`, `display_name`, `phone_number`, `status` | WhatsApp address book contacts extracted from `wa.db` or `msgstore.db`. |
| 7 | `wa_groups` | `id`, `evidence_id`, `group_jid`, `subject`, `creator_jid`, `creation_timestamp` | WhatsApp group chat metadata and creator identity. |
| 8 | `tg_messages` | `id`, `evidence_id`, `message_id`, `dialog_id`, `sender_id`, `body`, `timestamp`, `media_type`, `media_path`, `message_type` | Extracted Telegram messages with dialog identifier, sender ID, and timestamp in epoch seconds. |
| 9 | `tg_contacts` | `id`, `evidence_id`, `user_id`, `first_name`, `last_name`, `username`, `phone` | Extracted Telegram user profiles, usernames, and associated phone numbers. |
| 10 | `tg_groups` | `id`, `evidence_id`, `group_id`, `title`, `username`, `type` | Extracted Telegram channels and discussion groups. |
| 11 | `timeline_events` | `id`, `case_id`, `evidence_id`, `event_type`, `source_app`, `timestamp`, `normalized_timestamp`, `entity_id`, `entity_type`, `description`, `metadata_` | Normalized multi-app chronological event stream. Metadata includes computed 64-char event fingerprint. |
| 12 | `deleted_messages` | `id`, `case_id`, `evidence_id`, `source_app`, `chat_jid`, `gap_start`, `gap_end`, `missing_count`, `confidence_score`, `detection_method`, `detected_at` | Sequence and timestamp gaps representing purged or deleted messages with confidence rating. |
| 13 | `media_items` | `id`, `case_id`, `evidence_id`, `file_path`, `sha256`, `mime_type`, `media_type`, `file_size`, `width`, `height`, `duration`, `exif_data`, `is_orphan`, `linked_message_id` | Media attachments and files with parsed EXIF metadata (camera, GPS lat/long, capture timestamp). |
| 14 | `correlation_edges`| `id`, `case_id`, `source_type`, `target_type`, `source_id`, `target_id`, `relation_type`, `metadata_` | Entity resolution links (WhatsApp JID <-> Telegram phone) and cross-app message correlation nodes. |
| 15 | `generated_reports`| `id`, `report_id`, `case_id`, `report_type`, `lead_analyst`, `agency`, `case_notes`, `sha256`, `total_pages`, `size_bytes`, `filename`, `generated_at` | In-App Report History Tracker: Manifest of all court-ready reports generated with output SHA-256 hashes. |
| 16 | `activity_logs` | `id`, `case_id`, `action`, `description`, `timestamp` | Chain-of-Custody Audit Log: Immutable ledger recording every ingest, verify, parse, and export event. |
| 17 | `error_logs` | `id`, `case_id`, `evidence_id`, `error_type`, `message`, `stack_trace`, `endpoint`, `method`, `client_ip`, `user_agent`, `timestamp` | Detailed system exception records with full stack traces for forensic diagnostics. |

---

## 6. Forensic Parsing & Extraction Engine (`forensic/`)

### 6.1 WhatsApp Extractor (`forensic/whatsapp/`)
- **`detector.py`:** Inspects SQLite master schemas to confirm whether a database is a valid WhatsApp container by checking for tables such as `messages`, `chat`, `jid`, or `wa_contacts`.
- **`message_parser.py`:** Extracts message text, media paths, status codes, and remote JIDs. Normalizes 13-digit millisecond timestamps. Handles schema variations across WhatsApp versions (v11+ `message` table vs legacy `messages` table).
- **`contact_parser.py`:** Extracts contact records, JID addresses, display names, and phone numbers.
- **`group_parser.py`:** Resolves group chats, participant rosters, and group subjects.
- **`media_parser.py`:** Extracts thumbnail records, media dimensions, and file paths.

### 6.2 Telegram Extractor (`forensic/telegram/`)
- **`detector.py`:** Validates Telegram Android `cache4.db` by detecting tables such as `messages`, `users`, `chats`, and `dialogs`.
- **`message_parser.py`:** Extracts message sequences, sender IDs, dialog references, and text. Normalizes 10-digit epoch second timestamps.
- **`contact_parser.py`:** Extracts user profiles, usernames (e.g. `@suspect`), first/last names, and registered phone numbers.
- **`group_parser.py`:** Decodes channel IDs, supergroup titles, and discussion threads.
- **`media_parser.py`:** Identifies Telegram cached documents, voice notes, and photo references.

### 6.3 Deletion Gap Anomaly Detector (`forensic/deleted/`)
- **`detector.py` (`DeletedDetector`):**
  - Analyzes numeric primary key sequence gaps (e.g., message ID jumping from 104 to 109 indicates missing messages 105–108).
  - Calculates confidence scores based on gap width, adjacent message frequency, and timestamp deltas:
    $$\text{Confidence} = f(\text{missing\_count}, \Delta t)$$
  - Tags identified gaps with `detection_method="sequence_gap_analysis"` and records missing counts and boundary IDs.

### 6.4 Chronological Timeline Engine (`forensic/timeline/`)
- **`normalizer.py`:** Converts disparate timestamp representations (millisecond epoch, second epoch, ISO strings) into standardized UTC `datetime` objects.
- **`builder.py` (`TimelineBuilder`):**
  - Aggregates evidence ingestion events, WhatsApp messages, Telegram messages, and deletion anomalies.
  - Computes a deterministic 64-character SHA-256 fingerprint for every event:
    $$\text{hash\_fingerprint} = \text{SHA-256}(\text{app} + \text{entity\_id} + \text{timestamp} + \text{content})$$
  - Generates time-density histograms bucketed by hour or day for visualization.

### 6.5 Cross-Platform Correlation Prototype (`forensic/correlation/`)
- **`matcher.py`:**
  - **Phone Number Normalization:** Uses regex to strip formatting, country code delimiters, and spaces, standardizing numbers to E.164.
  - **Identity Resolution:** Matches WhatsApp contacts to Telegram contacts when phone numbers or normalized handles align.
  - **Cross-App Message Time-Window Matrix:** Identifies coordinated multi-platform conversations where suspect exchanges messages across WhatsApp and Telegram within configurable time intervals (e.g., within 15 minutes).
- **`graph.py`:** Converts identified correlation edges into node-link graph data structures suitable for visual rendering.

### 6.6 Media & EXIF Metadata Inspector (`forensic/media/`)
- **`metadata.py`:** Parses image binary headers using Pillow and ExifRead to extract:
  - Camera Manufacturer & Model (e.g., Apple iPhone 15 Pro, Samsung Galaxy S24)
  - ISO speed ratings, exposure time, focal length, aperture
  - Date/time digitized
  - GPS latitude, longitude, and altitude (converted from degrees/minutes/seconds to decimal coordinates)
- **`orphan.py`:** Scans physical storage directories to detect orphan media files that exist on disk but lack corresponding message records in the database.

---

## 7. Backend Architecture & Complete REST API Reference (15 Routers)

### 7.1 App Configuration & Database Session Management
- **`backend/app/config.py`:** Reads environment variables using `pydantic-settings`. Configures database connection string, maximum upload size (1GB default), and demo mode flags.
- **`backend/app/database.py`:** Manages SQLAlchemy session creation. Utilizes `NullPool` and explicit SSL configuration (`sslmode=require`) to support serverless PostgreSQL instances (Neon cloud) without stale connection errors.
- **`backend/middleware/error_logging.py`:** Global middleware intercepting unhandled exceptions, formatting stack traces, and logging them to `error_logs`.

### 7.2 Service Layer Deep-Dive
- **`evidence_service.py`:** Coordinates multi-hash digest computation, file extraction from ZIP archives, and filesystem cataloging.
- **`chat_service.py`:** Merges messages and deletion markers into a chronological thread stream for the chat viewer.
- **`timeline_service.py`:** Handles timeline queries, date filtering, and histogram aggregation.
- **`correlation_service.py`:** Orchestrates cross-platform contact matching and temporal message matrix synthesis.
- **`report_service.py`:** In-memory PDF compiler built with ReportLab Flowables. Enforces strict legal exclusion of AI assistant data.
- **`assistant_service.py`:** Rule-based and keyword-driven natural language processing engine for emotional tone and intention classification.
- **`log_service.py`:** Records immutable chain-of-custody activity logs for every operation.

### 7.3 Complete REST API Reference (All Endpoints)

#### 1. Cases Router (`/api/cases`)
- `POST /api/cases` — Create a new forensic case.
- `GET /api/cases` — List all registered cases.
- `GET /api/cases/{case_id}` — Get case metadata by ID.
- `PUT /api/cases/{case_id}` — Update case details (name, investigator, status).
- `DELETE /api/cases/{case_id}` — Delete case and all associated evidence, messages, and logs (cascading).
- `GET /api/cases/{case_id}/workspace` — Unified Workstation State Endpoint: Returns case details, active evidence list, hash integrity score, analysis stage, and summary counts.

#### 2. Chats Router (`/api/cases/{case_id}/chats`)
- `GET /api/cases/{case_id}/chats` — Returns list of all conversation threads across WhatsApp and Telegram with participant JIDs, names, and message counts.
- `GET /api/cases/{case_id}/chats/{jid}/messages` — Returns complete message stream for a thread, including inline deletion markers and media attachments.

#### 3. Evidence Router (`/api/evidence`)
- `POST /api/evidence/upload` — Ingest evidence file or ZIP archive; computes SHA-256, MD5, and SHA-1; unpacks contents; records manifest.
- `GET /api/evidence?case_id={id}` — List all evidence containers for a case.
- `GET /api/evidence/{evidence_id}` — Retrieve specific evidence container details.
- `GET /api/evidence/{evidence_id}/files` — List unpacked files within an evidence container.
- `GET /api/evidence/{evidence_id}/files/{file_id}` — Get metadata for a specific unpacked file.
- `POST /api/evidence/{evidence_id}/verify-hashes` — Cryptographic Hash Verification: Recomputes disk hashes and compares against recorded manifest (`VERIFIED_INTACT` vs `HASH_MISMATCH`).
- `GET /api/evidence/{evidence_id}/exif` — Extract EXIF camera and GPS metadata from evidence image files.
- `GET /api/evidence/{evidence_id}/sqlite-inspect` — SQLite Inspector: Inspect raw tables and schema of extracted `msgstore.db` or `cache4.db`.
- `DELETE /api/evidence/{evidence_id}` — Delete evidence record and stored disk files.

#### 4. WhatsApp Parser Router (`/api/whatsapp`)
- `POST /api/whatsapp/evidence/{evidence_id}/analyze/whatsapp` — Trigger WhatsApp artifact extraction.
- `GET /api/whatsapp/evidence/{evidence_id}/wa-messages` — Fetch extracted WhatsApp messages.
- `GET /api/whatsapp/evidence/{evidence_id}/wa-contacts` — Fetch extracted WhatsApp contacts.
- `GET /api/whatsapp/evidence/{evidence_id}/wa-groups` — Fetch extracted WhatsApp groups.
- `GET /api/whatsapp/evidence/{evidence_id}/wa-media` — Fetch WhatsApp media items.

#### 5. Telegram Parser Router (`/api/telegram`)
- `POST /api/telegram/evidence/{evidence_id}/analyze/telegram` — Trigger Telegram artifact extraction.
- `GET /api/telegram/evidence/{evidence_id}/tg-messages` — Fetch extracted Telegram messages.
- `GET /api/telegram/evidence/{evidence_id}/tg-contacts` — Fetch extracted Telegram contacts.
- `GET /api/telegram/evidence/{evidence_id}/tg-groups` — Fetch extracted Telegram groups.
- `GET /api/telegram/evidence/{evidence_id}/tg-media` — Fetch Telegram media items.

#### 6. Timeline Router (`/api/timeline` & `/api/cases/{case_id}/timeline`)
- `POST /api/cases/{case_id}/timeline/build` — Trigger timeline reconstruction across all ingested evidence.
- `GET /api/cases/{case_id}/timeline` — Retrieve normalized chronological event stream.
- `POST /api/cases/{case_id}/timeline/filter` — Filter timeline events by date range, source app, or event type.
- `GET /api/timeline/cases/{case_id}/histogram` — Get time-density distribution buckets for Chart.js.

#### 7. Deletions Router (`/api/deleted`)
- `POST /api/deleted/cases/{case_id}/deleted/detect` — Run sequence gap deletion analysis.
- `GET /api/deleted/cases/{case_id}/deleted` — Retrieve all detected deletion gap records and confidence scores.

#### 8. Correlation Router (`/api/cases/{case_id}/correlation`)
- `POST /api/cases/{case_id}/correlate` — Trigger cross-platform identity and message correlation engine.
- `GET /api/cases/{case_id}/correlation` — Fetch correlation edges and summary.
- `GET /api/cases/{case_id}/correlation/entities` — Retrieve resolved cross-platform entity pairs.
- `GET /api/cases/{case_id}/correlation/matrix` — Retrieve cross-app message exchange matrix.
- `GET /api/cases/{case_id}/correlation/status` — Get status of correlation analysis.

#### 9. Global Search Router (`/api/search`)
- `GET /api/search` — Global full-text search across messages, contacts, and media.
- `GET /api/search/messages` — Filtered message text search.
- `GET /api/search/contacts` — Contact directory search.
- `GET /api/search/media` — Media file and EXIF search.
- `GET /api/search/summary` — Overview of search hits across categories.

#### 10. Dashboard Analytics Router (`/api/dashboard`)
- `GET /api/dashboard/cases/{case_id}/stats` — Metric totals (messages, contacts, media, deletions).
- `GET /api/dashboard/cases/{case_id}/correlation-stats` — Breakdown of correlated identities and links.
- `GET /api/dashboard/cases/{case_id}/timeline-stats` — Volume trends by date.
- `GET /api/dashboard/cases/{case_id}/overview` — Consolidated executive overview data.

#### 11. Reports & Court PDF Router (`/api/reports` & `/api/cases/{case_id}/reports`)
- `POST /api/cases/{case_id}/reports` — In-Memory Court PDF Generator: Compiles and streams court-ready PDF report (`StreamingResponse`); logs metadata and SHA-256 in `generated_reports`.
- `GET /api/cases/{case_id}/reports/history` — Report History Tracker: Retrieves list of previously generated court reports with SHA-256 hashes and page counts.
- `GET /api/cases/{case_id}/reports/{report_id}/download` — Direct re-download of a generated court report.
- `GET /api/cases/{case_id}/reports/summary` — Report section preview summary.

#### 12. Audit Logs Router (`/api/logs`)
- `GET /api/logs/activity?case_id={id}` — Retrieve chain-of-custody audit logs.
- `GET /api/logs/analysis?case_id={id}` — Retrieve parser diagnostic execution logs.
- `GET /api/logs/errors?case_id={id}` — Retrieve system error logs with stack traces.
- `GET /api/logs/summary/{case_id}` — High-level audit activity summary.

#### 13. Demo Ingestion Router (`/api/demo`)
- `POST /api/demo/create-demo-case` — Generates a complete forensic demo case with realistic WhatsApp, Telegram, timeline, and deletion records.
- `DELETE /api/demo/demo-case/{case_id}` — Cleans up demo case records and temporary files.

#### 14. AI Forensic Assistant Router (`/api/cases/{case_id}/assistant`)
- `POST /api/cases/{case_id}/assistant/query` — Natural language investigator query endpoint. Searches messages, detects keywords, and returns answers with cited evidence.
- `POST /api/cases/{case_id}/assistant/sentiment` — Chat thread sentiment analyzer. Classifies emotional tone, detects intent markers, and calculates suspicion confidence scores.

#### 15. System Health Router (`/api/health`)
- `GET /api/health` — Returns system status, application version, and demo mode flag.

---

## 8. Frontend Forensic Workstation (`frontend/`)

### 8.1 Visual Identity & Design System
The user interface follows a clinical, high-density dark forensic theme:
- **`forensic-950` (`#0b0f17`):** Primary background surface.
- **`forensic-900` (`#111827`):** Workstation container, cards, and modal bodies.
- **`forensic-800` (`#1f2937`):** Dividers, borders, and input fields.
- **`accent-cyan` (`#06b6d4`):** Primary interactive CTA, active indicators, cryptographic hashes.
- **`accent-emerald` (`#10b981`):** WhatsApp branding and verified integrity badges (`VERIFIED_INTACT`).
- **`accent-blue` (`#3b82f6`):** Telegram branding and system media.
- **`accent-violet` (`#8b5cf6`):** Cross-platform correlation links and AI copilot indicators.
- **`accent-rose` (`#f43f5e`):** Deleted message warnings, sequence gaps, and tamper alerts (`HASH_MISMATCH`).
- **`accent-amber` (`#f59e0b`):** Investigative warnings, unverified hashes, and deceptive/aggressive sentiment.

**Typography:**
- **`Inter`:** Clean interface labels, cards, and narrative reports.
- **`JetBrains Mono`:** Cryptographic hashes (SHA-256, MD5, SHA-1), timestamps, JIDs, and SQLite hex inspector views.

### 8.2 Navigation & 4-Stage Forensic Workflow
- **Context-Aware Sidebar (`Sidebar.jsx`):** Detects whether an active case is selected (`/cases/:caseId/*`) and dynamically renders the 8 core case workstation tools. If no case is selected, case-specific links are disabled.
- **Forensic Workflow Stepper (`ForensicWorkflowStepper.jsx`):** A visual header widget indicating progress through the four standardized forensic stages:
  1. *Ingestion & Hashing*
  2. *Extract & Parse*
  3. *Analyze & Correlate*
  4. *Court Export*

### 8.3 Page-by-Page Specifications (All 11 Pages)
1. **`HomeScreen.jsx` (`/`):** Hero landing page displaying system status, direct link to Case Registry, and a prominent "Create Demo Case" trigger opening `DemoModal.jsx`.
2. **`CaseListPage.jsx` (`/cases`):** Registry of all forensic investigations. Displays case title, investigator name, date created, evidence count, and hash integrity status. Features clean `Open Case` and `Delete Case` actions without redundant icons.
3. **`CaseWorkspacePage.jsx` (`/cases/:caseId`):** Master layout container wrapping all sub-views. Hosts the `ForensicWorkflowStepper` and docked `ForensicAssistantDrawer`.
4. **`DashboardPage.jsx` (`/cases/:caseId/dashboard`):** Executive overview featuring 4 KPI metric cards, `MessageDistributionChart` (WhatsApp vs Telegram doughnut), `MessageVolumeChart` (daily activity line chart), recent events feed, and verification status. Redundant quick-action redirect links have been eliminated.
5. **`EvidencePage.jsx` (`/cases/:caseId/evidence`):** Evidence file manifest table displaying relative paths, file sizes, MIME types, and cryptographic SHA-256 badges. Features action buttons to open `ExifMetadataDrawer`, `SqliteInspectorModal`, and `EvidenceHashVerificationModal`.
6. **`ChatViewerPage.jsx` (`/cases/:caseId/chat`):** High-density three-pane chat investigation view:
   - *Left Pane:* Contact and group thread list with app badges and message counts.
   - *Center Stream:* Interactive message bubbles with sender information, timestamp, attachment previews, and prominent red/amber deletion gap warnings (`[DELETED MESSAGE DETECTED]`).
   - *Right Drawer:* Raw message metadata, cryptographic signatures, and investigator notes.
7. **`TimelinePage.jsx` (`/cases/:caseId/timeline`):** Filterable chronological stream. Includes a time-density histogram chart, date range pickers, source app filters, event search, and cryptographic event fingerprint badges.
8. **`CorrelationPage.jsx` (`/cases/:caseId/correlation`):** Cross-platform analysis view displaying:
   - *Entity Resolution Table:* Maps WhatsApp JIDs to Telegram usernames and phone numbers.
   - *Cross-App Message Thread Matrix:* Side-by-side correlated conversation exchanges occurring within matching time windows.
9. **`ReportsPage.jsx` (`/cases/:caseId/reports`):** Comprehensive court report generator and history tracker:
   - Report configuration checkboxes (Evidence, Custody, Timeline, Deletions, Correlations).
   - Investigator metadata inputs (Lead Analyst, Agency, Case Notes, Sworn Integrity Declaration).
   - `ReportPdfPreview.jsx` offering live layout preview.
   - Direct streaming download trigger (`responseType: 'blob'`).
   - In-App Report History Tracker Table: Lists previously generated court reports with report ID, filename, timestamp, size, total pages, and SHA-256 verification hash, with direct re-download actions.
10. **`LogsPage.jsx` (`/cases/:caseId/logs`):** Displays three tabbed audit logs: Chain-of-Custody Activity Logs, Parser Diagnostic Logs, and System Error Logs with stack traces.
11. **`SearchPage.jsx` (`/cases/:caseId/search`):** Full-text keyword search across messages, contacts, and media files.

### 8.4 Specialized Interactive Components & Drawers
- **`DemoModal.jsx`:** Interactive modal allowing examiners to generate realistic demo cases with configurable message counts, contact counts, and platform selections.
- **`EvidenceHashBadge.jsx`:** Monospace SHA-256 badge with click-to-copy and status tag (`VERIFIED_INTACT` / `HASH_MISMATCH`).
- **`EvidenceHashVerificationModal.jsx`:** Triggers real-time cryptographic verification of on-disk evidence files against the database manifest.
- **`ExifMetadataDrawer.jsx`:** Slide-out panel displaying image previews, camera make/model, capture timestamp, ISO, and GPS coordinates with interactive Google Maps links.
- **`SqliteInspectorModal.jsx`:** Allows investigators to directly browse raw table schemas and rows within extracted SQLite databases (`msgstore.db`, `cache4.db`).
- **`ForensicAssistantDrawer.jsx`:** Slide-out AI copilot drawer providing natural language search and sentiment breakdown, displaying a prominent legal disclaimer badge.

### 8.5 Custom Hooks & Frontend Services
- **Hooks:** `useCases`, `useDashboard`, `useEvidence`, `useChat`, `useTimeline`, `useCorrelation`, `useDeletions`, `useReports`, `useLogs`, `useAiAssistant`.
- **Services:** Clean Axios wrapper modules in `frontend/src/services/` for every backend API resource.

---

## 9. Court-Ready PDF Generation & In-App Report Tracker

### 9.1 In-Memory Streaming Pipeline (Zero Workspace Storage)
All court reports are compiled strictly in an in-memory buffer (`io.BytesIO`) and streamed directly to the browser. **Zero PDF files accumulate on server workspace disks.**

```
POST /api/cases/{case_id}/reports
               │
               ▼
ReportService.generate_report_bytes()
               │
               ├── Pulls deterministic evidence tables (Messages, Hashes, Timeline, Deletions)
               ├── Compiles Platypus flowable PDF in io.BytesIO() buffer
               ├── Calculates SHA-256 digest of PDF bytes
               ├── Inserts manifest into `generated_reports` table
               │
               ▼
FastAPI StreamingResponse (content_type="application/pdf")
               │
               ▼
Browser triggers direct PDF Blob download
```

### 9.2 Judicial Report Structure & Standards
Generated PDF reports are structured according to international digital forensics standards:
1. **Official Cover Page:** Case ID, Case Name, Lead Analyst, Agency, Date of Intake, Sworn Integrity Declaration.
2. **Running Headers & Footers:** ISO/IEC 27037 forensic soundness notice, case reference, generation timestamp, and dynamic page numbering (`Page X of Y`) implemented via `NumberedCanvas`.
3. **Chain of Custody Ledger:** Verifiable timeline of evidence intake, verification, analysis runs, and report generation.
4. **Evidence Manifest & Cryptographic Hashes:** Complete catalog of evidence files, sizes, MIME types, and SHA-256 / MD5 / SHA-1 hashes.
5. **Reconstructed Chronological Timeline:** Formatted tabular timeline with normalized UTC timestamps, source applications, entity JIDs, and 64-character event hash fingerprints.
6. **Deletion Gap Analysis:** Identified sequence gaps, missing message counts, and algorithmic confidence scores.
7. **Cross-Platform Correlated Entities:** Resolved phone numbers, usernames, and cross-application communication links.
8. **Sworn Forensic Examiner Sign-off Block:** Formal signature and legal attestation section for court testimony.

### 9.3 In-App Report History Tracker (`generated_reports`)
Every generated court report is tracked in PostgreSQL:
- Unique `report_id` (UUID)
- Case ID and Report Type
- Lead Analyst and Agency name
- Cryptographic SHA-256 hash of the exact generated PDF byte stream
- Total page count and file size in bytes
- Target filename and generation timestamp
- Dedicated re-download endpoint: `GET /api/cases/{case_id}/reports/{report_id}/download`

---

## 10. AI Forensic Assistant & Chat Sentiment Analyzer (Phase 15 As-Built)

> **Important Note:** While this feature was implemented in Phase 15, it has been flagged during architectural review for complete removal (see Part II, Section 17). The documentation below describes how it was constructed in the codebase.

### 10.1 Investigative Copilot Query Engine
The AI Forensic Assistant (`backend/services/assistant_service.py` and `backend/api/assistant.py`) provides investigators with a natural-language copilot. Investigators can submit queries such as:
- *"Find threats or weapon mentions"*
- *"Show messages discussing cash or wire transfers"*
- *"Locate conversations mentioning meeting places or drop-offs"*

The engine performs lexical pattern matching against case messages, groups relevant findings, highlights matching keywords, and returns answers with cited message IDs and timestamps.

### 10.2 Tone Classification & Suspicion Scoring
The sentiment analysis pipeline categorizes communications into five forensic emotional tones:
- **Aggressive:** Threats, violence, intimidation keywords (`kill`, `destroy`, `threat`, `pay or else`).
- **Suspicious:** Covert behavior, burner phones, contraband (`burner`, `drop off`, `stash`, `secret`, `smuggling`).
- **Deceptive:** Fabricated stories, alibi crafting, false claims (`pretend`, `cover story`, `deny`, `fake`, `wasn't me`).
- **Urgent:** Panic, time-sensitive demands, fleeing (`hurry`, `asap`, `immediately`, `clock is ticking`, `out of time`).
- **Evasive:** Shifting communication channels, avoiding surveillance (`not on phone`, `call on signal`, `delete this chat`).

**Suspicion Confidence Scoring:**
The service computes a composite suspicion rating (0% to 100%) based on:
1. Frequency and weight of detected lexical triggers.
2. Density of aggressive or evasive terms within short time windows.
3. Proximity of suspicious messages to detected deleted message gaps.

### 10.3 Strict Judicial Isolation (Court Admissibility Boundary)
To ensure ArtifactX reports remain strictly admissible in court:
- AI Copilot responses, sentiment classification tags, and suspicion scores **are stored in-memory or returned transiently to the investigator UI**.
- `report_service.py` is hard-coded to ignore assistant data entirely.
- The UI displays an explicit amber warning badge on all AI screens:
  > *"Internal Investigative Aid Only — Strictly Excluded from Legal Court Reports"*

---

## 11. Complete Project Repository Map

```
d:\ArtifactX\
├── .env                                    # Environment variables (Neon DB connection string)
├── .env.example                            # Example environment template
├── .gitignore                              # Git ignore rules
├── CLAUDE.md                               # Project development guidelines & rules (references EVERYTHING.md)
├── EVERYTHING.md                           # Master authoritative compendium (This document)
├── LICENSE.md                              # Academic integrity notice & license terms
├── SKILLS.md                               # Skills registry and design identity reference
├── skills-lock.json                        # Agent skills lockfile
│
├── backend/                                # FastAPI Application Root
│   ├── requirements.txt                    # Python dependencies
│   ├── api/                                # REST API Routers
│   │   ├── assistant.py                    # AI Copilot & Sentiment endpoints (slated for removal)
│   │   ├── cases.py                        # Case CRUD & Workspace state endpoint
│   │   ├── chats.py                        # Chat thread & message stream endpoints
│   │   ├── correlation.py                  # Cross-platform correlation endpoints
│   │   ├── dashboard.py                    # Analytics overview endpoints
│   │   ├── deleted.py                      # Deletion gap detection endpoints
│   │   ├── demo.py                         # Demo case generation endpoints
│   │   ├── evidence.py                     # Ingestion, hashing, EXIF, SQLite inspect
│   │   ├── logs.py                         # Activity, analysis, error log endpoints
│   │   ├── media.py                        # Media item endpoints
│   │   ├── reports.py                      # In-memory PDF generation & report history
│   │   ├── search.py                       # Global full-text search endpoints
│   │   ├── telegram.py                     # Telegram extraction endpoints
│   │   ├── timeline.py                     # Timeline & histogram endpoints
│   │   └── whatsapp.py                     # WhatsApp extraction endpoints
│   ├── app/                                # Core Application Setup
│   │   ├── config.py                       # Pydantic Settings configuration
│   │   ├── database.py                     # SQLAlchemy engine (NullPool, SSL require)
│   │   └── main.py                         # FastAPI app entry point & router mounting
│   ├── middleware/                         # HTTP Middleware
│   │   └── error_logging.py                # Exception logging middleware
│   ├── models/                             # ORM Data Models
│   │   └── models.py                       # 17 SQLAlchemy table definitions
│   ├── repositories/                       # Data Access Layer
│   │   ├── correlation_repo.py, dashboard_repo.py, deleted_repo.py,
│   │   ├── log_repo.py, media_repo.py, report_repo.py, search_repo.py,
│   │   ├── telegram_repo.py, timeline_repo.py, whatsapp_repo.py
│   ├── schemas/                            # Pydantic Request/Response Models
│   │   ├── case.py, contact.py, dashboard.py, deleted.py, evidence.py,
│   │   ├── group.py, log.py, message.py, report.py, search.py,
│   │   └── telegram_contact.py, telegram_group.py, telegram_message.py, timeline.py
│   ├── scripts/                            # Operational & Test Scripts
│   │   ├── setup_postgres.sh               # Local Postgres initialization script
│   │   ├── setup_postgres.sql              # Table schema DDL
│   │   └── test_phase14_e2e.py             # Automated Phase 14 E2E smoke test script
│   ├── services/                           # Business Logic & Workflows
│   │   ├── assistant_service.py            # AI NLP sentiment & copilot logic (slated for removal)
│   │   ├── correlation_service.py          # Entity resolution & message matrix
│   │   ├── dashboard_service.py            # Analytics compilation
│   │   ├── deleted_service.py              # Deletion gap detection orchestration
│   │   ├── log_service.py                  # Activity & audit trail logging
│   │   ├── media_service.py                # EXIF & orphan media analysis
│   │   ├── report_service.py               # In-memory ReportLab court PDF generator
│   │   ├── search_service.py               # Multi-category search orchestration
│   │   ├── telegram_service.py             # Telegram parser orchestration
│   │   ├── timeline_service.py             # Timeline reconstruction & histograms
│   │   └── whatsapp_service.py             # WhatsApp parser orchestration
│   └── utils/                              # Utility Functions
│       ├── file_storage.py, hashing.py, logging_config.py
│
├── forensic/                               # Dedicated Forensic Parsing Package
│   ├── correlation/                        # Correlation graph & matcher
│   ├── deleted/                            # Sequence gap anomaly detector
│   ├── media/                              # Media type & EXIF/GPS parser
│   ├── telegram/                           # Telegram SQLite cache4.db extractor
│   ├── timeline/                           # Chronological event normalizer & builder
│   └── whatsapp/                           # WhatsApp SQLite msgstore.db extractor
│
├── frontend/                               # React 18 + Vite Web Application
│   ├── package.json                        # Dependencies & npm scripts
│   ├── tailwind.config.js                  # Forensic workstation color palette
│   ├── vite.config.js                      # Vite config with API proxy
│   ├── src/
│   │   ├── App.jsx                         # Main router & app shell
│   │   ├── index.css                       # Design tokens & Tailwind utilities
│   │   ├── main.jsx                        # React DOM entry point
│   │   ├── components/                     # Workstation components & modals
│   │   │   ├── assistant/                  # AI Copilot drawer (slated for removal)
│   │   │   ├── cases/, common/, dashboard/, demo/, evidence/, layout/, logs/, reports/, search/, telegram/, whatsapp/, workspace/
│   │   ├── hooks/                          # Custom React data-fetching hooks
│   │   ├── pages/                          # Workstation view pages (11 pages)
│   │   └── services/                       # Axios API service wrappers
│
├── reports/                                # Zero-workspace storage (Kept empty)
└── uploads/                                # Ingested evidence packages & active DBs
```

---

## 12. Current Implementation Tracker (Phases 0–15 Status)

All 15 implementation phases from the original development roadmap have been executed and verified:

| Phase | Description | Key Deliverables | Status |
|---|---|---|:---:|
| **Phase 0** | Codebase Audit | Comprehensive read-through of parsers, timeline builder, correlation engine, and report services | ✅ Complete |
| **Phase 1** | Foundation Fixes | Added port 5174 to CORS; implemented traceback logging; corrected deletion detection | ✅ Complete |
| **Phase 2** | Backend Demo Engine | Fixed DemoData defaults; enforced `DEMO_MODE` guard; added timeline and deletion mock generation | ✅ Complete |
| **Phase 3** | Frontend Demo UX | Implemented `DemoModal.jsx` and integrated into `HomeScreen.jsx` | ✅ Complete |
| **Phase 4** | Dashboard Visualizations | Installed Chart.js; created `MessageVolumeChart` and `MessageDistributionChart` | ✅ Complete |
| **Phase 5** | Forensic Parser Audit | Verified WhatsApp and Telegram contact, group, message, and media parsers | ✅ Complete |
| **Phase 6** | Initial Smoke Test | End-to-end verification of backend startup, demo case creation, and report generation | ✅ Complete |
| **Phase 7** | Workstation UI Overhaul | Eliminated redundant buttons and quick links; introduced `CaseWorkspacePage` & `ForensicWorkflowStepper` | ✅ Complete |
| **Phase 8** | Multi-Hash & Audit Trail | Implemented SHA-256, MD5, and SHA-1 hashing on upload; added on-disk verification and `activity_logs` | ✅ Complete |
| **Phase 9** | EXIF & SQLite Inspector | Implemented Pillow/ExifRead GPS extraction and raw SQLite table inspection modal | ✅ Complete |
| **Phase 10** | Interactive Chat Viewer | Developed 3-pane `ChatViewerPage` with inline deletion markers and metadata drawer | ✅ Complete |
| **Phase 11** | Timeline Reconstruction | Built chronological event stream with UTC normalization, SHA-256 fingerprints, and density histogram | ✅ Complete |
| **Phase 12** | Correlation Engine | Implemented E.164 phone normalization, entity resolution table, and cross-app message matrix | ✅ Complete |
| **Phase 13** | In-Memory Court Reports | Overhauled ReportLab generator to stream in-memory (`io.BytesIO`); created `generated_reports` tracker | ✅ Complete |
| **Phase 14** | Workstation Validation | Automated 11-step end-to-end smoke test script (`test_phase14_e2e.py`) verifying zero disk writes | ✅ Complete |
| **Phase 15** | AI Copilot & Sentiment | Implemented `assistant_service.py`, tone detection, suspicion scoring, and court report exclusion | ⚠️ Built; Slated for Removal |

---

## 13. Installation, Configuration & Execution Guide

### Prerequisites
- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Version 3.11 to 3.13
- **Node.js:** Version 18 or higher (with npm)
- **Database:** PostgreSQL database instance (Neon Cloud or local PostgreSQL)

### Step 1: Clone Repository & Configure Environment
Create a `.env` file in the project root:

```ini
APP_NAME=ArtifactX
DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL Connection String (Neon or Local)
DATABASE_URL=postgresql://neondb_owner:...@neon.tech/neondb?sslmode=require

DEMO_MODE=true
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=1073741824
```

### Step 2: Backend Setup & Launch

#### Windows (PowerShell):
```powershell
# 1. Activate virtual environment (if present) or install requirements
.venv\Scripts\activate
pip install -r backend\requirements.txt

# 2. Set PYTHONPATH to repository root
$env:PYTHONPATH = "D:\ArtifactX"

# 3. Start FastAPI server via Uvicorn
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

#### Linux / macOS:
```bash
# 1. Activate virtual environment
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Set PYTHONPATH
export PYTHONPATH="$(pwd)"

# 3. Start server
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

### Step 3: Frontend Setup & Launch

Open a new terminal window:

```bash
cd frontend
npm install
npm run dev
```

The frontend application will be accessible at `http://localhost:5173` (or `5174`).

---

## 14. Testing & Verification Records

### Automated Smoke Test Execution ([`test_phase14_e2e.py`](file:///d:/ArtifactX/backend/scripts/test_phase14_e2e.py))
- **Health Verification:** `status="ok"`, `demo_mode=True`.
- **Evidence Verification:** On-disk SHA-256 hashes validated intact (`VERIFIED_INTACT`).
- **Streaming Report Engine:** 15,129-byte court PDF compiled in-memory; verified **0 PDF files written to workspace**.
- **In-App Report Tracker:** Database recorded matching SHA-256 byte signature (`2bfacb8...`).
- **Re-Download Stream:** Verified re-downloaded stream matched original cryptographic digest.
- **Result:** **11/11 automated end-to-end tests passed successfully.**

### Frontend Production Build
- Executed `npm run build`: `✓ built in 14.19s`, 0 syntax or module errors.

---

## 15. Credits, Academic Integrity & License

### Development Attribution
- **Architecture, Backend & Workstation Core:** Spandan Mhaske
- **Testing, Verification & Quality Assurance:** Om Chaudhari
- **Forensic Research & Documentation:** Gurudatt Pote, Swami Sonar

### Academic Integrity Notice & Terms of Use
*Copyright (c) 2026 ArtifactX Team. All rights reserved.*
This repository is published publicly **strictly for portfolio evaluation and academic review purposes**. Copying or submitting this code for university assignments, bootcamps, or commercial products without authorization constitutes plagiarism and is strictly prohibited. Refer to [LICENSE.md](file:///d:/ArtifactX/LICENSE.md) for full terms.

---
---

# PART II: STRATEGIC REORIENTATION, MISSING GAPS & FUTURE ROADMAP

> **Crucial Guidance for Developers & AI Agents:**  
> The sections below define where ArtifactX **must go next**. While Part I documents the code that currently compiles and runs, Part II identifies the critical architectural gaps between the current prototype and the true, uncompromising digital forensics workstation it was intended to become.

---

## 16. Strategic Critical Realization: What The Developer Must Know

An objective evaluation of the current application reveals three fundamental truths:

1. **The Word "Analysis" Is Unfulfilled:**  
   Currently, the workstation is predominantly an **Evidence Viewer and Inspector** (parsing tables, rendering message bubbles, listing contacts, and displaying file manifests). It does not yet perform true **forensic analysis**—it lacks behavioral chronobiology, network centrality, criminal hierarchy modeling, automated financial/crypto artifact harvesting, and spatial velocity anomaly detection.
2. **The Word "Correlation" Is Only Superficial:**  
   Currently, correlation consists of basic string-matching of phone numbers and grouping messages that occur within an arbitrary 15-minute sliding window. Real-world suspects hide their numbers on Telegram, operate multiple personas, and switch platforms to evade surveillance. Correlation must become an intelligent **Multi-Entity Identity Resolution Graph & Platform Handover Engine**.
3. **Deleted Messages Are Only "Detected", Not "Recovered":**  
   Currently, the system flags sequence gaps (e.g. noticing message ID 105 is missing between 104 and 106). That is detection. **Forensic recovery means parsing SQLite Write-Ahead Logs (`-wal`), freelist pages, and cell slack space to carve the actual deleted message text, timestamp, and sender identity.**
4. **AI Sentiment & Copilots Are a Detriment to Forensics:**  
   Keyword-based sentiment analysis ("Aggressive", "Deceptive") and conversational AI copilots are legally inadmissible, subjective, and violate the *Daubert* standard for expert testimony. They introduce legal liability and must be excised.

---

## 17. Planned Excision: Decommissioning AI Sentiment & Copilot

### Why It Must Be Removed
1. **Inadmissibility in Judicial Courts:** In a criminal court, an expert witness cannot defend a proprietary keyword heuristic that scores a suspect's text as "78% Deceptive" or "Aggressive". It fails the test of scientific peer review, known error rate, and objective reproducibility.
2. **Confirmation Bias & Legal Liability:** Automated suspicion scores risk biasing the investigator and give defense attorneys grounds to claim that evidence triage was prejudiced by non-validated automated scoring.
3. **Forensic Purity:** Professional tier-1 forensic suites (Cellebrite Physical Analyzer, Magnet AXIOM) strictly focus on bitstream preservation, parsing, chronological reconstruction, and verified data carving.

### Execution Blueprint for Removal
When undertaking the upcoming cleanup refactor, developers should execute the following removals:
- **Delete Backend API Router:** `backend/api/assistant.py` and remove its router include from `backend/app/main.py`.
- **Delete Backend Service:** `backend/services/assistant_service.py`.
- **Delete Frontend Drawer:** `frontend/src/components/assistant/ForensicAssistantDrawer.jsx`.
- **Delete Frontend Hook & Service:** `frontend/src/hooks/useAiAssistant.js` and `frontend/src/services/assistantService.js`.
- **Remove UI Triggers:** Remove the "AI Copilot" header buttons from `CaseWorkspacePage.jsx` and `ChatViewerPage.jsx`.

---

## 18. Future Flagship Pillar 1: True Deleted Message Recovery Engine (Physical Carving)

To become a tier-1 digital forensics platform, ArtifactX must implement physical SQLite database carving to extract **the actual payload of deleted messages**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SQLITE PHYSICAL PAYLOAD RECOVERY PIPELINE                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  WAL FILE CARVER │        │  FREELIST CARVER │        │ SLACK SPACE CARV │
│  (msgstore-wal)  │        │ (freelist pages) │        │ (B-Tree cells)   │
├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│Extracts uncheck- │        │Traverses freed   │        │Scans unused cell │
│pointed frames    │        │B-Tree leaf pages │        │bytes before      │
│containing deleted│        │before database   │        │page reorganization│
│rows in pristine  │        │VACUUM occurs     │        │for residual text │
│state             │        │                  │        │                  │
└──────────────────┘        └──────────────────┘        └──────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BINARY RECORD RECONSTRUCTION & PARSING                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Decode SQLite variable-length integers (varints) to determine serial types│
│ • Extract Protobuf payloads for WhatsApp message structures                 │
│ • Reconstruct MTProto serialized message packets for Telegram               │
│ • Match carved records to parent conversation JID                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
              [Recovered Message: Text + Timestamp + Sender JID]
```

### Engineering Specifications for Implementation
1. **SQLite Write-Ahead Log (`-wal`) Parsing:**
   - WhatsApp and Telegram operate SQLite in WAL mode. When a user deletes a message, the deletion is appended to the WAL file. The original database pages remain unaltered in the WAL until a checkpoint occurs.
   - The WAL carver will read raw 32-byte frame headers, reconstruct table B-Trees, and extract pre-deletion message records directly from uncommitted frames.
2. **Freelist Leaf Page Traversal:**
   - Deleted table records move pages into the SQLite Freelist. The carver will traverse the freelist trunk pages, read unallocated leaf pages, and decode deleted cell payloads before a database `VACUUM` occurs.
3. **B-Tree Cell Slack Space Carving:**
   - When a row is deleted within an active leaf page, its cell pointer is removed, but its payload bytes persist in the page slack space until the page is defragmented. The carver scans this residual space for UTF-8 string runs.
4. **Protobuf Wire Format Recovery:**
   - WhatsApp encapsulates modern messages in Google Protobuf. Carved byte streams will be parsed by a schema-adaptive Protobuf decoder to recover:
     - Field 1: Message Text Body
     - Field 2: Remote JID
     - Field 3: Millisecond Timestamp
     - Field 4: Media URL / Thumbnail bytes

---

## 19. Future Flagship Pillar 2: Deep Cross-Platform Correlation Engine

The current prototype's phone number string matching must be replaced with an investigative multi-platform correlation architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CROSS-PLATFORM FORENSIC CORRELATION ENGINE                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
     ┌─────────────────┬──────────────┴──────────────┬─────────────────┐
     ▼                 ▼                             ▼                 ▼
┌──────────────┐ ┌──────────────┐              ┌──────────────┐  ┌──────────────┐
│IDENTITY GRAPH│ │CHANNEL-HOPPING│              │PERCEPTUAL    │  │SHARED CONTENT│
│ RESOLUTION   │ │HANDOVER DETECT│              │MEDIA HASHING │  │ & CRYPTO ARTI│
├──────────────┤ ├──────────────┤              ├──────────────┤  ├──────────────┤
│Unifies JID,  │ │Detects when  │              │pHash/dHash   │  │Correlates    │
│TG handle,    │ │suspect says  │              │matches images│  │crypto wallets│
│phone, avatar,│ │"go to TG" and│              │forwarded     │  │IBANs, bank   │
│and contact   │ │resumes talk  │              │across apps   │  │numbers, code │
│aliases into  │ │within minutes│              │even if resized│ │words         │
│single entity │ │              │              │              │  │              │
└──────────────┘ └──────────────┘              └──────────────┘  └──────────────┘
```

### Engineering Specifications for Implementation
1. **Multi-Entity Identity Resolution Graph:**
   - Builds a unified Person Graph node linking disparate digital footprints:
     $$\text{Person} \leftarrow \{\text{WA JID}, \text{TG User ID}, \text{E.164 Phone}, \text{TG Handle}, \text{Avatar Hash}, \text{Contact Book Aliases}\}$$
   - Resolves identities even when a Telegram user hides their phone number by cross-referencing address book mutual contacts across seized databases.
2. **Platform Handover & Surveillance Evasion Detection:**
   - Automatically detects when a suspect transitions between platforms to evade monitoring.
   - Flags when a conversation on WhatsApp terminates and a conversation between the same resolved entities begins on Telegram within minutes:
     $$\Delta t = |t_{\text{Telegram\_Start}} - t_{\text{WhatsApp\_End}}| < 180\text{ seconds}$$
   - Flags explicit handover keywords: *"hop on TG"*, *"check telegram"*, *"switch to secret chat"*, *"call me on signal"*.
3. **Perceptual Media Correlation (`pHash` / `dHash`):**
   - Suspects frequently forward contraband images, bank receipts, or identity documents between WhatsApp and Telegram. Each app recompresses, resizes, and strips EXIF tags differently.
   - Computes perceptual hashes (pHash and dHash) for every extracted media item. Images with a Hamming distance $\le 4$ are mathematically linked as identical visual content, establishing cross-platform document sharing.
4. **Cross-App Shared Artifact Stitching:**
   - Correlates conversations across different applications that share identical high-value extracted artifacts:
     - Cryptocurrency wallet addresses (Bitcoin, Ethereum, Monero, USDT TRC-20).
     - Banking details (IBANs, routing numbers, UPI handles).
     - Alphanumeric tracking codes, flight numbers, or distinct code-words.
5. **Spatiotemporal Rendezvous Detection:**
   - Cross-correlates GPS coordinates extracted from WhatsApp photos with Telegram locations to identify physical co-location ($< 50$ meters at $\Delta t < 30$ mins).

---

## 20. Filling The Void: Comprehensive Digital Forensics Analysis Framework

> **The Meaning of "Analysis":**  
> A true digital forensics suite must not stop at extracting data. It must provide **behavioral intelligence, social network analysis, financial artifact harvesting, and anti-forensic anomaly detection**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DIGITAL FORENSIC ANALYSIS FRAMEWORK                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
     ┌─────────────────┬──────────────┴──────────────┬─────────────────┐
     ▼                 ▼                             ▼                 ▼
┌──────────────┐ ┌──────────────┐              ┌──────────────┐  ┌──────────────┐
│  MODULE A:   │ │  MODULE B:   │              │  MODULE C:   │  │  MODULE D:   │
│  TEMPORAL &  │ │NETWORK GRAPH │              │ FINANCIAL &  │  │SPATIOTEMPORAL│
│  BEHAVIORAL  │ │ & CENTRALITY │              │CRYPTO CARVING│  │  TRAJECTORY  │
├──────────────┤ ├──────────────┤              ├──────────────┤  ├──────────────┤
│• 24x7 Rhythm │ │• Hub/Kingpin │              │• BTC/ETH/XMR │  │• Speed Checks│
│• Velocity    │ │• Brokers     │              │• IBAN/SWIFT  │  │• Rendezvous  │
│• Turnaround  │ │• Modularity  │              │• Darknet URLs│  │• Movement Map│
│• Blackouts   │ │• Clique Map  │              │• Credentials │  │• Multi-User  │
└──────────────┘ └──────────────┘              └──────────────┘  └──────────────┘
```

### Module A: Temporal & Behavioral Communication Profiling
1. **24×7 Chronobiological Circadian Heatmaps:**
   - Plots communication frequency across a 24-hour day / 7-day week matrix.
   - Identifies the suspect's natural circadian rhythm: active waking hours, sleep periods, and anomalous middle-of-the-night bursts.
   - Assists in verifying physical time zones (e.g. suspect claiming to be in New York but operating on UTC+5:30 patterns).
2. **Communication Velocity & Spike Curves:**
   - Tracks message rate per hour ($V = \frac{dM}{dt}$).
   - Automatically flags statistical volume surges ($> 3\sigma$ above baseline), isolating the exact hours surrounding critical crime events.
3. **Turnaround Latency & Interaction Dominance:**
   - Analyzes response latency between entities:
     - Who initiates the conversation?
     - What is the average response time for Entity A vs. Entity B?
     - Reveals organizational hierarchy: subordinates respond in seconds; leaders respond with delay and concise instructions.
4. **Communication Blackout & Device Inactivity Detection:**
   - Automatically detects unnatural silence periods in established communication threads.
   - Flags sudden cutoffs preceding a crime, indicating burner phone usage, travel, or device seizure.

### Module B: Social Network Centrality & Hierarchy Mapping
1. **Degree Centrality (Hub Identification):**
   - Counts direct communication edges, identifying the most active members of a seized network.
2. **Betweenness Centrality (Broker & Courier Detection):**
   - Measures how often an individual falls on the shortest communication path between other members:
     $$C_B(v) = \sum_{s \ne v \ne t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$
   - **Investigative Value:** Identifies the "fixers", couriers, or middle-men who bridge two isolated criminal cells.
3. **Eigenvector Centrality:**
   - Identifies hidden leaders who maintain low message volume but communicate exclusively with high-ranking operatives.
4. **Community Detection (Louvain Modularity):**
   - Algorithmic clustering of communication networks into distinct operational factions or sub-groups.

### Module C: Financial, Crypto & Darknet Artifact Carving
A deterministic forensic extraction engine scanning message bodies, file names, and unallocated text for high-value intelligence:
1. **Cryptocurrency Wallet Carving:**
   - **Bitcoin:** Legacy P2PKH (`1...`), P2SH (`3...`), and Native SegWit/Bech32 (`bc1q...`).
   - **Ethereum & EVM Chains:** 42-character hex addresses (`0x[a-fA-F0-9]{40}`).
   - **Monero (XMR):** Privacy coin stealth addresses (`4...` or `8...`, 95 characters).
   - **Tether (USDT) TRC-20:** Tron addresses (`T[a-zA-Z0-9]{33}`).
2. **Financial Routing Artifacts:**
   - International Bank Account Numbers (IBANs) with ISO 7064 mod-97 verification.
   - SWIFT / BIC codes, wire routing numbers, and payment gateway identifiers.
   - Credit card numbers with real-time Luhn algorithm checksum validation.
3. **Darknet & Anonymization Artifacts:**
   - Tor hidden service addresses (`.onion` v3 URLs, 56 characters).
   - Telegram MTProto proxy links (`tg://proxy?...`), SOCKS5 endpoints, and VPN gateways.
4. **Credentials & Sensitive Data Carving:**
   - API keys, private keys (`-----BEGIN PRIVATE KEY-----`), seed phrases, and password patterns.

### Module D: Spatiotemporal Geolocation & Trajectory Mapping
1. **Unified Chronological Trajectory:**
   - Merges EXIF GPS tags from media files, WhatsApp shared locations, and Telegram live locations into an interactive chronological travel map.
2. **Velocity Check & Impossible Transit Detection (Teleportation Anomaly):**
   - Computes physical transit velocity between consecutive geolocation tags:
     $$v = \frac{\text{HaversineDistance}(\text{Point}_A, \text{Point}_B)}{t_B - t_A}$$
   - If velocity exceeds physically possible speeds (e.g. $> 900\text{ km/h}$ for land travel, or simultaneous activity in two distant cities within 10 minutes), the system flags **Account Sharing, Location Spoofing, or Multiple Physical Users**.
3. **Proximity & Rendezvous Analysis:**
   - Evaluates multi-device or multi-suspect cases to detect when two separate individuals were physically within 50 meters of each other at the same time.

### Module E: Anti-Forensics & Database Tamper Diagnostics
1. **SQLite Header Verification:**
   - Analyzes SQLite file headers: page size, file change counter, schema cookie, and freelist page counts.
   - Flags discrepancies where database size on disk does not match the page allocation table, indicating file truncation or manual hex editing.
2. **Clock Skew & Timestamp Tampering:**
   - Detects messages with timestamps preceding the phone's system boot time, creation timestamps occurring in the future, or sequence inversions where lower message IDs contain higher timestamps.

---

## 21. Strategic Engineering Roadmap (Phases R1–R4)

To bridge the gap between the current working prototype and the true forensic vision, the next development cycles should be executed according to this phased roadmap:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ARTIFACTX STRATEGIC ROADMAP PHASING                       │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ├──► PHASE R1: AI Excision & Codebase Purge
  │    ├── Delete backend/api/assistant.py and backend/services/assistant_service.py
  │    ├── Delete ForensicAssistantDrawer.jsx, useAiAssistant.js, assistantService.js
  │    └── Remove AI buttons from CaseWorkspacePage and ChatViewerPage
  │
  ├──► PHASE R2: True Deleted Message Recovery Engine (Physical Carving)
  │    ├── Implement SQLite WAL (-wal) frame parser for uncheckpointed rows
  │    ├── Implement SQLite Freelist leaf page carver
  │    ├── Implement B-Tree cell slack space text extractor
  │    └── Implement schema-adaptive Protobuf payload reconstructor
  │
  ├──► PHASE R3: Deep Cross-Platform Correlation Engine
  │    ├── Implement Multi-Entity Identity Resolution Graph (Person entity)
  │    ├── Implement Platform Handover / Surveillance Evasion Detector
  │    ├── Implement Perceptual Media Hasher (pHash/dHash, Hamming distance <= 4)
  │    └── Implement Cross-App Shared Artifact Stitching (Crypto/Bank/Code-words)
  │
  └──► PHASE R4: Digital Forensic Analysis Suite
       ├── Module A: 24x7 Circadian Heatmaps & Latency Dominance Analyzer
       ├── Module B: Social Network Centrality (Degree, Betweenness, Modularity)
       ├── Module C: Crypto Wallet, IBAN, Credit Card, and Darknet Carvers
       ├── Module D: Spatiotemporal Map with Teleportation Velocity Checks
       └── Module E: SQLite Header & Clock Skew Tamper Diagnostics
```

By executing this roadmap, ArtifactX will evolve from an experimental prototype into an enterprise-grade digital forensics workstation that delivers verifiable proof, deep intelligence, and true forensic payload recovery for courts of law worldwide.
