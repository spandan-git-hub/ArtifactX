# ArtifactX — API Changes Log

Maintained per `master.md` §1 and §6. Tracks all backend API contract changes so the frontend can be updated accordingly.

---

## 2026-10-13 A2 — GET /api/health
- **Old contract (per specification/legacy design):** Included `demo_mode: bool` field in health check response:
  ```json
  {
    "status": "ok",
    "app": "ArtifactX",
    "version": "1.0.0",
    "demo_mode": false
  }
  ```
- **New contract (verified in A0 & enforced in A2):** `demo_mode` field is removed. Only application status, name, and version are returned:
  ```json
  {
    "status": "ok",
    "app": "ArtifactX",
    "version": "1.0.0"
  }
  ```
- **Demo routes status:** No `/api/demo` routes exist (returns 404). All demo endpoints and schemas are absent.

## 2026-10-13 A3 — /api/assistant & /api/sentiment (Absence / Removal)
- **Old contract (per legacy design):** AI forensic assistant chat (`POST /api/assistant/chat`) and sentiment query endpoints.
- **New contract (verified & enforced in A3):** All assistant and sentiment routes are absent from the application router (return HTTP 404). Subjective AI predictions and sentiment scores are strictly excluded from the platform.

