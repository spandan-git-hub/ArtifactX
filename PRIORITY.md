# ArtifactX — Implementation Priority

> **What this file is:** Step-by-step phase-wise implementation order.  
> Backend (B) and frontend (F) tasks are separate within each phase.  
> **Tracking:** Mark `[x]` done, `[/]` in-progress, `[ ]` not started.  
> **Source of truth:** Read [BACKEND.md](BACKEND.md) and [FRONTEND.md](FRONTEND.md) for full specs before implementing anything.

---

## Phase 0 — Audit (Before Writing Any Code)

These tasks must happen first. They are read-only investigations.

- [ ] **A1** — Read `forensic/whatsapp/contact_parser.py`, `group_parser.py`, `media_parser.py`
  - Verify each exists and follows the same schema-adaptive pattern as `message_parser.py`
  - Verify return dicts match `WhatsAppContact`, `WhatsAppGroup` model fields

- [ ] **A2** — Read all files in `forensic/telegram/`
  - Verify `detector.py`, `message_parser.py`, `contact_parser.py`, `group_parser.py` all exist
  - Verify `detector.py` correctly identifies `cache4.db` / Telegram SQLite schemas

- [ ] **A3** — Read `forensic/timeline/builder.py`
  - Verify `TimelineBuilder.build_timeline_for_case(db, case_id)` exists
  - Verify it returns list of dicts compatible with `TimelineEvent` model fields (especially `normalized_timestamp` as a real `datetime` object)

- [ ] **A4** — Read `forensic/correlation/matcher.py`
  - Verify the dataclasses `WhatsAppMessage`, `WhatsAppContact`, `TelegramMessage`, `TelegramContact`, `MediaItem` defined there have the same field names that `correlation_service.py` uses when converting from ORM objects

- [ ] **A5** — Read `forensic/media/orphan.py`
  - Verify these three function signatures:
    - `find_orphan_media_items(case_id: int, db: Session) -> List[MediaItem]`
    - `find_orphan_files(case_id: int, evidence_id: int, db: Session) -> List[EvidenceFile]`
    - `mark_media_orphan_status(case_id: int, db: Session) -> int`

- [ ] **A6** — Read `backend/services/log_service.py`
  - Verify `log_analysis(evidence_id=0, ...)` does NOT trigger a FK constraint violation
  - The `analysis_logs.evidence_id` column must be nullable for passing `0` or `None` to work
  - If it is NOT nullable, add `nullable=True` to the column definition in `models.py`

- [ ] **A7** — Read `frontend/src/hooks/useDashboard.js`
  - Verify `loadOverview` is wrapped in `useCallback(async (id) => {...}, [])`
  - If not: the DashboardPage causes an infinite re-render loop

- [ ] **A8** — Read `frontend/src/services/reportService.js`
  - Verify `getEvidenceSummary`, `getTimelineSummary`, `getDeletedSummary` use `axios.get(...)` not `axios.post(...)`

- [ ] **A9** — Read `frontend/src/pages/ReportsPage.jsx`
  - Verify it exists and loads the three summary cards

- [ ] **A10** — Read `frontend/vite.config.js`
  - Verify `/api` proxy to `http://localhost:8000` is configured

---

## Phase 1 — Fix Broken Foundations

These are bugs in **currently running code** that cause wrong behavior. Fix these before adding anything new.

### Backend Fixes

- [ ] **B1** Fix CORS missing port 5174
  - File: `backend/app/main.py` line 38
  - Add `"http://localhost:5174"` to `allow_origins` list

- [ ] **B2** Fix stack trace logging across all services
  - Add `import traceback` to the top of each file
  - Replace `stack_trace=str(e.__traceback__)` with `stack_trace=traceback.format_exc()`
  - Files: `whatsapp_service.py`, `telegram_service.py`, `timeline_service.py`, `deleted_service.py`, `correlation_service.py`

- [ ] **B3** Fix WhatsApp deletion detection producing fabricated results
  - File: `forensic/deleted/detector.py` lines 81-93
  - `_get_expected_next_id()`: return `None` for `source_app == "whatsapp"` (WA IDs are hex, not sequential)
  - Only Telegram integer IDs are reliable for gap detection
  - This means WhatsApp will produce 0 deletions from ID analysis — this is **correct and honest**

