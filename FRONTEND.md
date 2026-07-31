# ArtifactX — Frontend: Complete Specification & Audit

> **What this file is:** The definitive truth of the frontend — what exists, what is broken, what must be written or rewritten.  
> Every section states the **current state** and the **required state** if they differ.  
> An AI reading this file should be able to fix every hole without needing any other context.

---

## 1. Stack

| Component | Current | Required |
|-----------|---------|----------|
| Framework | React 18 ✅ | React 18 |
| Language | JavaScript ✅ | JavaScript |
| Styling | Tailwind CSS ✅ | Tailwind CSS |
| Build | Vite ✅ | Vite |
| HTTP | Axios ✅ | Axios |
| Routing | React Router v6 ✅ | React Router v6 |
| Icons | Lucide React ✅ | Lucide React |
| Charts | chart.js + react-chartjs-2 ✅ | chart.js + react-chartjs-2 |
| Date helpers | date-fns ✅ | date-fns |

---

## 2. Vite Config

**Must have API proxy.** Without it, all API calls fail in development because the browser cannot reach `localhost:8000` (or `8080`) from a different port.

**File:** `frontend/vite.config.js`

```javascript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    }
  }
}
```

---

## 3. Architecture & Routing — `frontend/src/App.jsx`

### Current Issues & Overhaul Plan

1. **Broken / Misleading Redirections:** Dashboard links (`?tab=timeline`, `?tab=correlation`) redirect out of place because `CaseDetailPage` does not handle tabs properly.
2. **Redundant Header Navigation:** Header actions duplicate sidebar links.
3. **Unfriendly UX:** Lack of a unified Forensic Workstation container. No interactive message viewer, timeline stream, or court report generator UI.

### Unified Workstation Route Map

All case operations are consolidated under a clean tab-aware or sub-route aware **Forensic Workspace Container** (`CaseWorkspacePage.jsx`):

| Route | Component | Purpose | Status |
|-------|-----------|---------|--------|
| `/` | `HomeScreen` | Landing, quick stats, demo workflow trigger | ✅ Working (needs DemoModal) |
| `/cases` | `CaseListPage` | Case registry, intake, hash search | ✅ Working |
| `/cases/create` | `CaseForm` | Create case & record initial chain of custody | ✅ Working |
| `/cases/:caseId` | `CaseWorkspacePage` | **Unified Workstation Container** with tab navigation | 🔄 Overhauled |
| `/cases/:caseId/dashboard` | `DashboardPage` | Executive Overview, Message Volume & App Distribution Charts | 🔄 Overhauled |
| `/cases/:caseId/evidence` | `EvidencePage` | Ingestion, artifact extraction, EXIF & hash inspector | 🔄 Overhauled |
| `/cases/:caseId/chat` | `ChatViewerPage` | Interactive WA/TG chat message thread viewer with deletion tags | 🆕 New View |
| `/cases/:caseId/timeline` | `TimelinePage` | Reconstructed chronological event stream & density histogram | 🔄 Overhauled |
| `/cases/:caseId/correlation` | `CorrelationPage` | Cross-platform entity resolution & time correlation matrix | 🔄 Overhauled |
| `/cases/:caseId/deletions` | `DeletionsPage` | Sequence/time gap detector & confidence scoring breakdown | 🔄 Overhauled |
| `/cases/:caseId/reports` | `ReportsPage` | Court-Ready PDF generator, in-app report history tracker, & direct download | 🔄 Overhauled |
| `/cases/:caseId/logs` | `LogsPage` | Chain-of-custody audit log & system diagnostics | ✅ Working |

---

## 4. Design System — `frontend/src/index.css`

The Tailwind dark forensic workstation theme:
- `forensic-950` (`#0b0f17`) — deep background
- `forensic-900` (`#111827`) — card & container surfaces
- `forensic-800` (`#1f2937`) — borders, dividers, dark inputs
- `accent-cyan` (`#06b6d4`) — primary CTA, active tabs, cryptographic hashes
- `accent-emerald` (`#10b981`) — WhatsApp data, verified integrity (`VERIFIED_INTACT`)
- `accent-blue` (`#3b82f6`) — Telegram data, general media
- `accent-violet` (`#8b5cf6`) — Cross-platform correlations, entity links
- `accent-rose` (`#f43f5e`) — Deleted messages, sequence gaps, tamper warnings (`HASH_MISMATCH`)
- `accent-amber` (`#f59e0b`) — Warnings, unverified evidence, missing metadata

