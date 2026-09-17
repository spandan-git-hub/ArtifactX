# ArtifactX Baseline, Current State, and Non-Negotiable Invariants

## 1. Current baseline

ArtifactX is an end-to-end digital forensic workstation with:
- case registry and case workspace;
- evidence ingestion and hashing;
- WhatsApp and Telegram extraction;
- deletion-gap detection;
- timeline reconstruction;
- cross-platform correlation prototype;
- media/EXIF inspection;
- SQLite inspection;
- court PDF generation and report history;
- audit/error logs;
- demo case generation.

The supplied compendium records Phases 0–14 as complete and Phase 15 as built but slated for removal.

## 2. Existing backend structure

Key areas:
- `backend/api/`
- `backend/app/`
- `backend/models/`
- `backend/repositories/`
- `backend/schemas/`
- `backend/services/`
- `backend/utils/`
- `backend/scripts/`

Existing routers include cases, chats, evidence, WhatsApp, Telegram, timeline, deleted, correlation, search, dashboard, reports, logs, demo, media, and health. The assistant router is legacy and must be removed in R1.

## 3. Existing forensic structure

`forensic/` is deliberately independent of FastAPI and SQLAlchemy.

Existing domains:
- `forensic/whatsapp/`
- `forensic/telegram/`
- `forensic/deleted/`
- `forensic/timeline/`
- `forensic/correlation/`
- `forensic/media/`

Keep pure parsing/carving/analysis algorithms independent from HTTP and ORM concerns.

## 4. Existing frontend structure

The frontend is a React/Vite workstation with:
- case registry;
- case workspace;
- dashboard;
- evidence;
- chat;
- timeline;
- correlation;
- reports;
- logs;
- search.

The UI uses a dense forensic workstation style and a four-stage workflow:
1. Ingestion & Hashing
2. Extract & Parse
3. Analyze & Correlate
4. Court Export

## 5. Database baseline

The source describes 17 existing tables:
`cases`, `evidence`, `evidence_files`, `analysis_results`, `wa_messages`, `wa_contacts`, `wa_groups`, `tg_messages`, `tg_contacts`, `tg_groups`, `timeline_events`, `deleted_messages`, `media_items`, `correlation_edges`, `generated_reports`, `activity_logs`, `error_logs`.

Before changing schema, inspect actual ORM/DDL rather than assuming the compendium's summary is byte-for-byte identical to the repository.

## 6. Non-negotiable forensic invariants

### Evidence integrity
- Never mutate original evidence bytes.
- Record cryptographic hashes at intake.
- Preserve parent-child provenance for derived artifacts.
- Make analysis reproducible from the stored evidence.

### Determinism
- Court-report facts must be deterministic and traceable.
- Every derived finding must identify its source evidence and method.
- Never invent findings in live mode.

### Auditability
Log:
- intake;
- hash verification;
- parser execution;
- carving;
- decryption;
- derivation;
- analysis;
- report generation;
- failures.

### Zero-local-disk target
The strategic requirement is that evidence, extracted payloads, media, and generated reports are not persisted to application-local disk. Prefer PostgreSQL `BYTEA`/large-object storage or ephemeral `BytesIO` streams.

If an unavoidable third-party library requires a filesystem path, isolate it in a tightly controlled temporary mechanism and ensure the architecture documents, audits, and cleans it. Do not silently violate the invariant.

### Demo isolation
Demo data must remain explicitly tagged and must never be mistaken for live evidence.

## 7. What must not return

Do not reintroduce:
- AI copilot;
- sentiment classification;
- suspicion scores;
- subjective threat/deception labels;
- hidden AI-derived conclusions in court reports.

R1 is a deletion/refactor, not a rename.

## 8. Change discipline

Every implementation change must answer:
- Which requirement does this satisfy?
- Which source evidence does it operate on?
- Is it deterministic?
- What is its provenance?
- What database changes are required?
- What API contract changes are required?
- What frontend state changes are required?
- What tests prove it?
- What happens on malformed/adversarial evidence?