- [ ] **B4** Fix silent `sqlite3.Error` in WhatsApp message parser
  - File: `forensic/whatsapp/message_parser.py` line 107
  - Add `import logging; logging.getLogger(__name__).error(f"Parse error: {e}")` before `return []`
  - Apply same pattern to contact_parser, group_parser, media_parser if they have the same silent except

- [ ] **B5** Fix `search_repo._get_evidence_ids` ignoring the `app` filter
  - File: `backend/repositories/search_repo.py` lines 444-448
  - Add filter: `Evidence.metadata_["app"].astext == app` when `app in ("whatsapp", "telegram")`
  - This currently returns all evidence IDs regardless of app, causing extra DB round-trips

- [ ] **B6** Fix `analysis_logs.evidence_id` FK constraint if nullable
  - Only apply this fix if **A6 audit** reveals the column is NOT nullable
  - File: `backend/models/models.py`
  - Change: `evidence_id = Column(Integer, ForeignKey("evidence.id"))` → add `nullable=True`

### Frontend Fixes

- [ ] **F1** Fix sidebar navigation (context-aware)
  - File: `frontend/src/components/layout/index.jsx`
  - Move `navItems` inside `Sidebar` component body
  - Derive `activeCaseId` from `useLocation()` via `pathname.match(/\/cases\/(\d+)/)`
  - When `activeCaseId` found: show all 5 case-specific links (enabled)
  - When no `activeCaseId`: show global nav with disabled placeholders
  - Import `LayoutDashboard` from lucide-react

- [ ] **F2** Fix duplicate navigation in CaseDetailPage header
  - File: `frontend/src/pages/CaseDetailPage.jsx` lines 114-145
  - Remove the entire `actions={<div className="flex items-center gap-2">...</div>}` prop from `<Header>`
  - Keep only `breadcrumbs` prop on the Header

- [ ] **F3** Fix broken quick links on DashboardPage
  - File: `frontend/src/pages/DashboardPage.jsx` lines 234-254
  - Change `to={/cases/${caseId}?tab=timeline}` → `to={/cases/${caseId}}`
  - Change `to={/cases/${caseId}?tab=correlation}` → `to={/cases/${caseId}}`
  - These tabs don't exist yet; the links should go somewhere valid

- [ ] **F4** Fix infinite re-render if `loadOverview` is missing `useCallback`
  - Only apply if **A7 audit** confirms the bug exists
  - File: `frontend/src/hooks/useDashboard.js`
  - Wrap `loadOverview` in `useCallback(async (id) => {...}, [])`

- [ ] **F5** Fix reportService GET/POST mismatch
  - Only apply if **A8 audit** confirms the bug exists
  - File: `frontend/src/services/reportService.js`
  - Ensure `getEvidenceSummary`, `getTimelineSummary`, `getDeletedSummary` use `axios.get`

- [ ] **F6** Add null guard for `created_at` date formatting
  - Verify and fix in `CaseListPage.jsx` and `CaseDetailPage.jsx`

---

## Phase 2 — Fix Demo Mode (Backend)

Demo mode is the primary way to test the app without real evidence. It must produce **complete, realistic data** that makes all dashboard sections show real numbers.

### Backend

- [ ] **B7** Fix `DemoData` defaults
  - File: `backend/api/demo.py` lines 17-24
  - Change `has_telegram: bool = False` → `True`
  - Change `message_count: int = 50` → `100`
  - Change `contact_count: int = 10` → `15`
  - Add `case_name: str = Field(default_factory=lambda: f"Demo Case - {datetime.now().strftime('%Y%m%d_%H%M%S')}")` — import `Field` from pydantic

- [ ] **B8** Add `DEMO_MODE` guard to demo endpoint
  - File: `backend/api/demo.py` line 60
  - Add at top of function: `if not settings.demo_mode: raise HTTPException(403, "Demo mode is disabled")`

- [ ] **B9** Create `TimelineEvent` records in demo builder
  - File: `backend/api/demo.py` inside `_create_demo_whatsapp` and `_create_demo_telegram`
  - After saving messages, create one `TimelineEvent` per message with:
    - `case_id`, `evidence_id`, `event_type="message"`, `source_app="whatsapp"/"telegram"`
    - `timestamp=msg.timestamp`
    - `normalized_timestamp=datetime.fromtimestamp(msg.timestamp / 1000, tz=timezone.utc)`
    - `entity_id=str(msg.message_id)`, `entity_type="message"`
    - `description=f"Message: {msg.body[:60]}"`
  - This makes Dashboard's "Timeline Summary" section show actual event counts