**Typography:**
- `Inter` — body & UI elements
- `JetBrains Mono` — SHA-256/MD5/SHA-1 hashes, entity IDs, timestamps, hex viewer

---

## 5. Layout & Navigation System — `frontend/src/components/layout/`

### Sidebar (`Sidebar.jsx`)
- Must derive active `caseId` from `useLocation()`.
- When in a case context (`/cases/:caseId/*`), render active case workflow links:
  - Overview (`/cases/:caseId/dashboard`)
  - Evidence & Artifacts (`/cases/:caseId/evidence`)
  - Chat Viewer (`/cases/:caseId/chat`)
  - Chronological Timeline (`/cases/:caseId/timeline`)
  - Evidence Correlations (`/cases/:caseId/correlation`)
  - Deleted Messages (`/cases/:caseId/deletions`)
  - Court Reports (`/cases/:caseId/reports`)
  - Custody Logs (`/cases/:caseId/logs`)
- When not in case context: show Case List link enabled, disabled placeholders for case tools.

### Header (`Header.jsx`)
- Displays breadcrumbs, active case title, evidence verification status badge (`VERIFIED_INTACT`), and active investigator profile.
- **Rule:** Do NOT put duplicate navigation links in header actions. Header actions are strictly for primary page triggers (e.g. "Export Report", "Re-Verify Hashes", "Ingest Evidence").

### Guided Stepper Header (`ForensicWorkflowStepper.jsx`)
- Rendered inside `CaseWorkspacePage.jsx`.
- 4-stage progression indicator:
  1. **Ingest & Hash** (Upload ZIP/DB, SHA-256 manifest)
  2. **Extract & Parse** (WhatsApp `msgstore.db`, Telegram `cache4.db`, EXIF)
  3. **Analyze & Correlate** (Timeline, Chat viewer, Correlations, Deletions)
  4. **Court Export** (Generate Court-Ready PDF with Direct Streaming & In-App History Tracker)

---

## 6. Page Specifications

### 6.1 `HomeScreen.jsx`
- Hero dashboard introducing ArtifactX Digital Forensics Workstation.
- "Create Demo Case" button opens `DemoModal.jsx` (Section 8.1).
- Quick Stats cards showing total cases, analyzed messages, verified hash integrity rate.

### 6.2 `CaseListPage.jsx`
- Case management table showing Case Name, Investigator, Created Date, Evidence Count, Cryptographic Hash Status, Actions (View, Delete).
- Null-guard on `created_at` dates: `case.created_at ? new Date(case.created_at).toLocaleDateString() : '—'`.

### 6.3 `CaseWorkspacePage.jsx` (Container)
- Master workstation wrapper for all case sub-views.
- Top bar with `ForensicWorkflowStepper`.
- Tab bar for seamless switching between Dashboard, Evidence, Chat, Timeline, Correlations, Deletions, Court Reports, Logs without page reloads.

### 6.4 `DashboardPage.jsx`
- Executive forensic overview:
  - 4 Key Metrics: Total Messages, Parsed Contacts, Correlated Entities, Detected Deletions.
  - `MessageDistributionChart` (Doughnut: WhatsApp vs Telegram split).
  - `MessageVolumeChart` (Line chart: Messages per day over time).
  - Recent Events Feed & Integrity Verification Status widget.

### 6.5 `EvidencePage.jsx`
- Artifact Extraction & Metadata Analysis workstation:
  - Drag-and-drop evidence ingestion (`EvidenceUploader.jsx`).
  - Extracted files tree/table with SHA-256, MD5, SHA-1 cryptographic hashes, file size, MIME type.
  - EXIF metadata slide-out panel (`ExifMetadataDrawer.jsx`) showing camera model, timestamp, GPS coordinates on map.
  - SQLite table inspector for WhatsApp (`msgstore.db`) and Telegram (`cache4.db`).

