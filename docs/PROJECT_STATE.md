# ArtifactX — Current Project State (Post-Cleanup)

> **Status:** Phase A (Required Cleanup) Complete  
> **Last Updated:** 2026-10-13  
> **Reference:** Supersedes `REPORTBYSONNET.md` per `AUDIT_A0.md`

---

## 1. Executive Summary

ArtifactX is a digital forensic analysis workstation designed for inspecting, parsing, recovering, and correlating digital artifacts from WhatsApp and Telegram evidence.

Following the Phase A cleanup (A0–A7), the repository has been audited and brought into strict conformance with forensic engineering principles:
- **Truth over appearance (R1, R7):** No fake capabilities, unvalidated decryptors, or unsupported format claims.
- **Zero runtime disk writes for evidence (R4):** All evidence ingestion, hash verification, and binary retrieval occur strictly in-memory (`content_bytes` in database) or via memory-deserialized SQLite connections.
- **Defensible reporting & objective terminology (R9):** Elimination of unsubstantiated claims ("court-ready", "legally admissible", "tamper-proof"). Reports are structured as Forensic Evidence Reports marked "Draft for expert review".
- **Strict test isolation & security (R5, R13, R14):** Test suite is isolated from production infrastructure, network access is blocked in tests, and secret leakage guards are active.

---

## 2. Repository Structure

```
ArtifactX/
├── backend/                  # FastAPI REST backend
│   ├── api/                  # 16 active API routers (modular endpoints)
│   ├── app/                  # FastAPI app factory, config, DB session management
│   ├── models/               # SQLAlchemy ORM models (26 models)
│   ├── repositories/         # Data access layer
│   ├── schemas/              # Pydantic v2 validation and serialization schemas
│   ├── services/             # Core application and forensic service logic
│   └── utils/                # In-memory cryptographic and extraction utilities
├── forensic/                 # Pure forensic parsing and analysis modules
│   ├── correlation/          # Cross-evidence correlation engines
│   ├── decryption/           # Decryption orchestrator & Decryptor plugin protocol
│   ├── deleted/              # Deleted record recovery and gap detection
│   ├── media/                # EXIF extraction and media analysis
│   ├── telegram/             # Telegram parser and entity extractors
│   ├── timeline/             # Multi-source timeline constructor
│   └── whatsapp/             # WhatsApp SQLite database parser
├── frontend/                 # Single-page application (React 18 + Vite + Tailwind CSS)
│   ├── src/components/       # Modular UI components (Cases, Evidence, Timeline, Reports)
│   ├── src/pages/            # View pages
│   └── src/services/         # API client services
├── tests/                    # Automated test suite
│   ├── conftest.py           # Isolation fixtures, network blocking, DB sandboxing
│   ├── unit/                 # Unit tests (models, guards, utilities)
│   └── integration/          # Integration tests (API contracts, DB workflows)
├── tools/
│   └── guards/               # Automated AST and regex guard-rails
│       ├── banned_language.py
│       ├── no_disk_write.py
│       ├── forbidden_imports.py
│       ├── secret_leak.py
│       ├── no_demo_seed.py
│       ├── no_assistant_sentiment.py
│       └── run_all.py
├── docs/                     # Verified living documentation
│   ├── AUDIT_A0.md           # Baseline discrepancy audit
│   ├── API_CHANGES.md        # API contract change log
│   ├── DEPENDENCIES.md       # Dependency inventory and licensing
│   ├── LIMITATIONS.md        # Explicit forensic boundaries and constraints
│   └── PROJECT_STATE.md      # This file
└── Project Files/            # Implementation specifications and master checklist
```

---

## 3. Subsystem Breakdown & Verified Status

### 3.1 Backend Application & Database
- **Framework:** FastAPI with Uvicorn.
- **Database Support:** SQLAlchemy 2.0 ORM with PostgreSQL (NullPool for serverless Neon in staging/production) and SQLite (StaticPool with `:memory:` isolation for testing).
- **Portability:** Database models use standard SQLAlchemy portable types (`JSON`, `LargeBinary`, `DateTime`, `Integer`, `String`, `Boolean`). No Postgres-specific JSONB or ARRAY locking.
- **Database Migrations:** Managed by Alembic. Baseline schema migration `a77eef711395` and integrity state migration `da9ec651c70b`. Neon production migrations are strictly governed (R17).

### 3.2 Evidence Ingestion & Storage (Zero-Disk Storage)
- **Runtime Storage:** `uploads/` and `reports/` directories and filesystem fallbacks are completely eliminated.
- **Binary Evidence:** Evidence payload is held in `evidence_files.content_bytes` (LargeBinary).
- **Legacy Row Accounting:** Historical evidence rows lacking binary database content are flagged `integrity_state="LEGACY_UNVERIFIABLE"`; hash verification reports `verification_status="LEGACY_UNVERIFIABLE"` and never claims integrity without verifiable bytes.
- **Upload Size Limit:** Configured default `max_upload_size = 268435456` bytes (256 MiB). Memory consumption during processing is documented at ~2–3× file size.

