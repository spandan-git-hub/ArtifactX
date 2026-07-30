# ArtifactX Rules

## Project Files

Always read the relevant source-of-truth files before starting work:

| File | Purpose |
|------|---------|
| `PRIORITY.md` | Phase-wise step-by-step implementation tracker — use this to know what to build next |
| `FRONTEND.md` | Complete frontend implementation reference (routing, design, components, services, issues) |
| `BACKEND.md` | Complete backend implementation reference (schema, APIs, services, forensic engine) |
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
* React
* JavaScript
* Tailwind CSS
* Vite
* chart.js + react-chartjs-2

**Backend**
* FastAPI
* Python 3.13

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

## Forensic Rules

* Never fabricate forensic findings.
* Parse evidence only from uploaded evidence files via `forensic/` module.
* Do not create synthetic forensic results.
* All findings must originate from actual evidence.
* Demo mode data is clearly tagged as demo — not real forensic findings.

---

## Run Commands

```powershell
# Backend
pip install -r requirements.txt
$env:PYTHONPATH = "D:\ArtifactX"
$env:PATH = "C:\Users\Spandan\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts;$env:PATH"
cd D:\ArtifactX\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd D:\ArtifactX\frontend
npm install && npm run dev
```