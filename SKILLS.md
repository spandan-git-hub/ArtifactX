# ArtifactX — Skills Reference

> This file documents installed skills and their intended usage for ArtifactX development.
> The skills listed here are active agents capabilities, not npm packages.

---

## Installed Skills

### `frontend-design`
- **Location:** `.agents/skills/frontend-design/`
- **Purpose:** Guidance for distinctive, intentional visual design — palette, typography, layout, motion
- **When to use:**
  - Creating any new UI component or page
  - Redesigning existing pages for better aesthetics
  - Making decisions about color, typography, spacing, animation
- **Key principle:** Design should be forensic-tool-specific — dark, precise, data-forward. Not generic SaaS.
- **Avoid:** AI-default looks (warm cream + serif, near-black + acid-green, broadsheet layouts)
- **ArtifactX identity:** Dark blue-gray base (`forensic-950`), cyan accent, monospace data displays, subtle glow effects

### `vercel-react-best-practices`
- **Location:** `.agents/skills/vercel-react-best-practices/`
- **Purpose:** React performance optimization — waterfalls, bundle size, re-renders, data fetching
- **When to use:**
  - Writing any new React component
  - Data fetching with hooks
  - Reviewing components for performance
  - Bundle optimization
- **Key rules for ArtifactX:**
  - Use `Promise.all()` for parallel API calls (avoid waterfalls in hooks)
  - Avoid barrel imports — import directly from component files
  - Use `useTransition` / `useDeferredValue` for search input
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
| **Python/FastAPI best practices** | Backend needs proper async patterns, error handling, type safety |
| **Security auditing** | Forensic tool must handle evidence securely; no file path traversal, no data leaks |
| **Testing (pytest + jest)** | No test coverage exists; brittle to changes |
| **PDF/report generation** | ReportLab is complex; a skill with patterns would help |
| **Data visualization** | chart.js integration patterns for forensic dashboards |

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
| New page or component | `frontend-design` | `vercel-react-best-practices` |
| New React hook or data fetching | `vercel-react-best-practices` | — |
| Redesigning existing UI | `frontend-design` | — |
| Charts / visualizations | `frontend-design` (design) | `vercel-react-best-practices` (perf) |
| Backend API endpoint | None installed — use BACKEND.md | — |
| Demo modal UX | `frontend-design` | `vercel-react-best-practices` |
| Finding new capability | `find-skills` | — |

---

## ArtifactX Design Identity (for `frontend-design` skill)

When the `frontend-design` skill asks to "ground it in the subject":

**Subject:** A forensic analysis platform used by investigators to extract and analyze evidence from mobile apps (WhatsApp, Telegram).

**Audience:** Digital forensics professionals, law enforcement, legal investigators.

**Visual identity:**
- **Dark, precise, clinical** — like a terminal or security dashboard
- **Monospaced fonts for data** — hashes, IDs, timestamps all use JetBrains Mono
- **Cyan as primary accent** — feels technological, analytical, not consumer
- **Data-forward** — charts, tables, and metrics are the hero, not decorative elements
- **Minimal animation** — subtle fade-ins, no bouncy transitions; this is a serious tool
- **Green = WhatsApp, Blue = Telegram** — consistent color coding throughout

**One unique element (signature):** The SHA-256 hash displayed for every evidence file in `hash-text` style — cyan monospace breaking across lines. This is the visual fingerprint of the forensic world made literal.

---

## Notes

- Forensic rules: Never fabricate findings. All data displayed must originate from actual evidence or explicit demo mock data. No synthetic forensic results.
- Evidence parsing lives in `forensic/` — a separate package from `backend/`. Keep this boundary.
- The `.env` file contains real credentials (Neon DB URL). Never log or expose these.
