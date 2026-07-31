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

1. **Eliminated Redundant & Senseless Buttons:** Removed all duplicate "Quick Actions" cards, misleading "Full Timeline" / "Correlation Graph" / "Case Details" buttons on dashboard, and confusing magnifying glass buttons next to case items in the case registry.
2. **Unified Navigation:** All case navigation is cleanly handled by the context-aware sidebar and workstation tabs.
3. **Forensic Workstation Container:** Case tools are consolidated under `CaseWorkspacePage.jsx`.

### Unified Workstation Route Map

All case operations are consolidated under a clean tab-aware or sub-route aware **Forensic Workspace Container** (`CaseWorkspacePage.jsx`):

| Route | Component | Purpose | Status |
|-------|-----------|---------|--------|
| `/` | `HomeScreen` | Landing, quick stats, demo workflow trigger | ✅ Working (needs DemoModal) |
| `/cases` | `CaseListPage` | Case registry, intake, hash search (clean Open Case & Delete actions) | 🔄 Overhauled |
| `/cases/create` | `CaseForm` | Create case & record initial chain of custody | ✅ Working |
| `/cases/:caseId` | `CaseWorkspacePage` | **Unified Workstation Container** with tab navigation | 🔄 Overhauled |
| `/cases/:caseId/dashboard` | `DashboardPage` | Executive Overview, Message Volume & App Distribution Charts (no redundant buttons) | 🔄 Overhauled |
| `/cases/:caseId/evidence` | `EvidencePage` | Ingestion, artifact extraction, EXIF & hash inspector | 🔄 Overhauled |
| `/cases/:caseId/chat` | `ChatViewerPage` | Interactive WA/TG chat message thread viewer with deletion tags & sentiment overlays | 🔄 Overhauled |
| `/cases/:caseId/timeline` | `TimelinePage` | Reconstructed chronological event stream & density histogram | 🔄 Overhauled |
| `/cases/:caseId/correlation` | `CorrelationPage` | Cross-platform entity resolution & time correlation matrix | 🔄 Overhauled |
| `/cases/:caseId/deletions` | `DeletionsPage` | Sequence/time gap detector & confidence scoring breakdown | 🔄 Overhauled |
| `/cases/:caseId/reports` | `ReportsPage` | Court-Ready PDF generator, in-app report history tracker, & direct download (AI excluded) | 🔄 Overhauled |
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
- `accent-violet` (`#8b5cf6`) — Cross-platform correlations, entity links, AI Assistant badge
- `accent-rose` (`#f43f5e`) — Deleted messages, sequence gaps, tamper warnings (`HASH_MISMATCH`), high suspicion score
- `accent-amber` (`#f59e0b`) — Warnings, unverified evidence, aggressive/deceptive chat sentiment

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

### Header (`Header.jsx`)
- Displays breadcrumbs, active case title, evidence verification status badge (`VERIFIED_INTACT`), and active investigator profile.
- **Rule:** Do NOT put duplicate navigation links in header actions. Header actions are strictly for primary page triggers (e.g. "Export Report", "Re-Verify Hashes", "Ingest Evidence").

---

## 6. Page Specifications

### 6.1 `HomeScreen.jsx`
- Hero dashboard introducing ArtifactX Digital Forensics Workstation.
- "Create Demo Case" button opens `DemoModal.jsx` (Section 8.1).
- Quick Stats cards showing total cases, analyzed messages, verified hash integrity rate.

### 6.2 `CaseListPage.jsx`
- Case management table showing Case Name, Investigator, Created Date, Evidence Count, Cryptographic Hash Status.
- **Clean Action Bar:** Each case item card features a clean `Open Case` primary button and a `Delete Case` icon button — redundant magnifying glass icons and duplicate "View Details" links are removed.
- Null-guard on `created_at` dates: `case.created_at ? new Date(case.created_at).toLocaleDateString() : '—'`.

### 6.3 `CaseWorkspacePage.jsx` (Container)
- Master workstation wrapper for all case sub-views.
- Top bar with `ForensicWorkflowStepper`.
- Docked/Floating `ForensicAssistantDrawer.jsx` (AI Copilot chat + sentiment overlay trigger).
- Tab bar for seamless switching between Dashboard, Evidence, Chat, Timeline, Correlations, Deletions, Court Reports, Logs without page reloads.