### 6.6 `ChatViewerPage.jsx` (NEW)
- Interactive Chat Message Thread Viewer:
  - Left pane: Contact / Group list with app badges (WhatsApp green, Telegram blue) and message counts.
  - Center pane: Interactive chat bubble stream:
    - Sender name / JID / handle
    - Message body text
    - Formatted timestamp
    - Attachment preview (images, audio, video) with EXIF inspection button
    - **Deleted Message Badge:** `[DELETED MESSAGE DETECTED]` with sequence gap info
  - Right pane: Selected message raw metadata & cryptographic signature.

### 6.7 `TimelinePage.jsx`
- Reconstructed Chronological Event Stream:
  - Time density histogram chart (chart.js bar chart).
  - Filter bar: Date Range picker, App Selector (All, WhatsApp, Telegram), Search Query, Event Type (Message, Call, Media, File Creation).
  - Event Stream Cards with timestamp, app badge, sender/receiver, message excerpt, hash fingerprint.

### 6.8 `CorrelationPage.jsx`
- Cross-Platform Evidence Correlation Engine:
  - Entity Resolution Table: Maps phone numbers, JIDs, and Telegram handles across platforms.
  - Cross-App Message Threads: Correlates WhatsApp & Telegram messages exchanged between same entities within time windows.
  - Time Window Matrix: Identifies simultaneous activity across multiple accounts.

