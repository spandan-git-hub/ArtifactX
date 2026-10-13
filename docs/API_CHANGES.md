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

## 2026-10-13 A4 — GET /api/cases/{case_id} & POST /api/cases/{case_id}/reports
- **Endpoint:** `GET /api/cases/{case_id}`
  - **Old contract:** Analysis stage 4 was named `"Court Export"` with description `"Forensic audit complete; ready for court PDF report export."`:
    ```json
    {
      "analysis_stage": {
        "stage_number": 4,
        "stage_name": "Court Export",
        "description": "Forensic audit complete; ready for court PDF report export."
      }
    }
    ```
  - **New contract:** Stage 4 renamed to `"Report Export"` with description `"Forensic audit complete; ready for report export."`:
    ```json
    {
      "analysis_stage": {
        "stage_number": 4,
        "stage_name": "Report Export",
        "description": "Forensic audit complete; ready for report export."
      }
    }
    ```
- **Endpoint:** `POST /api/cases/{case_id}/reports`
  - Route path remains unchanged (`/api/cases/{case_id}/reports`).
  - Function renamed internally from `generate_court_report` to `generate_report`.
  - Filename in `Content-Disposition` header changed from `ArtifactX_CourtReport_Case{case_id}_{type}_{timestamp}.pdf` to `ArtifactX_ForensicReport_Case{case_id}_{type}_{timestamp}.pdf`.
  - Response error messages on generation failure sanitized from `"Failed to generate court report: ..."` to `"Failed to generate forensic report: ..."`.

