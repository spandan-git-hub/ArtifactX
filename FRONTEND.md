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
| Charts | NOT INSTALLED ❌ | chart.js + react-chartjs-2 |
| Date helpers | date-fns ✅ | date-fns |

---

## 2. Vite Config

**Must have API proxy.** Without it, all API calls fail in development because the browser cannot reach `localhost:8000` from a different port.

**File:** `frontend/vite.config.js`

```javascript
// Required:
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

**Verify this exists.** If missing, add it.

---

## 3. Routing — `frontend/src/App.jsx`

**Current state:** All routes defined and wired. ✅

| Route | Component | Status |
|-------|-----------|--------|
| `/` | `HomeScreen` (inline in App.jsx) | ✅ Working |
| `/cases` | `CaseListPage` | ✅ Working |
| `/cases/create` | `CaseForm` | ✅ Working |
| `/cases/:id` | `CaseDetailPage` | ✅ Working |
| `/cases/:id/edit` | `CaseForm` | ✅ Working |
| `/cases/:caseId/dashboard` | `DashboardPage` | ✅ Working |
| `/cases/:caseId/search` | `SearchPage` | ✅ Working |
| `/cases/:caseId/reports` | `ReportsPage` | ✅ Working |
| `/cases/:caseId/logs` | `LogsPage` | ✅ Working |

**Bug — HomeScreen demo button:** The "Create Demo Case" button fires an API call immediately with no UX. User sees the button spin and then a redirect with no explanation of what happened. Needs a `DemoModal` component (see Section 8).

---

## 4. Design System — `frontend/src/index.css`

**Current state:** Fully implemented and correct. ✅

The Tailwind dark forensic theme is complete:
- 407 lines of base/component/utility layers
- All component classes exist: `.card`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.badge-*`, `.nav-item`, `.data-table`, `.metric-card`, `.alert-*`, `.animate-in`, `.stagger-children`, `.text-gradient`, `.hash-text`, etc.
- Custom scrollbar, `::selection`, focus rings defined
- Keyframe animations: `fadeIn`, `slideUp`, `slideDown`, `pulse-soft`

**No fix required.**

**Color system** (from `tailwind.config.js`):
- `forensic-950/900/800/700/600/500/400/300/100` — background + text hierarchy
- `accent-cyan` — primary (CTAs, active links)
- `accent-emerald` — success, WhatsApp
- `accent-blue` — Telegram
- `accent-amber` — warnings, archived
- `accent-rose` — errors, danger, deletions
- `accent-violet` — correlations, logs

**Typography:**
- `Inter` — body (Google Fonts)
- `JetBrains Mono` — monospace (hashes, IDs, data)

---

## 5. Layout — `frontend/src/components/layout/index.jsx`

### Sidebar (lines 16–95)

**Current state — broken navigation:**

The `navItems` array is defined as a **static constant** (lines 16–21):
```javascript
const navItems = [
  { path: '/cases', icon: FolderKanban, label: 'Cases', exact: true },
  { path: '/search', icon: Search, label: 'Search', disabled: true },     // always disabled
  { path: '/reports', icon: FileText, label: 'Reports', disabled: true },  // always disabled
  { path: '/logs', icon: ClipboardList, label: 'Logs', disabled: true },   // always disabled
];
```

This means: **when a user is on `/cases/5/dashboard`, the sidebar still shows Search/Reports/Logs as disabled links**. The sidebar has no awareness of what case is currently active.

**Required fix — context-aware sidebar:**

Move `navItems` logic inside the `Sidebar` component and derive `caseId` from `useLocation()`:

```javascript
const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  
  // Extract caseId from any case-specific route
  const caseIdMatch = location.pathname.match(/\/cases\/(\d+)/);
  const activeCaseId = caseIdMatch ? caseIdMatch[1] : null;

  const navItems = activeCaseId ? [
    { path: '/cases', icon: FolderKanban, label: 'All Cases' },
    { path: `/cases/${activeCaseId}/dashboard`, icon: LayoutDashboard, label: 'Dashboard' },
    { path: `/cases/${activeCaseId}/search`, icon: Search, label: 'Search' },
    { path: `/cases/${activeCaseId}/reports`, icon: FileText, label: 'Reports' },
    { path: `/cases/${activeCaseId}/logs`, icon: ClipboardList, label: 'Logs' },
  ] : [
    { path: '/cases', icon: FolderKanban, label: 'Cases' },
    { path: '#', icon: Search, label: 'Search', disabled: true },
    { path: '#', icon: FileText, label: 'Reports', disabled: true },
    { path: '#', icon: ClipboardList, label: 'Logs', disabled: true },
  ];

  // Active detection: exact match for case-context items, prefix for global
  const isActive = (path) => {
    if (path === '#') return false;
    return location.pathname === path || (path !== '/cases' && location.pathname.startsWith(path));
  };
  
  // ... rest of render unchanged
};
```

