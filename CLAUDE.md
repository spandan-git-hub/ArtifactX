# ArtifactX Rules

## Project Files

Always read the relevant source-of-truth files before starting work:

| File | Purpose |
|------|---------|
| `PRIORITY.md` | Phase-wise step-by-step implementation tracker — use this to know what to build next |
| `FRONTEND.md` | Complete frontend implementation reference (routing, design, components, services, issues, UX standards) |
| `BACKEND.md` | Complete backend implementation reference (schema, APIs, services, forensic engine, report generation) |
| `SKILLS.md` | Installed skills, usage map, and ArtifactX design identity |

Do not rely on conversation history. Always re-read the relevant file.

---

## Skills

See `SKILLS.md` for installed skills and when to use them.

Installed skills:
- `find-skills` — Search for and install new capabilities
- `frontend-design` — Visual design guidance (follow ArtifactX identity in SKILLS.md)
- `vercel-react-best-practices` — React performance optimization

If a needed skill is missing:
* search at https://skills.sh/ or run `npx skills find [query]`
* install via `npx skills add <skill> -g -y`
* if installation fails, stop and report

---

## Technology Stack

**Frontend**
* React 18
* JavaScript
* Tailwind CSS
* Vite
* chart.js + react-chartjs-2
* Lucide React icons
* date-fns

**Backend**
* FastAPI
* Python 3.13
* SQLAlchemy 2.0
* Pydantic v2
* ReportLab (Court-Ready PDF report engine)
* structlog

**Database**
* PostgreSQL (Neon cloud — see `.env` for connection string)
* SQLite used only by forensic parsers to READ evidence files (not the app DB)

---

## Development Rules

* Follow `PRIORITY.md` for what to implement next.
* Use `FRONTEND.md` and `BACKEND.md` as source of truth for all implementation details.
* Do not invent features not listed in these files.
* Do not remove existing features.
* Do not change the technology stack.
* Generate production-ready code.
* Fix discovered issues before moving forward.

---

## UI/UX & Redundancy Rules

* **No Redundant or Senseless Buttons:** Completely eliminate redundant "Quick Actions" cards, confusing magnifying glass buttons next to case items, and misleading redirect links (e.g. "Full Timeline", "Correlation Graph", "Case Details" buttons on dashboard). All navigation MUST be handled cleanly by the context-aware sidebar and workstation tabs.
* **No Broken or Redirecting Buttons:** Every button, tab, and link must point to a valid, working route or trigger a defined modal/action. Never use dummy query params like `?tab=timeline`.
* **No Redundant Navigation:** Remove duplicate action buttons in headers that replicate sidebar navigation. Sidebar navigation must be context-aware (showing active case links when inside a case).
* **Forensic Workstation UX:** Layout must follow a structured 4-step forensic workflow: 1) Ingestion & Hashing -> 2) Parsing & Extraction -> 3) Deep Analysis (Timeline/Correlation/Deletions/Chat Viewer) -> 4) Verification & Court Report Export.
* **Data-Forward & High Density:** Prioritize interactive chat viewers, metadata drawers, and data visualization over text-heavy static cards.

---

## Forensic & Integrity Rules

* **Evidence Integrity & Hashing:** Calculate and display cryptographic hashes (SHA-256, MD5, SHA-1) on ingestion and verification. Maintain a chain-of-custody log for all operations.
* **No Synthetic Artifacts:** Never fabricate forensic findings. Parse evidence only from uploaded evidence files via `forensic/` module. Demo mode data must be clearly tagged as demo data.
* **Court-Ready Reports & Zero Workspace Storage:** Generated PDF court reports **MUST NOT** be saved inside the project workspace directory. Reports must be generated in-memory (`io.BytesIO`) and streamed directly to the browser for download (`StreamingResponse`), or cached in system temp storage (`tempfile.gettempdir()`). Report metadata (Case ID, Report Type, Generation Timestamp, Lead Analyst, Verification SHA-256 Hash of PDF bytes) must be tracked in the app database (`generated_reports` / `activity_logs`).
* **AI Forensic Assistant Isolation (Legal Boundary):** The AI Assistant (copilot chat, chat sentiment analysis, intention checking, suspicion scoring) is strictly an internal investigative helper for the human investigator. **AI insights MUST BE EXCLUDED from official court-ready PDF reports** to ensure judicial admissibility and prevent courts from rejecting evidence.

---

## Run Commands

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