- [ ] **B10** Create `DeletedMessage` records in demo builder
  - File: `backend/api/demo.py` inside `_create_demo_whatsapp` and `_create_demo_telegram`
  - After saving messages, create 2-3 `DeletedMessage` records with:
    - Varied `confidence_score` values (0.75, 0.85, 0.60)
    - `detection_method="sequence_gap_analysis"`
  - This makes Dashboard's "Deletions Detected" stat non-zero

---

## Phase 3 — Demo UX (Frontend)

The demo flow needs a proper UI. This is a new component.

### Frontend

- [ ] **F7** Create `DemoModal` component
  - File: `frontend/src/components/demo/DemoModal.jsx` (NEW — does not exist)
  - Create directory `frontend/src/components/demo/` if it doesn't exist
  - Full spec in **FRONTEND.md Section 8.1**
  - State: `{ caseName, hasWhatsApp, hasTelegram, step, progress, errorMsg }`
  - Steps: 9 total, advance every 1.2s while API call is in-flight
  - On success: navigate to `/cases/{case_id}/dashboard`
  - On error: show error message with retry button

- [ ] **F8** Integrate `DemoModal` into HomeScreen
  - File: `frontend/src/App.jsx` (HomeScreen component at bottom of file)
  - Add `demoModalOpen` state
  - "Create Demo Case" button → `setDemoModalOpen(true)`
  - Render `<DemoModal isOpen={demoModalOpen} onClose={() => setDemoModalOpen(false)} />`
  - Remove the existing `handleCreateDemo` function and loading state from the button

---

## Phase 4 — Charts (Frontend)

Visual data representations for the dashboard. Requires installing chart.js.

### Frontend

- [ ] **F9** Install chart.js packages
  - Run in terminal: `cd D:\ArtifactX\frontend && npm install chart.js react-chartjs-2`
  - Verify it doesn't break existing builds: `npm run dev` should still work

- [ ] **F10** Create `MessageVolumeChart` component
  - File: `frontend/src/components/dashboard/MessageVolumeChart.jsx` (NEW)
  - Full spec in **FRONTEND.md Section 8.2**
  - Line chart: WA (emerald) and TG (blue) messages per day
  - Data derived from `overview.recent_events` by grouping by `date(normalized_timestamp)` + `source_app`
  - Add a `buildVolumeData(events)` utility function in the component file

- [ ] **F11** Create `MessageDistributionChart` component
  - File: `frontend/src/components/dashboard/MessageDistributionChart.jsx` (NEW)
  - Full spec in **FRONTEND.md Section 8.3**
  - Doughnut chart: WA vs TG total message counts

- [ ] **F12** Export new charts from dashboard index
  - File: `frontend/src/components/dashboard/index.js`
  - Add exports for `MessageVolumeChart` and `MessageDistributionChart`

- [ ] **F13** Integrate charts into DashboardPage
  - File: `frontend/src/pages/DashboardPage.jsx`
  - Add a new grid row after the 4-stat row (before the "Two Column Layout" section)
  - Row: `MessageDistributionChart` on left, `MessageVolumeChart` on right
  - Only render when `stats.total_messages > 0`

---

## Phase 5 — Validate Forensic Parsers

The forensic engine is the core of the app. These parsers must work correctly on real evidence files.

### Backend / Forensic

- [ ] **B11** Audit and fix `forensic/whatsapp/contact_parser.py`
  - If file doesn't exist: create it with schema-adaptive query (same pattern as `message_parser.py`)
  - If file exists but doesn't handle both legacy (`wa_contacts`) and modern WhatsApp schemas: fix it
  - Return dicts with: `evidence_id`, `jid`, `display_name`, `phone_number`, `status`

- [ ] **B12** Audit and fix `forensic/whatsapp/group_parser.py`
  - Same existence and schema-adaptive check
  - Return dicts with: `evidence_id`, `group_jid`, `subject`, `creator_jid`, `creation_timestamp`

