# ArtifactX Rules

## Project Files

Always read the following files before starting work:

* PROJECT_PLAN.md
* REQUIREMENTS.md
* PLAN.md
* STATUS.md
* TASKS.md

Use these files as the source of truth.

Do not rely on conversation history.

---

## Required Skills

* fastapi
* frontend-design
* vercel-react-best-practices
* forensic-data-engineer
* forensic-reporting
* find-skills

If a required skill is missing:

* attempt global installation
* if installation is not possible, stop and report the missing skill

---

## Technology Stack

Frontend

* React
* JavaScript
* Tailwind CSS

Backend

* FastAPI
* Python

Database

* SQLite

---

## Development Rules

* Follow REQUIREMENTS.md exactly.
* Do not invent features.
* Do not remove features.
* Do not change the technology stack.
* Generate production-ready code.
* Generate tests for backend functionality.
* Fix discovered issues before moving forward.

---

## Phase Execution Rules

* Determine the next unfinished phase from PLAN.md.
* Implement only one phase at a time.
* Do not start the next phase until the current phase is complete.
* Update TASKS.md after completed tasks.
* Update STATUS.md after completed phases.

---

## Review Rules

When asked to review:

* Verify requirements implementation.
* Verify tests exist.
* Verify tests pass.
* Verify APIs function correctly.
* Verify frontend integration if applicable.
* Check for dead code.
* Check for duplicate code.
* Check for broken imports.
* Fix discovered issues.

Do not start another phase during review.

---

## Forensic Rules

* Never fabricate findings.
* Parse evidence only from uploaded evidence files.
* Do not create synthetic forensic results.
* All findings must originate from actual evidence.

---

## Completion Rules

ArtifactX is complete only when:

* Every phase in PLAN.md is complete.
* Every task in TASKS.md is checked.
* Every requirement in REQUIREMENTS.md is implemented.
* Integration testing passes.
* Requirements audit passes.
