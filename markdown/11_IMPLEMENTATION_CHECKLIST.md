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

- [ ] Remove `backend/api/assistant.py`
- [ ] Remove `backend/services/assistant_service.py`
- [ ] Remove `ForensicAssistantDrawer.jsx`
- [ ] Remove `useAiAssistant.js`
- [ ] Remove `assistantService.js`
- [ ] Remove assistant router include
- [ ] Remove assistant UI triggers
- [ ] Remove assistant frontend route/state references
- [ ] Remove assistant-only dependencies
- [ ] Repository-wide assistant reference audit complete
- [ ] No sentiment/suspicion code remains active
- [ ] Court report contains no AI-derived fields
- [ ] R1 backend tests pass
- [ ] R1 frontend build passes

# C. Zero-Local-Storage Hardening

- [ ] Upload stream hashes without persistent local staging
- [ ] Evidence binary stored in PostgreSQL
- [ ] ZIP members stored in PostgreSQL
- [ ] SQLite parser accepts memory/stream input
- [ ] Media parser accepts memory/stream input
- [ ] Derived artifacts have parent hashes
- [ ] Report generation uses `BytesIO`
- [ ] `uploads/` remains empty
- [ ] `reports/` remains empty
- [ ] Zero-disk integration test passes
- [ ] No sensitive material appears in logs

# D. R2 — Physical Recovery

- [ ] WAL header parser
- [ ] WAL frame parser
- [ ] WAL page reconstruction
- [ ] Freelist header parser
- [ ] Freelist trunk traversal
- [ ] Freelist leaf-page scanner
- [ ] B-tree page parser
- [ ] Cell/freeblock/slack scanner
- [ ] SQLite varint decoder
- [ ] SQLite serial-type decoder
- [ ] SQLite record decoder
- [ ] WhatsApp payload candidate decoder
- [ ] Telegram payload candidate decoder
- [ ] Recovery provenance schema
- [ ] Recovery API
- [ ] Recovery UI
- [ ] Synthetic deletion fixtures
- [ ] Malformed SQLite fixtures
- [ ] False-positive tests
- [ ] Source immutability test
- [ ] R2 acceptance gate passed

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

**Last completed phase:** Phase A — Baseline Preservation

**Current active phase:** Phase B — R1 AI Excision

**Current active task:** Plan and prepare Phase B (AI Excision: assistant router, service, UI drawer, hook)

**Blocking issue:** None

**Last successful test command:** `$env:PYTHONPATH="d:\ArtifactX"; python backend\scripts\test_phase14_e2e.py`

**Last verified commit/change:** Baseline snapshots captured in `snapshots/` (`baseline_schema.json`, `baseline_schema.sql`, `baseline_openapi.json`, `baseline_test_phase14.log`, `baseline_system_state.json`)

**Next action:** Review Phase B implementation plan and execute surgical AI excision

**Date/time updated:** 2026-09-17 21:50:00 UTC+05:30

## Change log

| Date | Phase | Change | Tests | Status | Notes |
|---|---|---|---|---|---|
| 2026-09-17 | Phase A | Captured DB schema (18 tables), OpenAPI contract (70 routes, 2 assistant endpoints), full Phase 14 regression run (11/11 passed, 0 workspace PDFs), system metadata, and frontend build verification (vite build 0 errors). | `test_phase14_e2e.py` (11/11), `npm run build` | Verified complete | Baseline frozen in `snapshots/` prior to R1 |