- [ ] **B13** Audit and fix `forensic/whatsapp/media_parser.py`
  - Same existence check
  - Return dicts with: `message_id`, `media_path`, `message_type`

- [ ] **B14** Audit `forensic/telegram/` — all four parsers
  - For each of `detector.py`, `message_parser.py`, `contact_parser.py`, `group_parser.py`:
  - Verify they handle Telegram's schema (`messages`, `users`, `dialogs`, `chats` tables)
  - Fix or create any that are missing or broken

- [ ] **B15** Audit `forensic/timeline/builder.py`
  - Verify `TimelineBuilder.build_timeline_for_case(db, case_id)` queries both WA and TG messages
  - Verify it creates events with `normalized_timestamp` as a Python `datetime` object (not a string or int)
  - Fix if `normalized_timestamp` is not being computed correctly

- [ ] **B16** Audit `forensic/correlation/matcher.py` dataclass field alignment
  - Run a demo case creation, then trigger correlation via `POST /api/correlation/cases/{id}/correlation/build`
  - If it crashes with `AttributeError` or `TypeError`: the dataclass fields don't match what the service provides
  - Fix the dataclass definitions to match the ORM field names

---

## Phase 6 — End-to-End Smoke Test

Test the full application workflow from scratch. Do this after Phases 1-5.

### Backend Smoke Tests

- [ ] **T1** Backend starts without errors
  ```powershell
  $env:PYTHONPATH = "D:\ArtifactX"
  cd D:\ArtifactX\backend
  uvicorn app.main:app --port 8000 --reload
  # → Should print: Application startup complete. No import errors.
  ```

- [ ] **T2** Health endpoint returns demo_mode=true
  ```
  GET http://localhost:8000/api/health
  # → { "status": "ok", "demo_mode": true, ... }
  ```

- [ ] **T3** Demo case creation produces complete data
  ```
  POST http://localhost:8000/api/demo/create-demo-case
  Body: { "case_name": "Test", "has_whatsapp": true, "has_telegram": true }
  # → Verify: response has case_id, WA stats, TG stats (all non-zero)
  # → Verify DB: SELECT COUNT(*) FROM timeline_events WHERE case_id=N → non-zero
  # → Verify DB: SELECT COUNT(*) FROM deleted_messages WHERE case_id=N → 2-3 rows
  ```

- [ ] **T4** Dashboard overview returns all data
  ```
  GET http://localhost:8000/api/cases/{id}/overview
  # → stats.total_messages > 0
  # → stats.total_contacts > 0
  # → timeline_stats.total_events > 0
  # → stats.total_deleted > 0
  ```

- [ ] **T5** Search returns results from demo data
  ```
  GET http://localhost:8000/api/search?case_id={id}&query=meeting
  # → Returns message results
  ```

- [ ] **T6** Report generation produces a PDF file
  ```
  POST http://localhost:8000/api/cases/{id}/reports
  Body: { "report_type": "full" }
  # → Returns filename
  # → Verify file exists at reports/{id}/*.pdf
  ```

### Frontend Smoke Tests

- [ ] **T7** Full demo workflow end-to-end
  1. Open `http://localhost:5173`
  2. Click "Create Demo Case"
  3. `DemoModal` opens with WhatsApp + Telegram checked
  4. Click "Start Demo Analysis"
  5. Progress steps animate, one by one
  6. Redirected to `/cases/{id}/dashboard`
  7. Dashboard shows non-zero stats for messages, contacts, deletions
  8. Charts render (WA + TG data visible)
  9. Timeline Summary section is visible (events > 0)

- [ ] **T8** Sidebar shows case-specific navigation
  - When on dashboard page, sidebar shows: All Cases / Dashboard / Search / Reports / Logs
  - All links are enabled and navigate correctly
  - Header does NOT show duplicate nav buttons

- [ ] **T9** Search page returns results
  - Navigate to Search page
  - Type "meeting" → results appear from WA and TG messages

- [ ] **T10** Reports page works
  - All three summary cards show data
  - "Generate PDF" button creates a report
  - Download link appears

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
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd D:\ArtifactX\frontend
npm install
npm run dev
```

> If Vite uses port 5174 instead of 5173: add `"http://localhost:5174"` to backend CORS `allow_origins` (this is already in B1 fix above).
