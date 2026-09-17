# ArtifactX Agentic Build Pack

## Purpose
This directory is the implementation-control layer for ArtifactX. An agentic coding system should read these files before modifying the repository.

## Source of truth
The supplied project compendium is the authoritative source for the current as-built state and intended R1–R5 roadmap. It describes:
- the existing React 18 + Vite frontend;
- FastAPI + Python backend;
- PostgreSQL persistence;
- the standalone `forensic/` package;
- the four-stage forensic workflow;
- court-report generation;
- the R1–R5 strategic roadmap.

The current prototype has already completed Phases 0–14 and has Phase 15 AI functionality that is explicitly slated for removal. Do not treat the old AI feature as a future requirement.

## Reading order
1. `01_BASELINE_AND_INVARIANTS.md`
2. `02_TARGET_ARCHITECTURE.md`
3. `03_STORAGE_AND_EVIDENCE_MODEL.md`
4. `04_R1_AI_EXCISION.md`
5. `05_R2_DELETED_RECOVERY.md`
6. `06_R3_DECRYPTION.md`
7. `07_R4_CORRELATION.md`
8. `08_R5_ANALYSIS_SUITE.md`
9. `09_API_DATA_CONTRACTS.md`
10. `10_TESTING_AND_ACCEPTANCE.md`
11. `11_IMPLEMENTATION_CHECKLIST.md`

## Agent operating rule
Do not implement an entire phase from memory. Before editing code:
1. inspect the existing repository;
2. identify the exact files/classes/routes affected;
3. make the smallest coherent change;
4. run the phase's tests;
5. update the checklist;
6. do not begin the next phase until acceptance criteria pass.

## Evidence and legal posture
ArtifactX is intended to preserve and analyze digital evidence. Original evidence must be handled non-destructively. Derived artifacts must retain provenance and cryptographic linkage to their parent evidence.

AI-generated inference, sentiment labels, suspicion scores, or copilot answers are not part of the court-evidence model and are removed by R1.

## Important implementation qualification
The source compendium contains proposed cryptographic/decryption details and examples. Treat protocol-specific values, offsets, algorithms, library behavior, and vendor-format assumptions as implementation hypotheses requiring validation against authoritative format specifications and controlled forensic test images before being relied upon.

## Security boundary
All decryption, carving, credential/key handling, and artifact extraction functionality is for evidence that the examiner is legally authorized to process. Build explicit authorization, audit logging, rate limiting, and safe failure behavior into operational tooling. Never silently fall back to destructive or uncontrolled credential guessing.
