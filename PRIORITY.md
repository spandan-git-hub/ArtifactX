# ArtifactX — Implementation Priority

> **What this file is:** Step-by-step phase-wise implementation order.  
> Backend (B) and frontend (F) tasks are separate within each phase.  
> **Tracking:** Mark `[x]` done, `[/]` in-progress, `[ ]` not started.  
> **Source of truth:** Read [BACKEND.md](BACKEND.md) and [FRONTEND.md](FRONTEND.md) for full specs before implementing anything.

---

## Phase 0 — Audit (Before Writing Any Code)

- [x] **A1** — Read `forensic/whatsapp/contact_parser.py`, `group_parser.py`, `media_parser.py`
- [x] **A2** — Read all files in `forensic/telegram/`
- [x] **A3** — Read `forensic/timeline/builder.py`
- [x] **A4** — Read `forensic/correlation/matcher.py`
- [x] **A5** — Read `forensic/media/orphan.py`
- [x] **A6** — Read `backend/services/log_service.py`
- [x] **A7** — Read `frontend/src/hooks/useDashboard.js`
- [x] **A8** — Read `frontend/src/services/reportService.js`
- [x] **A9** — Read `frontend/src/pages/ReportsPage.jsx`
- [x] **A10** — Read `frontend/vite.config.js`

---

## Phase 1 — Fix Broken Foundations

- [x] **B1** Fix CORS missing port 5174 in `backend/app/main.py`
- [x] **B2** Fix stack trace logging across all services using `traceback.format_exc()`
- [x] **B3** Fix WhatsApp deletion detection producing fabricated results in `forensic/deleted/detector.py`
- [x] **B4** Fix silent `sqlite3.Error` in WhatsApp message parser
- [x] **B5** Fix `search_repo._get_evidence_ids` ignoring the `app` filter
- [x] **B6** Fix `analysis_logs.evidence_id` FK constraint if nullable
- [x] **F1** Fix sidebar navigation (context-aware active case links)
- [x] **F2** Fix duplicate navigation in `CaseDetailPage` header
- [x] **F3** Fix broken quick links on `DashboardPage`
- [x] **F4** Fix infinite re-render in `useDashboard.js` using `useCallback`
- [x] **F5** Fix `reportService` GET/POST mismatch
- [x] **F6** Add null guard for `created_at` date formatting

---

## Phase 2 — Fix Demo Mode (Backend)

- [x] **B7** Fix `DemoData` defaults (`has_telegram=True`, `message_count=100`, `contact_count=15`)
- [x] **B8** Add `DEMO_MODE` guard to demo endpoint
- [x] **B9** Create `TimelineEvent` records in demo builder
- [x] **B10** Create `DeletedMessage` records in demo builder

---

## Phase 3 — Demo UX (Frontend)

- [x] **F7** Create `DemoModal` component (`frontend/src/components/demo/DemoModal.jsx`)
- [x] **F8** Integrate `DemoModal` into `HomeScreen`

---

## Phase 4 — Charts (Frontend)

- [x] **F9** Install chart.js packages (`chart.js` + `react-chartjs-2`)
- [x] **F10** Create `MessageVolumeChart` component
- [x] **F11** Create `MessageDistributionChart` component
- [x] **F12** Export new charts from dashboard index
- [x] **F13** Integrate charts into `DashboardPage`

---

## Phase 5 — Validate Forensic Parsers

- [x] **B11** Audit and fix `forensic/whatsapp/contact_parser.py`
- [x] **B12** Audit and fix `forensic/whatsapp/group_parser.py`
- [x] **B13** Audit and fix `forensic/whatsapp/media_parser.py`
- [x] **B14** Audit `forensic/telegram/` — all four parsers
- [x] **B15** Audit `forensic/timeline/builder.py`
- [x] **B16** Audit `forensic/correlation/matcher.py` dataclass field alignment

---

## Phase 6 — Initial End-to-End Smoke Test

- [x] **T1** Backend starts without errors
- [x] **T2** Health endpoint returns `demo_mode=true`
- [x] **T3** Demo case creation produces complete data
- [x] **T4** Dashboard overview returns all data
- [x] **T5** Search returns results from demo data
- [x] **T6** Report generation produces a PDF file
- [x] **T7** Full demo workflow end-to-end
- [x] **T8** Sidebar shows case-specific navigation
- [x] **T9** Search page returns results
- [x] **T10** Reports page works

---

## Phase 7 — Workstation UI/UX Overhaul & Redundancy Removal

Revamp the UI into a high-density, professional Forensic Workstation (`ForensicStudio`) and eliminate all redundant links, broken buttons, and senseless redirects.

### Backend
- [x] **B17** Add `CaseWorkspace` API summary endpoint (`GET /api/cases/{id}/workspace`) returning unified state (case details, active evidence list, hash integrity score, analysis stage).

