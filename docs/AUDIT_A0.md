# AUDIT_A0 — Verified Inventory: Code vs. REPORTBYSONNET.md Claims

**Date:** 2026-10-13  
**Branch:** `feat/A0-audit-baseline`  
**Auditor:** IDE agent (A0 pass)  
**Method:** grep, file inspection, manual code trace

> All file paths relative to `D:\ArtifactX\`.

---

## 1. Table / Router Counts

| Claim in REPORTBYSONNET.md | Verified count | Discrepancy |
|---|---|---|
| "26 tables" | **24 tables** | Report overcounts by 2 (person_entities listed twice) |
| "17 routers" | **16 registrations, 15 unique files** | timeline registered twice; 15 unique API modules |

**24 actual tables:** Case, Evidence, EvidenceFile, AnalysisResult, WhatsAppMessage, WhatsAppContact, WhatsAppGroup, TelegramMessage, TelegramContact, TelegramGroup, TimelineEvent, DeletedMessage, MediaItem, CorrelationEdge, AnalysisLog, ActivityLog, ErrorLog, GeneratedReport, RecoveryRun, RecoveredFinding, DerivedArtifact, DecryptionOperation, PersonEntity, CorrelationFinding

---

## 2. Demo Remnants

| Claim | Verified? | Code reality | File:line |
|---|---|---|---|
| Demo mode removed, scaffolding retained | **Absent** | No demo.py, no DEMO_MODE, no DemoModal.jsx, no demoService.js anywhere | (none) |
| Health endpoint returns `demo_mode` | **False** | Returns `{"status":"ok","app":…,"version":"1.0.0"}` only | `backend/app/main.py:86-91` |

A0 finding: Demo/seeding remnants are absent. A2 will be a no-op or minimal.

---

## 3. Sentiment / Assistant Remnants

| Claim | Verified? | Code reality |
|---|---|---|
| ForensicAssistantDrawer.jsx / useAiAssistant.js present | **Not found** | grep for sentiment|assistant|copilot returns 0 hits everywhere |

A0 finding: Sentiment/assistant remnants are absent. A3 will be a no-op.

---

## 4. Court-Ready / Banned Language Violations (R9) — CRITICAL

Confirmed violations requiring A4:

| Banned string | Files and lines |
|---|---|
| `"court-ready PDF"` / `"court-ready"` | `backend/services/report_service.py:1,4,91,112,185` |
| `"COURT ADMISSIBLE"` | `backend/services/report_service.py:72` |
| `"court report"` / `generate_court_report` function | `backend/api/reports.py:34,42,65` |
| `"Court Export"` stage name | `backend/api/cases.py:118` |
| `"court-ready JSON graph"` | `backend/services/correlation_service.py:498` |
| `"court-ready reports"` docstring | `backend/models/models.py:314` |
| `"judicial provenance"` | `forensic/decryption/orchestrator.py:5` |
| `"Court-Ready PDF Reports & Custody Tracker"` | `frontend/src/pages/ReportsPage.jsx:125` |
| `"Judicial Admissibility Guarantee"` | `frontend/src/components/reports/ReportPdfPreview.jsx:81` |
| `generateCourtReportStream` / `ArtifactX_CourtReport_` | `frontend/src/services/reportService.js:9,29` |
| `'Court Export'` stepper label | `frontend/src/components/workspace/ForensicWorkflowStepper.jsx:35` |
| `"Generate & Stream Court PDF"` | `frontend/src/components/reports/ReportPanel.jsx:210` |

---

## 5. uploads/ and reports/ Directories

| Claim | Verified? | Code reality | File:line |
|---|---|---|---|
| Startup creates uploads/ and reports/ | **False** | main.py does NOT mkdir; but config.py defines UPLOADS_DIR/REPORTS_DIR | `backend/app/config.py:36-38` |
| `upload_dir` setting present | **YES** | `upload_dir: str = "uploads"` present | `backend/app/config.py:24` |
| `max_upload_size` | **1 GiB** | Spec requires 256 MiB (DEC-009) | `backend/app/config.py:25` |
| `TEST_DATABASE_URL` setting | **Absent** | Not in config or .env.example | — |

---

## 6. verify-hashes Disk Fallback — CONFIRMED (R4 violation)

`POST /{evidence_id}/verify-hashes`:
- Tries `content_bytes` first (OK)
- Falls back to `Path(evidence.storage_path)` / `UPLOADS_DIR / evidence.storage_path` and calls `compute_multi_hashes(filepath)` from `hashing.py` — **disk read**
- For EvidenceFile members: falls back to `evidence.extracted_path` on disk

Files: `backend/api/evidence.py:688-746`, `backend/utils/hashing.py:8-38`

Action required: A5.2

---

## 7. Decryption Code

| Item | Verified? | Code reality | File |
|---|---|---|---|
| crypt12/14/15 decryptors | **YES** | All present and registered in orchestrator | `forensic/decryption/whatsapp/crypt*.py` |
| crypt15 passkey->PBKDF2-SHA512 | **Unverified** | File exists; design believed wrong (DEC-002); must verify at B6 | `crypt15.py` — TODO(verify) |
| Telegram SQLCipher decryptor | **YES — violation** | Exists, registered in orchestrator, dispatched on `fmt=="sqlcipher"` | `forensic/decryption/telegram/sqlcipher.py`, `orchestrator.py:18,83-92` |
| Telegram MTProto decryptor | **YES — violation** | Exists, registered, dispatched | `forensic/decryption/telegram/mtproto.py`, `orchestrator.py:19,94-100` |
| WhatsApp media .enc decryptor | **YES — no test fixture** | Exists, registered; violates R7 (no test proves it) | `forensic/decryption/whatsapp/media.py`, `orchestrator.py:77-81` |
| DECRYPTOR_NOT_AVAILABLE guard | **Absent** | All formats reachable; no typed error returned | `orchestrator.py:59-103` |

Action required: A6.1 (remove Telegram decryptors), A6.2 (remove media), A6.4 (unregister all, add plugin interface)

---

## 8. Telegram Parser

| Claim | Verified? | Code reality |
|---|---|---|
| TL/TDS blob parser exists | **NO** | grep for tl, TLRPC, struct.unpack, NativeByteBuffer in forensic/ = 0 hits. NO TL parser. |
| Message bodies from TL blobs | **Unlikely** | telegram_service.py (12 KB) does not import any TL library; likely reads plain columns |

A0 finding: **No TL parser exists**. Major gap; implement in B9.

---

## 9. WAL / Freelist Carving Code

| Claim | Verified? | Code reality |
|---|---|---|
| Carving code inside backend/api/recovery.py | **PARTIALLY FALSE** | API is thin; delegates to forensic.deleted.DeletedRecoveryEngine (correct layering R18) |
| Physical carving engine | **YES** | forensic/deleted/ has wal_carver.py, freelist_carver.py, slack_carver.py, orchestrator.py, sqlite_record.py, payload_decoder.py — a real engine |
| Carving level | Page + record level (per filenames); accuracy to be tested in B8/B10 |

---

## 10. Perceptual Hash Code

| Claim | Verified? | Code reality |
|---|---|---|
| Perceptual hash implemented | **NO** | grep for imagehash/phash/dhash/perceptual = 0 hits. Feature does not exist. |

Action required: B12.4.

---

## 11. Confidence Formulas

| Claim | Verified? | Code reality | File |
|---|---|---|---|
| Deletion confidence "calibrated 0.10-0.95" | Unverified | DeletedMessage.confidence_score column exists; formula in forensic/deleted/orchestrator.py not yet read | B10 pass |
| confidence_score=1.0 on shared-artifact matches | **YES — R8 violation** | PersonEntity.confidence_score default=1.0; CorrelationFinding.confidence_score default=1.0 | `models.py:452,480` |

Action required: B12.6.

---

## 12. Health Endpoint

Returns: `{"status":"ok","app":"ArtifactX","version":"1.0.0"}`  
No `demo_mode` field. Clean.

---

## 13. Other Key Findings

| Finding | File:line | Action |
|---|---|---|
| `Base.metadata.create_all()` + raw ALTER TABLE at startup | `main.py:28-35` | A1.2: introduce Alembic |
| `storage_path` column in Evidence (nullable=False) | `models.py:61` | A5.3 |
| `backend/utils/file_storage.py` disk utilities | `file_storage.py:1-36` | A5.1 |
| 0 tests; no tests/ directory | — | A1 |
| `backend/scripts/test_phase14_e2e.py` does not exist | — | Pre-existing gap |

---

## 14. Baseline Measurements (A0.3)

| Metric | Value |
|---|---|
| pytest collected | **0 tests** (no tests/ directory) |
| `npm run build` | **PASS** (exit 0, 16.51s, 1935 modules) |
| `backend/scripts/test_phase14_e2e.py` | **Does not exist** |

---

## 15. Git / .env State (A0.4)

| Check | Result |
|---|---|
| `.env` git-ignored | YES — `.gitignore:24:.env` |
| Git tree before A0 work | Only `.gitignore` modified (`Project Files/` ignore entry) |
| Tag `pre-cleanup` | To be created in this pass |

---

## Summary of Discrepancies (priority order)

| # | Issue | Severity | Section |
|---|---|---|---|
| 1 | Banned language throughout backend + frontend (court-ready, COURT ADMISSIBLE, Judicial Admissibility) | Critical R9 | A4 |
| 2 | Telegram SQLCipher/MTProto decryptors registered and reachable | Critical R7/DEC-004 | A6.1 |
| 3 | WA media .enc decryptor registered, no test fixture | Critical R7/DEC-005 | A6.2 |
| 4 | No DECRYPTOR_NOT_AVAILABLE guard; all formats reachable | Critical R7/DEC-006 | A6.4 |
| 5 | 0 tests; no test infrastructure | Critical R13 | A1 |
| 6 | Disk fallback in verify-hashes | High R4 | A5.2 |
| 7 | storage_path column, no migration | High | A5.3 |
| 8 | create_all + raw ALTER TABLE at startup | High | A1.2 |
| 9 | PersonEntity/CorrelationFinding default confidence=1.0 | High R8 | B12.6 |
| 10 | TEST_DATABASE_URL not in config | High R13 | A1/A7 |
| 11 | upload_dir setting; UPLOADS_DIR/REPORTS_DIR defined | Medium | A5/A7 |
| 12 | max_upload_size 1 GiB vs spec 256 MiB | Medium | A7.1 |
| 13 | No TL parser for Telegram messages | Major gap | B9 |
| 14 | No perceptual hash implementation | Major gap | B12.4 |
| 15 | Table count: 24 vs 26 claimed; router count: 15 vs 17 | Minor | Doc only |
| 16 | Demo/assistant code: absent (REPORTBYSONNET wrong) | Minor | A2/A3 no-ops |