### 3.3 Decryption Engine
- **Decoupled Architecture:** `forensic.decryption.orchestrator.DecryptionOrchestrator` implements a `Decryptor` plugin protocol (`can_handle`, `decrypt`).
- **Demoted/Removed Unvalidated Engines (A6):**
  - Telegram SQLCipher and Telegram MTProto removed (Android `cache4.db` is plain SQLite; network-traffic `auth_key` out of scope).
  - WhatsApp `.enc` media decryptor removed pending verified test fixture.
  - Legacy WhatsApp `crypt12/14/15` classes unregistered from orchestrator pending clean, differential-tested implementations in Phase B6.
- **Status Contract:** Invoking `/decryption/run` without a registered validated engine returns HTTP 200 with typed state `status="DECRYPTOR_NOT_AVAILABLE"`.
- **Entropy Detection:** Unknown high-entropy files (>7.5 bits/byte without recognized container magic) are reported honestly as `UNKNOWN_ENCRYPTED_KEY_REQUIRED` with no format claim. Standard compressed containers (ZIP, JPEG, PNG, MP4, etc.) are excluded by magic bytes from false encryption claims.

### 3.4 Forensic Parsers & Analysis
- **WhatsApp Parser (`forensic/whatsapp/parser.py`):** Parses unencrypted `msgstore.db` SQLite databases (messages, chats, participants).
- **Telegram Parser (`forensic/telegram/parser.py`):** Parses unencrypted Android Telegram `cache4.db` SQLite databases.
- **Timeline Engine (`forensic/timeline/builder.py`):** Aggregates chronological events across WhatsApp and Telegram.
- **Deleted Data Detection (`forensic/deleted/detector.py`):** Detects message revocations and identifies ID sequence gaps (demoted to weak heuristic indicators; confidence capped at ≤0.30 per DEC-014).
- **Correlation Engine (`forensic/correlation/`):** Identifies shared phone numbers, cryptocurrency addresses, and near-duplicate images across artifacts.

### 3.5 Reporting & Export
- **Engine:** ReportLab generating PDF documents entirely in-memory via `io.BytesIO`.
- **Terminology:** All outputs standardized to "Forensic Evidence Report" (full) or "Forensic Summary Report" (short), accompanied by "Draft for expert review".
- **Default Filename:** Standardized to `ArtifactX_ForensicReport_Case{case_id}.pdf`.

### 3.6 Frontend Client
- **Stack:** React 18 with Vite.
- **Cleaned Components:**
  - Removed all demo mode components (`DemoModal.jsx`, `demoService.js`) and toggles.
  - Removed all AI assistant components (`ForensicAssistantDrawer.jsx`, `useAiAssistant.js`, `assistantService.js`).
  - Stage 4 in workflow stepper renamed to "Report Export".
  - Build verified passing cleanly (`npm run build`).

---

## 4. Test Suite & Verification Infrastructure

- **Pytest Suite:** 47 automated tests passing across unit and integration categories.
- **Isolation Guarantees:**
  - Network sockets are intercepted and blocked during test runs.
  - `conftest.py` validates that `DATABASE_URL` is never pointing to production host (e.g. `neon.tech`).
- **Static Guard-Rails (`tools/guards/run_all.py`):**
  - `banned_language.py`: Enforces elimination of prohibited marketing and legal assertions.
  - `no_disk_write.py`: Prevents disk write calls (`open(..., 'w')`, `Path.write_*`) across `backend/` and `forensic/`.
  - `secret_leak.py`: Prevents tracked `.env` files, real credentials, and raw private keys.
  - `no_demo_seed.py`: Prevents reintroduction of demo or mock seeding code.
  - `no_assistant_sentiment.py`: Prevents reintroduction of assistant or sentiment analysis code.
  - `forbidden_imports.py`: Enforces strict layering boundaries (pre-existing 9 violations in `media/orphan.py` and `timeline/builder.py` scheduled for resolution in Phase B11/B12).

---

## 5. Roadmap: Transition to Phase B

With Phase A (Cleanup) completed, the codebase is primed for Phase B (Full Functional Pipeline):
1. **B1–B4:** Ground-truth synthetic dataset generation with deterministic RNG, verifiable manifests, and negative fixtures.
2. **B5:** Hardened evidence ingestion, size limits, streaming uploads, and hash-chained audit logging.
3. **B6:** Independent, differential-tested WhatsApp crypt14 and crypt15 decryptors.
4. **B7–B10:** Schema-guided WhatsApp parsing, pure SQLite forensic carving (freelist, WAL, unallocated cells), Telegram TL blob deserialization, and tiered deleted data recovery.
5. **B11–B13:** Canonical timeline construction, deep entity correlation with strict threshold calibration, and end-to-end pipeline execution.