### Frontend
- [x] **F14** Create `CaseWorkspacePage.jsx` container to wrap case tools with unified sub-route / tab navigation (`/cases/:caseId/*`).
- [x] **F15** Create `ForensicWorkflowStepper.jsx` header showing progress through the 4 forensic stages (Ingest & Hash -> Extract & Parse -> Analyze & Correlate -> Court Export).
- [x] **F16** Remove duplicate action buttons across all page headers that replicate sidebar navigation.
- [x] **F17** Clean up all quick-action buttons on `DashboardPage.jsx` and `CaseDetailPage.jsx` to navigate cleanly to sub-routes without dummy query params.
- [x] **F18** Remove redundant "Quick Actions" card from `CaseDetailPage.jsx` and redundant "Quick Links" from `DashboardPage.jsx`.
- [x] **F19** Simplify `CaseListPage.jsx` row actions to clean `Open Case` and `Delete Case` buttons, removing the confusing magnifying glass icon button.

---

## Phase 8 — Cryptographic Hash Verification & Chain-of-Custody Manifest

Ensure full evidence integrity, multi-hash calculation (SHA-256, MD5, SHA-1), and audit trail logging.

### Backend
- [ ] **B18** Implement SHA-256, MD5, and SHA-1 calculation on evidence upload in `backend/api/evidence.py`.
- [ ] **B19** Implement hash verification endpoint (`POST /api/evidence/{id}/verify-hashes`) to verify on-disk evidence files against recorded `EvidenceFile` manifest.
- [ ] **B20** Implement Chain-of-Custody logging service (`log_activity`) recording evidence ingest, hash verification, analysis runs, and report exports in `activity_logs`.

### Frontend
- [ ] **F20** Create `EvidenceHashBadge.jsx` displaying SHA-256 hash in JetBrains Mono cyan text with click-to-copy and verification status badge (`VERIFIED_INTACT` / `HASH_MISMATCH`).
- [ ] **F21** Add "Verify Evidence Hashes" button on evidence views triggering real-time re-hashing and displaying an integrity manifest modal.

---

## Phase 9 — Artifact Extraction & EXIF Metadata Inspector

Provide rich inspection of extracted mobile app databases, media attachments, and EXIF metadata.

### Backend
- [ ] **B21** Implement EXIF metadata extraction service using Pillow/ExifRead in `backend/api/evidence.py` (`GET /api/evidence/{id}/exif`).
- [ ] **B22** Implement raw SQLite table inspector endpoint (`GET /api/evidence/{id}/sqlite-inspect`) to allow direct inspection of extracted `msgstore.db` and `cache4.db` table structures.

### Frontend
- [ ] **F22** Overhaul `EvidencePage.jsx` with tree/table view, file size, MIME type, SHA-256 hash badges, and raw SQLite inspector modal.
- [ ] **F23** Create `ExifMetadataDrawer.jsx` slide-out drawer rendering image previews, camera make/model, ISO, capture timestamp, and GPS coordinates with map link.

---

## Phase 10 — Interactive Chat Message Thread Viewer with Deletion Indicators

Replace static data tables with an interactive, rich chat view for extracted WhatsApp and Telegram messages.

### Backend
- [ ] **B23** Create `Chat` API endpoints (`GET /api/cases/{id}/chats` and `GET /api/cases/{id}/chats/{jid}/messages`) returning thread message lists with inline deletion flags and media info.

### Frontend
- [ ] **F24** Create `ChatViewerPage.jsx` (`/cases/:caseId/chat`):
  - Left pane: Contact / Group thread list with green (WA) / blue (TG) app badges and message counts.
  - Center pane: Interactive chat bubble stream displaying sender name, JID, timestamp, body text, attachment previews, and EXIF trigger.
  - Center pane: Render prominent red/amber deletion warning badges (`[DELETED MESSAGE DETECTED]`) on detected message sequence/time gaps.
  - Right pane: Selected message raw metadata & cryptographic signature drawer.

---

## Phase 11 — Reconstructed Chronological Timeline & Density Histogram

Provide a filterable multi-app event stream with visualization.

### Backend
- [ ] **B24** Optimize `timeline_service.py` and `TimelineBuilder` to support time-range filtering, app filtering, and density aggregation (`GET /api/timeline/cases/{id}/histogram`).

### Frontend
- [ ] **F25** Overhaul `TimelinePage.jsx` (`/cases/:caseId/timeline`):
  - Chart.js time-density histogram showing message/event volume over time.
  - Filter toolbar: Date Range picker, Source App selector, Event Type filter, Search query.
  - High-density chronological event stream with timestamps, app badges, entity JIDs, and hash fingerprints.

---

## Phase 12 — Evidence Correlation Engine & Visualizer

