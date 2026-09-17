# ArtifactX — Skills Reference

> This file documents installed skills and their intended usage for ArtifactX development.
> The skills listed here are active agents capabilities, not npm packages.

---

## Installed Skills

### `frontend-design`
- **Location:** `.agents/skills/frontend-design/`
- **Purpose:** Guidance for distinctive, intentional visual design — palette, typography, layout, motion
- **When to use:**
  - Creating any new UI component or page (Chat Viewer, Timeline Stream, Correlation Graph, Court Report Preview)
  - Redesigning existing pages for better aesthetics and non-redundant layout
  - Making decisions about color, typography, spacing, animation
- **Key principle:** Design should be forensic-tool-specific — dark, precise, data-forward, high density workstation UI. Not generic SaaS.
- **Avoid:** AI-default looks (warm cream + serif, near-black + acid-green, broadsheet layouts), broken/senseless action buttons, duplicate nav links
- **ArtifactX identity:** Dark slate/blue-gray base (`forensic-950`), cyan accent, monospace data displays (`JetBrains Mono`), subtle glow effects, clear deletion indicators (`accent-rose`)

### `vercel-react-best-practices`
- **Location:** `.agents/skills/vercel-react-best-practices/`
- **Purpose:** React performance optimization — waterfalls, bundle size, re-renders, data fetching
- **When to use:**
  - Writing any new React component or custom hook
  - Data fetching with hooks (`useCallback` memoization to prevent infinite re-renders)
  - Reviewing components for performance
  - Bundle optimization & chart rendering efficiency
- **Key rules for ArtifactX:**
  - Use `Promise.all()` for parallel API calls (avoid waterfalls in hooks)
  - Avoid barrel imports — import directly from component files
  - Use `useTransition` / `useDeferredValue` for high-volume message search and timeline filters
  - Hoist static JSX outside component render (static icons, empty states)
  - Use functional `setState` in callbacks to avoid stale closures

### `find-skills`
- **Location:** `.agents/skills/find-skills/`
- **Purpose:** Search for and install new skills from https://skills.sh/ when a needed capability is missing
- **When to use:**
  - When a task requires expertise not covered by installed skills
  - Before implementing something complex from scratch

---

## Skills Gap Analysis

The following skills are NOT installed but would be valuable for ArtifactX:

| Capability Needed | Reason |
|------------------|--------|
| **Python/FastAPI best practices** | Backend needs proper async patterns, background processing, type safety |
| **Security & Evidence Cryptography** | Forensic tool must calculate and verify SHA-256 / MD5 / SHA-1 hashes and maintain chain of custody |
| **Testing (pytest + jest)** | Unit & integration tests for evidence parsers and court report generator |
| **Court-Ready PDF Generation** | ReportLab rules for legal document layout, page numbering, sworn sign-off blocks, verification tables |
| **Data Visualization & Graphs** | chart.js + react-chartjs-2 integration for timeline density and entity correlation matrices |

### Finding New Skills

```bash
# Search the skills registry
npx skills find python
npx skills find fastapi
npx skills find security
npx skills find testing

# Install globally
npx skills add <owner/repo@skill> -g -y
```

---

## Skill Usage Map for ArtifactX Tasks

| Task | Primary Skill | Secondary Skill |
|------|--------------|----------------|
| Workstation UI Redesign | `frontend-design` | `vercel-react-best-practices` |
| Interactive Chat & Message Viewer | `frontend-design` | `vercel-react-best-practices` |
| Chronological Timeline & Correlation UI | `frontend-design` (design) | `vercel-react-best-practices` (perf) |
| Court-Ready Report Preview & Export | `frontend-design` | — |
| Backend API & Hashing Engine | None installed — use BACKEND.md | — |
| Demo Workstation Workflow | `frontend-design` | `vercel-react-best-practices` |
| Finding new capability | `find-skills` | — |

---

## ArtifactX Design Identity (for `frontend-design` skill)

When the `frontend-design` skill asks to "ground it in the subject":

**Subject:** A digital forensic analysis and court report platform used by law enforcement, legal investigators, and forensic experts to extract, correlate, and present digital evidence from mobile applications (WhatsApp, Telegram, EXIF metadata).

**Audience:** Digital forensics professionals, law enforcement officers, legal counsel, and judicial courts.

**Visual identity:**
- **Dark, precise, clinical forensic workstation** — high contrast dark slate (`forensic-950`), clear data hierarchy
- **Monospaced fonts for technical data** — SHA-256/MD5/SHA-1 hashes, entity IDs, timestamps, and raw DB rows all use JetBrains Mono
- **Cyan as primary accent** (`#06b6d4`) — technological, analytical, precise
- **App Color Coding:** Green (`#10b981`) = WhatsApp, Blue (`#3b82f6`) = Telegram, Violet (`#8b5cf6`) = Cross-app Correlations, Rose (`#f43f5e`) = Deleted Messages & Anomalies
- **Data-forward & Interactive:** Interactive chat message threads, timeline density charts, entity correlation nodes, and instant metadata inspection panels
- **Court-Ready Formatting:** Crisp typography, official seal headers, clear evidence integrity hashes, and structured legal annexures

**One unique element (signature):** The **Evidence Fingerprint Badge** displayed across every evidence item and court report page — showing cryptographic SHA-256 hash in `hash-text` style alongside verification timestamp and chain-of-custody status tag (`VERIFIED_INTACT`).

---

## Notes

- Forensic rules: Never fabricate findings. All data displayed must originate from actual evidence or explicit demo mock data. No synthetic forensic results.
- Cryptographic integrity: Always compute SHA-256, MD5, and SHA-1 hashes upon file ingestion and verify them before court report compilation.
- Evidence parsing lives in `forensic/` — a separate package from `backend/`. Keep this boundary clean.
- The `.env` file contains real credentials (Neon DB URL). Never log or expose these.