### 6.9 `DeletionsPage.jsx`
- Sequence & Time Gap Anomaly Detector:
  - Summary stats: Total Deletions Detected, High Confidence Deletions, Missing Message Estimate.
  - Deletion Gap List: Source App, Chat JID, Missing ID Range (e.g. MSG #102 to MSG #108), Estimated Time Gap, Confidence Score (e.g. 92%), Detection Method explanation.
  - Forensic Impact Notes.

### 6.10 `ReportsPage.jsx` (Court-Ready Reports & In-App Report Tracker)
- Professional Legal Report Generator & Tracker:
  - Report Configuration: Select sections (Executive Summary, Chain of Custody, Hash Verification Manifest, Evidence Findings, Timeline, Deletions, Correlated Entities).
  - Investigator Inputs: Lead Analyst Name, Agency/Dept, Case Notes, Sworn Integrity Declaration.
  - Live PDF Previewer (`ReportPdfPreview.jsx`).
  - **Direct Download Execution:** Calls API with `{ responseType: 'blob' }`, creating a temporary Blob URL in memory to trigger instant browser file download — **zero disk storage in the project workspace directory**.
  - **In-App Report History Tracker Table:** Renders historical log of generated reports for the case (Report ID, Type, Lead Analyst, Generation Date, Verification SHA-256 Hash of report bytes, Download / Re-generate button).

### 6.11 `LogsPage.jsx`
- Complete Chain of Custody Audit Log:
  - Log entries for file upload, hash calculation, analysis execution, report generation, investigator access.
  - Filterable by log severity (INFO, WARNING, ERROR).

---

## 7. Services — `frontend/src/services/`

All API requests proxy through `/api` (Vite proxy to `http://localhost:8080`).

- `caseService.js` — Case CRUD operations.
- `evidenceService.js` — File upload, extracted file list, hash verification, EXIF inspection.
- `chatService.js` — WhatsApp/Telegram message threads, chat list, message details.
- `timelineService.js` — Timeline event stream, time histogram data, export.
- `correlationService.js` — Entity correlation triggers, entity mapping list.
- `deletedService.js` — Deletion detection trigger, deletion gap records.
- `reportService.js` — Summary stats (GET requests), PDF streaming download handler (`responseType: 'blob'`), report history tracker fetching (`GET /api/cases/{id}/reports/history`).
- `demoService.js` — Demo case creation with full config (`has_whatsapp`, `has_telegram`, `message_count`).

---

## 8. Essential Components

### 8.1 `DemoModal.jsx` (`components/demo/DemoModal.jsx`)
- Props: `{ isOpen, onClose }`
- State: Config form inputs -> 9-step progress bar -> Done / Nav to Case Workspace -> Error display.

### 8.2 `MessageVolumeChart.jsx` & `MessageDistributionChart.jsx`
- Built using `react-chartjs-2`.
- Dark theme styled with grid colors `#1f2937` and custom tooltips.

### 8.3 `EvidenceHashBadge.jsx` (`components/evidence/EvidenceHashBadge.jsx`)
- Renders SHA-256 hash in JetBrains Mono cyan text.
- Click to copy hash with toast notification.
- Displays integrity state: `VERIFIED` (emerald), `UNVERIFIED` (amber), `TAMPERED` (rose).

### 8.4 `ExifMetadataDrawer.jsx` (`components/evidence/ExifMetadataDrawer.jsx`)
- Slide-out drawer displaying image preview, camera make/model, ISO, aperture, software, creation date, GPS coordinates with OpenStreetMap link.

### 8.5 `ReportPdfPreview.jsx` (`components/reports/ReportPdfPreview.jsx`)
- Render court report layout preview showing official cover header, custody log table, evidence hash table, and sworn analyst signature block.

---

## 9. Custom Hooks — `frontend/src/hooks/`

- `useCases.js` — Case list, active case state, creation, deletion.
- `useDashboard.js` — Wraps `loadOverview` in `useCallback` to prevent infinite re-render loops.
- `useChat.js` — Active chat selection, message pagination, search within thread.
- `useTimeline.js` — Timeline event fetching, filtering, date bounds.
- `useCorrelation.js` — Correlation matrix state & entity matching actions.
- `useDeletions.js` — Deletion detection execution & gap list state.
- `useReports.js` — PDF generation streaming download status, Blob handler, & in-app report history tracker state.

---

## 10. Complete Bug Register

| ID | Severity | File | Description | Required Fix |
|----|----------|------|-------------|--------------|
| F1 | HIGH | `components/layout/index.jsx` | Sidebar nav is static — disabled links regardless of route | Make `navItems` dynamic using `useLocation()` and active `caseId` |
| F2 | HIGH | `pages/CaseDetailPage.jsx` | Duplicate navigation in header actions | Remove `actions` prop from `<Header>` |
| F3 | HIGH | `App.jsx` | Demo creation has no UX — silent API call + sudden redirect | Build and integrate `DemoModal.jsx` |
| F4 | MEDIUM | `pages/DashboardPage.jsx` | Quick links `?tab=timeline` redirect out of place | Update routes to `/cases/${caseId}/timeline` & `/cases/${caseId}/correlation` |
| F5 | MEDIUM | `hooks/useDashboard.js` | `loadOverview` missing `useCallback` causing infinite render loop | Wrap in `useCallback(async (id) => {...}, [])` |
| F6 | LOW | `pages/CaseListPage.jsx` | Date formatting crashes if `created_at` is null | Add null guard check before `toLocaleDateString()` |
| F7 | MISSING | `components/demo/DemoModal.jsx` | Demo modal component missing | Build per Section 8.1 spec |
| F8 | MISSING | `components/dashboard/MessageVolumeChart.jsx` | Chart component missing | Build using chart.js |
| F9 | MISSING | `components/dashboard/MessageDistributionChart.jsx` | Chart component missing | Build using chart.js |
| F10 | MISSING | `pages/ChatViewerPage.jsx` | Chat message thread viewer missing | Build interactive chat viewer per Section 6.6 |
| F11 | MISSING | `components/evidence/ExifMetadataDrawer.jsx` | EXIF metadata slide-out panel missing | Build EXIF inspector drawer |
| F12 | MISSING | `components/reports/ReportPdfPreview.jsx` | Court report preview component missing | Build court report previewer |

---

## 11. Required Audit Tasks

| File | Verification Criteria |
|------|-----------------------|
| `frontend/vite.config.js` | API proxy configured for `/api` targetting `http://localhost:8080` |
| `frontend/src/services/reportService.js` | Summary endpoints use `axios.get`; PDF export uses `responseType: 'blob'` for direct download |
| `frontend/src/components/evidence/EvidenceUploader.jsx` | Multi-file drag & drop, upload progress bar, SHA-256 display |
| `frontend/src/components/whatsapp/WhatsAppAnalysis.jsx` | Renders message threads, contacts, group tables |
| `frontend/src/components/telegram/TelegramAnalysis.jsx` | Renders Telegram messages, contacts, dialogs |
| `frontend/src/pages/ReportsPage.jsx` | Court report inputs, PDF section toggles, in-app report tracker, streaming download handler |

---

## 12. Dependencies (`package.json`)

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-router-dom": "^6.24",
    "axios": "^1.7",
    "date-fns": "^3.0",
    "lucide-react": "^0.400",
    "tailwindcss": "^3.4",
    "vite": "^5.4",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0"
  }
}
```