**Also add `LayoutDashboard` to the imports at the top of this file.**

### Header (lines 97–129)

**Current state:** Working. Accepts `breadcrumbs` array and `actions` slot. ✅

**Bug in `CaseDetailPage`:** The Header's `actions` prop is used to show Dashboard/Search/Reports/Logs nav buttons (lines 114–145 of CaseDetailPage). This duplicates the sidebar navigation and clutters the header. After the sidebar is made context-aware, these header action buttons are redundant.

**Fix required in `CaseDetailPage.jsx` lines 114–146:** Remove the `actions={...}` prop from the `<Header>` call. The header should only show breadcrumbs in this page.

### Layout (lines 131–144)

**Current state:** Working. Offsets content by sidebar width. ✅

---

## 6. Pages

### HomeScreen (inline in `App.jsx`)

**Current state:** Works. Has "Access Dashboard" and "Create Demo Case" buttons. Loading state exists.

**Bug — silent demo creation:** `handleCreateDemo` calls `demoService.createDemoCase(...)` and immediately redirects on success with no staged UX. User has no visibility into what's being created.

**Required:** `DemoModal` component (see Section 8.1). The HomeScreen should:
1. On "Create Demo Case" click → set `demoModalOpen = true`
2. The `DemoModal` handles the rest (config input, API call, progress, redirect)

### CaseListPage

**Current state:** Working. Lists cases, "New Case" button, delete with confirm. ✅

