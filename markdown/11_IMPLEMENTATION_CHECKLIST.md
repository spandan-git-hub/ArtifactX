# ArtifactX Master Implementation Checklist

> Update this file after every completed feature. Never rely on memory for project progress.

## Status legend

- [ ] Not started
- [~] In progress
- [x] Verified complete
- [!] Blocked / needs decision
- [D] Deferred intentionally

---

# A. Baseline Preservation

- [x] Repository snapshot created before R1
- [x] Existing backend starts
- [x] Existing frontend builds
- [x] Existing database schema captured
- [x] Existing API/OpenAPI snapshot captured
- [x] Existing Phase 14 regression test captured
- [x] Existing zero-disk behavior measured
- [x] Current Git working tree recorded

# B. R1 — AI Excision

- [x] Remove `backend/api/assistant.py`
- [x] Remove `backend/services/assistant_service.py`
- [x] Remove `ForensicAssistantDrawer.jsx`
- [x] Remove `useAiAssistant.js`
- [x] Remove `assistantService.js`
- [x] Remove assistant router include
- [x] Remove assistant UI triggers
- [x] Remove assistant frontend route/state references
- [x] Remove assistant-only dependencies
- [x] Repository-wide assistant reference audit complete
- [x] No sentiment/suspicion code remains active
- [x] Court report contains no AI-derived fields
- [x] R1 backend tests pass
- [x] R1 frontend build passes

# C. Zero-Local-Storage Hardening

- [x] Upload stream hashes without persistent local staging
- [x] Evidence binary stored in PostgreSQL
- [x] ZIP members stored in PostgreSQL
- [x] SQLite parser accepts memory/stream input
- [x] Media parser accepts memory/stream input
- [x] Derived artifacts have parent hashes
- [x] Report generation uses `BytesIO`
- [x] `uploads/` remains empty
- [x] `reports/` remains empty
- [x] Zero-disk integration test passes
- [x] No sensitive material appears in logs

# D. R2 — Physical Recovery

- [x] WAL header parser
- [x] WAL frame parser
- [x] WAL page reconstruction
- [x] Freelist header parser
- [x] Freelist trunk traversal
- [x] Freelist leaf-page scanner
- [x] B-tree page parser
- [x] Cell/freeblock/slack scanner
- [x] SQLite varint decoder
- [x] SQLite serial-type decoder
- [x] SQLite record decoder
- [x] WhatsApp payload candidate decoder
- [x] Telegram payload candidate decoder
- [x] Recovery provenance schema
- [x] Recovery API
- [x] Recovery UI
- [x] Synthetic deletion fixtures
- [x] Malformed SQLite fixtures
- [x] False-positive tests
- [x] Source immutability test
- [x] R2 acceptance gate passed

# E. R3 — Decryption

- [ ] Encryption format detector
- [ ] WhatsApp key parser
- [ ] Crypt12 implementation validated against fixtures
- [ ] Crypt14 implementation validated against fixtures
- [ ] Crypt15 implementation validated against fixtures
- [ ] WhatsApp media decryptor validated
- [ ] Telegram SQLCipher detector
- [ ] Authorized passcode workflow
- [ ] SQLCipher parameter profiles validated
- [ ] Telegram secret-chat implementation validated
- [ ] Decryption operation provenance
- [ ] Derived-artifact storage
- [ ] Key/passcode redaction tests
- [ ] Wrong-key tests
- [ ] Corruption/authentication tests
- [ ] Zero-disk plaintext test
- [ ] R3 acceptance gate passed

# F. R4 — Deep Correlation

- [ ] Person entity model
- [ ] Account/entity attribute model
- [ ] Identity-resolution engine
- [ ] Evidence-backed edge model
- [ ] Platform handover detector
- [ ] Configurable handover threshold
- [ ] pHash implementation
- [ ] dHash implementation
- [ ] Media distance tests
- [ ] Crypto artifact extraction
- [ ] Banking artifact extraction
- [ ] Code-word/artifact extraction
- [ ] GPS rendezvous detector
- [ ] Graph API
- [ ] Graph UI
- [ ] Edge drill-down to evidence
- [ ] Ambiguous-match labeling
- [ ] R4 acceptance gate passed

# G. R5 — Analysis Suite

## G1 Temporal
- [ ] Circadian heatmap
- [ ] Message velocity
- [ ] Baseline calculation
- [ ] Statistical spike detection
- [ ] Response latency
- [ ] Initiator metrics
- [ ] Blackout detection
- [ ] Parameter provenance

## G2 Network
- [ ] Degree centrality
- [ ] Betweenness centrality
- [ ] Eigenvector centrality
- [ ] Community detection
- [ ] Reference graph fixtures
- [ ] Metric reproducibility tests

## G3 Financial/Artifact
- [ ] Bitcoin detector
- [ ] EVM detector
- [ ] Monero candidate detector
- [ ] Tron/USDT candidate detector
- [ ] IBAN validation
- [ ] SWIFT/BIC detection
- [ ] Luhn validation
- [ ] Onion detection
- [ ] Proxy/VPN artifact detection
- [ ] Sensitive-secret redaction
- [ ] Artifact provenance

