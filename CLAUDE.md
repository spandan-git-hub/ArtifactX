# ArtifactX Rules

## Project Files

Always read `PLAN.md` before starting work. It contains the complete project documentation including requirements, phases, architecture, and completion status.

For skill usage, refer to `SKILLS.md` which catalogs available and recommended skills.

Do not rely on conversation history.

---

## Skills

See `SKILLS.md` for:
- Installed skills and their purposes
- How to find new skills
- When to use each skill

Installed skills:
- `find-skills` — Search for and install new capabilities
- `frontend-design` — Visual design guidance
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

**Backend**
* FastAPI
* Python

**Database**
* SQLite

---

## Development Rules

* Follow PLAN.md exactly.
* Do not invent features.
* Do not remove features.
* Do not change the technology stack.
* Generate production-ready code.
* Fix discovered issues before moving forward.

---

## Phase Execution Rules

* All phases are complete according to PLAN.md
* Maintain feature parity with existing implementation
* Refer to PLAN.md for architecture and module design

---

## Review Rules

When asked to review:

* Verify requirements implementation matches PLAN.md
* Verify APIs function correctly
* Verify frontend integration if applicable
* Check for dead code
* Check for duplicate code
* Check for broken imports
* Fix discovered issues

---

## Forensic Rules

* Never fabricate findings.
* Parse evidence only from uploaded evidence files.
* Do not create synthetic forensic results.
* All findings must originate from actual evidence.

---

## Completion Rules

ArtifactX is complete when:

* All phases in PLAN.md are marked complete
* All requirements in PLAN.md are implemented
* Verification of the implementation passes


<!-- 

# Backend
cd backend && pip install -r requirements.txt
$env:PYTHONPATH = "D:\ArtifactX"
$env:PATH = "C:\Users\Spandan\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts;$env:PATH"
cd D:\ArtifactX\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev  

-->