**Minor bug:** If `case.created_at` is null (shouldn't happen but defensive check needed):
```javascript
// CURRENT (crashes on null):
new Date(case.created_at).toLocaleDateString()

// REQUIRED:
case.created_at ? new Date(case.created_at).toLocaleDateString('en-US', { 
  year: 'numeric', month: 'short', day: 'numeric' 
}) : '—'
```
Verify this null guard is present. If not, add it.

### CaseDetailPage

**Current state:** Working. Accordion sections for evidence, WhatsApp analysis, Telegram analysis. Quick Actions card at bottom.

**Bug:** Header actions duplicate navigation (see Section 5). Remove them.

**No other bugs found.**

### DashboardPage

**Current state:** Fully implemented (260 lines). Renders stats, app breakdown, correlation summary, recent events, timeline summary. All data comes from `useCaseOverview()`.

**Bug — "Full Timeline" and "Correlation Graph" quick links (lines 234–254):**
```javascript
// CURRENT (broken — adds a ?tab= query param that CaseDetailPage doesn't read):
to={`/cases/${caseId}?tab=timeline`}
to={`/cases/${caseId}?tab=correlation`}

// REQUIRED (correct — these sections don't exist in CaseDetailPage currently,
// keep links to evidence upload until timeline/correlation tabs are built):
to={`/cases/${caseId}`}
```
Or: add tab reading to `CaseDetailPage` (but that's scope expansion). For now, fix to valid routes.

**Missing features (NOT bugs — these are new components to build):**
- `MessageVolumeChart` — line chart of messages per day (requires chart.js install)
- `MessageDistributionChart` — doughnut chart WA vs TG split (requires chart.js install)

### SearchPage

**Current state:** Fully implemented. Uses `useGlobalSearch()`. SearchBar + SearchResults components. ✅

**No bugs found.**

### ReportsPage

**Needs audit** — verify the page file exists at `frontend/src/pages/ReportsPage.jsx` with:
- Left col: `ReportPanel` component
- Right col: three summary cards calling summary APIs
- All three summary API calls use GET (not POST)

### LogsPage

**Current state:** Implemented. Passes `caseId` to `LogsViewer`. ✅

**No bugs found.**

---

## 7. Services — `frontend/src/services/`

**All services use:** `const API_BASE = '/api'` proxied by Vite to `http://localhost:8000`.

### `demoService.js`

**Audit needed** — Verify it calls `POST /api/demo/create-demo-case` with the correct body shape:
```javascript
{
  case_name: string,
  has_whatsapp: boolean,
  has_telegram: boolean,  // must be true by default
  message_count: number,
  contact_count: number
}
```
If `has_telegram` is hardcoded to `false`, change to `true`.

### `caseService.js`, `evidenceService.js`, `searchService.js`, `logService.js`, `dashboardService.js`, `whatsappService.js`, `telegramService.js`, `reportService.js`

**All assumed working.** No bugs found in the API routing or method choices.

**Verify one specific thing in `reportService.js`:** The summary fetching functions must use `GET`, not `POST`. A previous bug report mentioned POST/GET mismatch — verify this is fixed:
```javascript
// Required:
getEvidenceSummary: (caseId) => axios.get(`${API_BASE}/cases/${caseId}/reports/summary`),
getTimelineSummary: (caseId) => axios.get(`${API_BASE}/cases/${caseId}/reports/timeline`),
getDeletedSummary: (caseId) => axios.get(`${API_BASE}/cases/${caseId}/reports/deleted`),
```

---

## 8. Components — New Ones Required

### 8.1 `DemoModal` — `frontend/src/components/demo/DemoModal.jsx`

**Status:** Does NOT exist. Must be created.

**Specification:**
```
Props: { isOpen: bool, onClose: () => void }
State:
  - caseName: string (default: `Demo Case - ${Date.now()}`)
  - hasWhatsApp: bool (default: true)
  - hasTelegram: bool (default: true)
  - step: 'idle' | 'running' | 'done' | 'error'
  - progress: number (0 to STEPS.length)
  - errorMsg: string | null
```

**Progress steps** (shown sequentially with ~1.2s delay each):
```javascript
const STEPS = [
  'Creating case...',
  'Setting up WhatsApp evidence...',
  'Generating message history...',
  'Extracting contact book...',
  'Setting up Telegram evidence...',
  'Generating Telegram messages...',
  'Building timeline...',
  'Detecting deleted messages...',
  'Finalizing analysis...',
];
```

**Behavior:**
1. User fills case name, checks WhatsApp/Telegram
2. Click "Start Demo Analysis" → `step = 'running'`
3. Call `demoService.createDemoCase({ case_name, has_whatsapp, has_telegram, message_count: 100, contact_count: 15 })`
4. While API call is in flight, advance `progress` every 1.2s using `setInterval`
5. When API resolves (success): clear interval, set `progress = STEPS.length`, set `step = 'done'`
6. After 600ms delay: navigate to `/cases/{case_id}/dashboard`
7. When API resolves (error): clear interval, set `step = 'error'`, set `errorMsg`

**UI structure:**
```jsx
<Modal backdrop>
  <div class="card max-w-md mx-auto">
    {step === 'idle' && <ConfigForm />}
    {step === 'running' && <ProgressList steps={STEPS} progress={progress} />}
    {step === 'done' && <SuccessState />}
    {step === 'error' && <ErrorState message={errorMsg} onRetry={reset} />}
  </div>
</Modal>
```

**Progress list item style:**
- Completed: `text-accent-emerald` + checkmark icon
- Current: `text-accent-cyan` + spinning Loader2 icon
- Pending: `text-forensic-500`

### 8.2 `MessageVolumeChart` — `frontend/src/components/dashboard/MessageVolumeChart.jsx`

**Status:** Does NOT exist. Must be created after chart.js is installed.

**Install:**
```bash
cd frontend && npm install chart.js react-chartjs-2
```

**Specification:**
```
Props: { data: [{ date: string, whatsapp: number, telegram: number }] }
```

**Implementation:**
```javascript
import { Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js';

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const chartData = {
  labels: data.map(d => d.date),
  datasets: [
    {
      label: 'WhatsApp',
      data: data.map(d => d.whatsapp),
      borderColor: '#10b981',   // accent-emerald
      backgroundColor: '#10b98115',
      tension: 0.4,
    },
    {
      label: 'Telegram',
      data: data.map(d => d.telegram),
      borderColor: '#3b82f6',   // accent-blue
      backgroundColor: '#3b82f615',
      tension: 0.4,
    }
  ]
};

// Chart.js options must set dark background, no grid lines, custom font colors
const options = {
  responsive: true,
  scales: {
    x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } },
    y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }
  },
  plugins: { legend: { labels: { color: '#d1d5db' } } }
};
```

**Data source:** Derive from `overview.recent_events` by grouping events by date and `source_app`. Add a `buildChartData(events)` utility function.

### 8.3 `MessageDistributionChart` — `frontend/src/components/dashboard/MessageDistributionChart.jsx`

**Status:** Does NOT exist. Must be created with chart.js.

**Specification:**
```
Props: { whatsappCount: number, telegramCount: number }
```

**Implementation:**
```javascript
import { Doughnut } from 'react-chartjs-2';
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js';

Chart.register(ArcElement, Tooltip, Legend);

const chartData = {
  labels: ['WhatsApp', 'Telegram'],
  datasets: [{
    data: [whatsappCount, telegramCount],
    backgroundColor: ['#10b981', '#3b82f6'],
    borderColor: ['#065f46', '#1e40af'],
    borderWidth: 2,
  }]
};
```

---

## 9. Hooks — `frontend/src/hooks/`

### `useCases.js`

**Current state:** Fully working. Loads on mount, provides CRUD methods. ✅

**Minor issue:** No `loadCases` call is made after `createCase`/`updateCase`/`deleteCase` succeeds for the list page. State is updated optimistically in-place (e.g., `setCases(prev => [...prev, newCase])`). This is correct behavior — no fix needed.

### `useDashboard.js`

**Audit needed** — Verify `useCaseOverview()` hook:
- Exposes `{ overview, loading, error, loadOverview }`
- `loadOverview(caseId)` calls `GET /api/cases/{id}/overview`
- Does NOT trigger a re-fetch loop (`loadOverview` must be stable with `useCallback`)

**If `loadOverview` is NOT wrapped in `useCallback`, it causes an infinite re-render loop** because `DashboardPage` has it in `useEffect`'s dependency array (line 31 of DashboardPage.jsx).

**Required (if not already done):**
```javascript
const loadOverview = useCallback(async (caseId) => {
  // ... fetch logic
}, []);  // empty deps = stable reference
```

### `useSearch.js`

**Audit needed** — Verify `useGlobalSearch()` hook exposes: `{ results, loading, error, query, search, clear }`.

### `useWhatsApp.js`, `useTelegram.js`

**Audit needed** — Verify these hooks correctly call `analyze` endpoint and fetch results, with `loading` state per operation.

---

## 10. Complete Bug Register

| ID | Severity | File | Description | Fix |
|----|----------|------|-------------|-----|
| F1 | HIGH | `components/layout/index.jsx` L16-21 | Sidebar nav is static — always shows Search/Reports/Logs as disabled regardless of current route | Make `navItems` dynamic inside component using `useLocation()` |
| F2 | HIGH | `pages/CaseDetailPage.jsx` L114-145 | Header actions duplicate sidebar nav — shows same 4 links twice | Remove `actions` prop from `<Header>` call |
| F3 | HIGH | `App.jsx` HomeScreen | Demo creation has no UX — silent API call + redirect | Build and integrate `DemoModal` component |
| F4 | MEDIUM | `pages/DashboardPage.jsx` L235,241 | "Full Timeline" and "Correlation Graph" links go to `/cases/${caseId}?tab=*` which does nothing | Change to `/cases/${caseId}` until tab routing is implemented |
| F5 | MEDIUM | `hooks/useDashboard.js` | `loadOverview` may not be in `useCallback` → infinite re-render loop on dashboard | Wrap with `useCallback(async (id) => {...}, [])` |
| F6 | LOW | `pages/CaseListPage.jsx` | `new Date(case.created_at)` may crash if `created_at` is null | Add null guard |
| F7 | MISSING | `components/demo/DemoModal.jsx` | File does not exist | Create per spec in Section 8.1 |
| F8 | MISSING | `components/dashboard/MessageVolumeChart.jsx` | File does not exist | Create after installing chart.js |
| F9 | MISSING | `components/dashboard/MessageDistributionChart.jsx` | File does not exist | Create after installing chart.js |
| F10 | MISSING | chart.js, react-chartjs-2 | npm packages not installed | `npm install chart.js react-chartjs-2` in frontend/ |

---

## 11. Required Audit Tasks (Unverified Files)

| File | What to Verify |
|------|---------------|
| `frontend/src/pages/ReportsPage.jsx` | Exists; uses GET for summary calls; ReportPanel component present |
| `frontend/src/services/reportService.js` | Summary functions use GET not POST |
| `frontend/src/services/demoService.js` | `has_telegram` defaults to `true` |
| `frontend/src/hooks/useDashboard.js` | `loadOverview` wrapped in `useCallback`; no re-render loop |
| `frontend/src/hooks/useSearch.js` | `useGlobalSearch()` hook exposes correct interface |
| `frontend/src/components/evidence/EvidenceUploader.jsx` | Drag-and-drop works; shows upload progress; calls `evidenceService.uploadEvidence(caseId, file)` |
| `frontend/src/components/evidence/EvidenceInventory.jsx` | Lists files with SHA-256 hash, delete button, analysis trigger |
| `frontend/src/components/whatsapp/WhatsAppAnalysis.jsx` | Runs analysis, shows messages/contacts/groups tables |
| `frontend/src/components/telegram/TelegramAnalysis.jsx` | Same as WhatsApp |
| `frontend/vite.config.js` | Has `/api` proxy to `http://localhost:8000` |

---

## 12. Package.json Dependencies (Frontend)

```json
{
  "react": "^18.3",
  "react-dom": "^18.3",
  "react-router-dom": "^6.24",
  "axios": "^1.7",
  "date-fns": "^3.0",
  "lucide-react": "^0.400",
  "tailwindcss": "^3.4",
  "vite": "^5.4",
  "chart.js": "^4.4.0",          ← MISSING, must install
  "react-chartjs-2": "^5.2.0"   ← MISSING, must install
}
```