Map cross-platform identity resolution and message correlations.

### Backend
- [ ] **B25** Enhance `correlation_service.py` to perform phone number normalization (E.164), handle matching, and cross-app message time-window correlation.

### Frontend
- [ ] **F26** Overhaul `CorrelationPage.jsx` (`/cases/:caseId/correlation`):
  - Entity Resolution Table: Maps WhatsApp JIDs to Telegram handles and phone numbers.
  - Cross-App Message Thread Matrix: Displays correlated message exchanges across platforms within time windows.

---

## Phase 13 — In-Memory Court-Ready PDF Generator & In-App Report History Tracker

Overhaul the PDF generator into a zero-workspace storage engine that streams PDFs directly to the browser while tracking generated report history in the database.

### Backend
- [ ] **B26** Update `report_service.py` and `reports.py` to generate court PDFs into an in-memory `io.BytesIO()` buffer and return `StreamingResponse` for direct download — **zero PDF files written to project workspace directory**.
- [ ] **B27** Create `GeneratedReport` model and `GET /api/cases/{id}/reports/history` endpoint to track generated report metadata (Report ID, Case ID, Report Type, Lead Analyst, Timestamp, Verification SHA-256 Hash of PDF bytes, Total Pages, Size Bytes) in the database.
- [ ] **B28** Overhaul ReportLab PDF layout (Cover Page, Custody Log, Evidence Hashes, Timeline, Deletions, Correlated Entities, Sworn Analyst Sign-off Block). **Strictly exclude AI Assistant responses and sentiment scores**.

### Frontend
- [ ] **F27** Overhaul `ReportsPage.jsx` (`/cases/:caseId/reports`):
  - Report configuration section toggles.
  - Lead Analyst name, agency, and case notes input fields.
  - Sworn integrity declaration checkbox.
  - `ReportPdfPreview.jsx` live layout previewer.
  - Direct Blob streaming download trigger (`responseType: 'blob'`).
  - In-App Report History Tracker Table displaying past generated reports, SHA-256 signatures, and re-download/re-generate buttons.

---

## Phase 14 — Workstation Validation & End-to-End Smoke Test

- [ ] **T11** Verify zero broken buttons or non-functional routes across all sub-views.
- [ ] **T12** Execute full evidence ingestion, hash verification, EXIF inspection, chat thread viewing, deletion badge checking, timeline filtering, correlation building, and streaming court-ready PDF generation (confirming zero `.pdf` files written to workspace) end-to-end.

---

## Phase 15 — AI Forensic Assistant & Chat Sentiment Analyzer (FINAL PHASE)

*Note: This phase will be executed as the very last addition after the entire application and core workstation are fully built.*

### Backend
- [ ] **B29** Create `assistant.py` router and `assistant_service.py`:
  - `POST /api/cases/{id}/assistant/query`: Processes investigator natural language questions over case messages and evidence metadata.
  - `POST /api/cases/{id}/assistant/sentiment`: Executes chat sentiment classification (Aggressive, Suspicious, Deceptive, Urgent, Evasive, Neutral), intention marker detection (financial demand, coercion, deletion awareness), and suspicion confidence scoring (0-100%).
- [ ] **B30** Enforce Court Report Exclusion: Ensure `report_service.py` completely ignores `assistant.py` datasets to preserve judicial admissibility of court reports.

### Frontend
- [ ] **F28** Create `ForensicAssistantDrawer.jsx` (`components/assistant/ForensicAssistantDrawer.jsx`):
  - Slide-out copilot chat UI for investigator prompts and assistance.
  - Sentiment & Intention Breakdown widget.
  - Visual disclaimer badge: *"Internal Investigative Aid Only — Excluded from Legal Court Reports"*.
- [ ] **F29** Add optional Sentiment Overlay toggle in `ChatViewerPage.jsx` to display emotional tone badges and suspicion confidence indicators directly on chat messages.
- [ ] **F30** Create `useAiAssistant.js` hook to handle copilot queries, sentiment requests, and confidence score states.

---

## Reference Files

| File | Purpose |
|------|---------|
| [FRONTEND.md](FRONTEND.md) | Spec + audit of every frontend file |
| [BACKEND.md](BACKEND.md) | Spec + audit of every backend file |
| [SKILLS.md](SKILLS.md) | Installed skills and ArtifactX design identity |
| [CLAUDE.md](CLAUDE.md) | Dev rules and run commands |
| [.env](.env) | Environment config |

---

## Quick Start

```powershell
# Backend
pip install -r requirements.txt
$env:PYTHONPATH = "D:\ArtifactX"
$env:PATH = "C:\Users\Spandan\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts;$env:PATH"
cd D:\ArtifactX\backend
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload

# Frontend (new terminal)
cd D:\ArtifactX\frontend
npm install
npm run dev
```