### 6.4 `DashboardPage.jsx`
- Executive forensic overview:
  - 4 Key Metrics: Total Messages, Parsed Contacts, Correlated Entities, Detected Deletions.
  - `MessageDistributionChart` (Doughnut: WhatsApp vs Telegram split).
  - `MessageVolumeChart` (Line chart: Messages per day over time).
  - Recent Events Feed & Integrity Verification Status widget.
  - **No Redundant Quick Links:** Removed misleading bottom buttons (`Full Timeline`, `Correlation Graph`, `Case Details`).

### 6.5 `EvidencePage.jsx`
- Artifact Extraction & Metadata Analysis workstation:
  - Drag-and-drop evidence ingestion (`EvidenceUploader.jsx`).
  - Extracted files tree/table with SHA-256, MD5, SHA-1 cryptographic hashes, file size, MIME type.
  - EXIF metadata slide-out panel (`ExifMetadataDrawer.jsx`) showing camera model, timestamp, GPS coordinates on map.
  - SQLite table inspector for WhatsApp (`msgstore.db`) and Telegram (`cache4.db`).

### 6.6 `ChatViewerPage.jsx`
- Interactive Chat Message Thread Viewer:
  - Left pane: Contact / Group list with app badges (WhatsApp green, Telegram blue) and message counts.
  - Center pane: Interactive chat bubble stream with deletion badges and optional sentiment overlays.
  - Right pane: Selected message raw metadata, cryptographic signature, and investigator notes.

### 6.7 `TimelinePage.jsx`
- Reconstructed Chronological Event Stream with time density histogram chart.

### 6.8 `CorrelationPage.jsx`
- Cross-Platform Evidence Correlation Engine.

### 6.9 `DeletionsPage.jsx`
- Sequence & Time Gap Anomaly Detector.

### 6.10 `ReportsPage.jsx` (Court-Ready Reports & In-App Report Tracker)
- Professional Legal Report Generator & Tracker with direct streaming downloads and database metadata tracking (AI copilot output strictly excluded).

### 6.11 `LogsPage.jsx`
- Complete Chain of Custody Audit Log.

---

## 7. Services — `frontend/src/services/`

- `caseService.js`, `evidenceService.js`, `chatService.js`, `timelineService.js`, `correlationService.js`, `deletedService.js`, `reportService.js`, `assistantService.js`, `demoService.js`.

---

## 8. Essential Components

- `DemoModal.jsx`, `MessageVolumeChart.jsx`, `MessageDistributionChart.jsx`, `EvidenceHashBadge.jsx`, `ExifMetadataDrawer.jsx`, `ForensicAssistantDrawer.jsx`, `ReportPdfPreview.jsx`.

---

## 9. Custom Hooks — `frontend/src/hooks/`

- `useCases.js`, `useDashboard.js`, `useChat.js`, `useTimeline.js`, `useCorrelation.js`, `useDeletions.js`, `useReports.js`, `useAiAssistant.js`.

---

## 10. Complete Bug Register

| ID | Severity | File | Description | Required Fix |
|----|----------|------|-------------|--------------|
| F1 | HIGH | `components/layout/index.jsx` | Sidebar nav static — disabled links | Make `navItems` dynamic using `useLocation()` and active `caseId` |
| F2 | HIGH | `pages/CaseDetailPage.jsx` | Duplicate navigation & Quick Actions card | Removed duplicate header actions & removed bottom Quick Actions card |
| F3 | HIGH | `App.jsx` | Demo creation missing UX | Integrate `DemoModal.jsx` |
| F4 | MEDIUM | `pages/DashboardPage.jsx` | Redundant Quick Links buttons at bottom | Removed bottom Quick Links section |
| F5 | MEDIUM | `hooks/useDashboard.js` | `loadOverview` missing `useCallback` | Wrap in `useCallback` |
| F6 | LOW | `pages/CaseListPage.jsx` | Confusing magnifying glass button & date formatting | Cleaned up card actions to `Open Case` & `Delete Case` |

---

## 11. Required Audit Tasks

| File | Verification Criteria |
|------|-----------------------|
| `frontend/src/pages/CaseListPage.jsx` | Confusing magnifying glass button removed; clean Open Case & Delete actions |
| `frontend/src/pages/CaseDetailPage.jsx` | Redundant Quick Actions card removed |
| `frontend/src/pages/DashboardPage.jsx` | Redundant Quick Links buttons removed |

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
