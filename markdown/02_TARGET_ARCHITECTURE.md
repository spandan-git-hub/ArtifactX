# ArtifactX Target Architecture

## 1. Goal

Evolve ArtifactX from an evidence viewer/inspector into a modular forensic analysis workstation while preserving the existing workstation UX and forensic invariants.

## 2. Layering

```text
React Workstation
      |
      v
FastAPI API Layer
      |
      v
Application Services
      |
      +----------------------+
      |                      |
      v                      v
Forensic Engines        Persistence
      |                      |
      v                      v
Pure Python modules     PostgreSQL
      |
      v
Immutable evidence bytes / derived artifacts
```

## 3. Recommended target package layout

```text
forensic/
  acquisition/
  common/
  whatsapp/
  telegram/
  deleted/
  decryption/
    whatsapp/
    telegram/
  correlation/
  media/
  analysis/
    temporal/
    network/
    financial/
    spatial/
    tamper/
  provenance/
  timeline/
```

Use small modules with typed inputs/outputs. Avoid putting parsing logic in API routers.

## 4. Domain model additions

The existing schema should be extended only where required. Likely new concepts include:
- `derived_artifacts`
- `recovered_records`
- `decryption_operations`
- `analysis_runs`
- `analysis_findings`
- `entities`
- `entity_attributes`
- `media_fingerprints`
- `artifact_occurrences`
- `geolocation_events`
- `tamper_diagnostics`

The exact schema must be reconciled with the existing ORM and migration strategy before implementation.

## 5. Provenance model

Every derived result should be traceable:

```text
case
  -> evidence
      -> evidence_file
          -> operation
              -> derived_artifact
                  -> finding
```

Each operation should capture:
- operation ID;
- parent artifact ID;
- algorithm/method;
- tool version;
- timestamp;
- examiner/operator identity where available;
- input hash;
- output hash;
- parameters that materially affect reproducibility;
- status;
- error information.

## 6. Analysis finding model

A finding is not a conclusion about guilt.

Minimum fields:
- finding ID;
- case ID;
- analysis run ID;
- finding type;
- source artifact IDs;
- method;
- deterministic inputs;
- result payload;
- confidence only when mathematically/algorithmically defined;
- limitations;
- created timestamp.

UI wording must distinguish:
- observed fact;
- derived measurement;
- anomaly flag;
- analyst interpretation.

## 7. Async execution

Large carving/decryption/analysis operations should not block request workers.

Use an explicit job state model:
`QUEUED -> RUNNING -> SUCCEEDED | FAILED | CANCELLED`.

Persist progress and provenance. The first implementation may use a database-backed job runner; do not introduce a distributed queue unless repository constraints require it.

## 8. API design

API routers should:
- validate requests;
- authorize case access;
- invoke services;
- return typed responses;
- never contain binary parsing algorithms.

Long-running operations should return an operation/job identifier and expose status endpoints.

## 9. Frontend architecture

Add analysis workspaces without destroying the current pages.

Suggested additions:
- Recovery page
- Decryption page
- Entity Graph page
- Artifact Correlation page
- Behavioral Analysis page
- Spatial Analysis page
- Integrity/Tamper page

The navigation should remain context-aware and preserve the four-stage workflow.

## 10. Court-report boundary

Court reports may include deterministic, source-linked findings only.

Every report section must declare its source data and method. Experimental or non-validated analysis must be clearly separated from court-exportable content until validated.

## 11. Failure philosophy

Malformed evidence is expected. Engines must:
- fail closed;
- never mutate source bytes;
- report precise errors;
- continue independent analyses where safe;
- never convert uncertainty into a positive finding.