## G4 Spatial
- [ ] EXIF/location normalization
- [ ] Unified trajectory
- [ ] Haversine calculation
- [ ] Velocity calculation
- [ ] Impossible-transit anomaly
- [ ] Simultaneous-location anomaly
- [ ] Proximity analysis
- [ ] Map UI
- [ ] Calculation drill-down

## G5 Tamper Diagnostics
- [ ] SQLite header parser
- [ ] Page-size checks
- [ ] Change-counter checks
- [ ] Schema-cookie checks
- [ ] Freelist diagnostics
- [ ] Page allocation consistency
- [ ] Timestamp anomaly checks
- [ ] Clock-skew diagnostics
- [ ] Synthetic tamper fixtures

- [ ] R5 acceptance gate passed

# H. Court Reporting

- [ ] Deterministic evidence sections preserved
- [ ] Recovery section policy defined
- [ ] Decryption provenance section defined
- [ ] Deep-correlation section defined
- [ ] Analysis section inclusion policy defined
- [ ] Experimental/unvalidated findings excluded or clearly separated
- [ ] Report SHA-256 recorded
- [ ] Page count recorded
- [ ] Byte size recorded
- [ ] Re-download hash identical
- [ ] Zero report files on disk
- [ ] Report regression suite passes

# I. Security and Operational Readiness

- [ ] Authorization boundary documented
- [ ] Case-level access control verified
- [ ] Sensitive input redaction verified
- [ ] Rate limits for credential-testing workflows verified
- [ ] Audit trail covers decryption/recovery/analysis
- [ ] Dependency audit completed
- [ ] Secret scanning completed
- [ ] Malformed archive tests pass
- [ ] Oversized upload tests pass
- [ ] ZIP path traversal tests pass
- [ ] Resource exhaustion tests pass
- [ ] Database transaction rollback tests pass

# J. Final Release Gate

- [ ] All R1–R5 phase gates passed
- [ ] Full backend test suite passes
- [ ] Full frontend build passes
- [ ] End-to-end workstation test passes
- [ ] Zero-local-disk test passes
- [ ] Database migration verified
- [ ] API/OpenAPI contract verified
- [ ] Court report byte-for-byte re-download verified
- [ ] Provenance audit performed
- [ ] Documentation updated
- [ ] This checklist is fully current
- [ ] Release candidate tagged

---

## Current project state

**Last completed phase:** Phase D — R2 Physical Recovery

**Current active phase:** Phase E — R3 Decryption

**Current active task:** Review Phase E requirements and establish implementation plan for Cryptographic Decryption (WhatsApp Crypt12/14/15, Telegram SQLCipher)

**Blocking issue:** None

**Last successful test command:** `$env:PYTHONPATH="d:\ArtifactX"; python backend\scripts\test_r2_recovery_e2e.py`

**Last verified commit/change:** Phase D R2 Physical Recovery verified complete (6/6 R2 tests passed, 11/11 Phase 14 regression passed, 10/10 zero-storage passed, vite build clean with 0 errors)

**Next action:** Await user instruction before proceeding to Phase E

**Date/time updated:** 2026-09-18 00:32:00 UTC+05:30

## Change log

| Date | Phase | Change | Tests | Status | Notes |
|---|---|---|---|---|---|
| 2026-09-17 | Phase A | Captured DB schema (18 tables), OpenAPI contract (70 routes, 2 assistant endpoints), full Phase 14 regression run (11/11 passed, 0 workspace PDFs), system metadata, and frontend build verification (vite build 0 errors). | `test_phase14_e2e.py` (11/11), `npm run build` | Verified complete | Baseline frozen in `snapshots/` prior to R1 |
| 2026-09-17 | Phase B | Surgically removed assistant router & service, frontend assistant drawer/hook/service, copilot UI buttons, sentiment/suspicion overlays, and inspector cards. Verified 0 active AI references. | OpenAPI route check (68 clean routes), `test_phase14_e2e.py` (11/11 passed), `vite build` (0 errors) | Verified complete | Judicial admissibility enforced; AI entirely excised |
| 2026-09-17 | Phase C | Hardened zero-local-storage pipeline: added BYTEA columns to evidence, evidence_files, and generated_reports; in-memory stream hashing; in-memory ZIP extraction; deserialized in-memory SQLite parser (open_sqlite); in-memory EXIF/media inspection; eliminated tempfile caching for court PDFs. | `test_zero_storage_e2e.py` (10/10 passed), `test_phase14_e2e.py` (11/11 passed), `vite build` (0 errors) | Verified complete | Zero-local-disk target fully satisfied; uploads/ and reports/ remain strictly empty |
| 2026-09-18 | Phase D | Implemented SQLite physical carving: WAL header & frame parser, freelist trunk/leaf scanner, B-tree cell slack space carver, varint/serial-type/record decoders, WhatsApp & Telegram payload decoders, RecoveredFinding & RecoveryRun models, 4 REST endpoints (`/api/cases/{case_id}/recovery/...`), RecoveryPage workstation UI with hex/ASCII inspector & provenance. | `test_r2_recovery_e2e.py` (6/6 passed), `test_phase14_e2e.py` (11/11 passed), `test_zero_storage_e2e.py` (10/10 passed), `npm run build` (0 errors) | Verified complete | Physical carving verified without evidence mutation; zero-disk invariant preserved |


