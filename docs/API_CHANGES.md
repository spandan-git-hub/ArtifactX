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
## 2026-10-13 A5 — Zero-Disk Storage & Legacy Row Fallbacks
- **Endpoint:** `POST /api/evidence/{evidence_id}/verify-hashes`
  - **Old contract:** Attempted to read from disk (`storage_path` or `UPLOADS_DIR / storage_path`) when `content_bytes` was NULL.
  - **New contract:** Strictly in-memory verification. For legacy rows lacking binary content in database, returns `verification_status="LEGACY_UNVERIFIABLE"`, `is_valid=false`, and `main_file.actual_sha256="LEGACY_UNVERIFIABLE"`.
  - Added field: `"integrity_state": "OK" | "LEGACY_UNVERIFIABLE"`.
  - Sample response for legacy row:
    ```json
    {
      "evidence_id": 1,
      "case_id": 1,
      "filename": "legacy_msgstore.db",
      "verification_status": "LEGACY_UNVERIFIABLE",
      "integrity_state": "LEGACY_UNVERIFIABLE",
      "is_valid": false,
      "verified_at": "2026-10-13T22:00:00.000000",
      "main_file": {
        "storage_path": "uploads/legacy_msgstore.db",
        "expected_sha256": "e3b0c44298fc...",
        "actual_sha256": "LEGACY_UNVERIFIABLE",
        "expected_md5": null,
        "actual_md5": "LEGACY_UNVERIFIABLE",
        "expected_sha1": null,
        "actual_sha1": "LEGACY_UNVERIFIABLE",
        "is_intact": false
      },
      "extracted_files_summary": {
        "total": 0,
        "matched": 0,
        "mismatched": 0
      },
      "files": []
    }
    ```
- **Endpoint:** `GET /api/cases/{case_id}/workspace`
  - Added `legacy_unverifiable_count` to `summary_counts`.
  - Added `integrity_state` to each item in `active_evidence[]`.
- **Endpoint:** `GET /api/cases/{case_id}/reports/summary`
  - Added `legacy_unverifiable_count` integer count field to `EvidenceSummary`.
- **Endpoint:** `GET /api/evidence` & `GET /api/evidence/{evidence_id}`
  - Added `integrity_state` to `EvidenceRead` response schema.
- **Endpoint:** `GET /api/evidence/{evidence_id}/files/{file_id}`
  - Returns in-memory binary response (`Response(content=...)`) directly from database storage instead of disk file (`FileResponse`). Returns 404 if bytes are unavailable on legacy rows.
