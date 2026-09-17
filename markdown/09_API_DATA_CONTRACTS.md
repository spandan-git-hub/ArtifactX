# ArtifactX API and Data Contract Plan

## Purpose

Prevent frontend/backend drift while R1–R5 are implemented.

## Contract rules

1. All IDs are stable and explicit.
2. Dates/times are ISO 8601 UTC unless a field explicitly represents source-local time.
3. Hashes are lowercase hexadecimal unless existing API conventions require otherwise.
4. Every derived finding exposes provenance.
5. Long-running operations return an operation/job ID.
6. Error responses are structured and do not expose secrets.

## Common operation response

```json
{
  "operation_id": "uuid",
  "status": "QUEUED",
  "created_at": "2026-01-01T00:00:00Z"
}
```

Statuses:
`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.

## Common provenance response

```json
{
  "source_artifact_id": "uuid",
  "source_sha256": "64-hex",
  "method": "string",
  "algorithm_version": "string",
  "parameters": {},
  "created_at": "ISO-8601"
}
```

## Recovery contract

```json
{
  "id": "uuid",
  "source_file_id": "uuid",
  "source_sha256": "64-hex",
  "source_app": "whatsapp|telegram",
  "method": "wal|freelist|slack|record_reconstruction",
  "offset": 0,
  "page_number": 0,
  "validation_status": "CANDIDATE",
  "body": null,
  "timestamp": null,
  "sender_id": null,
  "limitations": []
}
```

## Decryption contract

Never return key material.

```json
{
  "operation_id": "uuid",
  "format": "crypt14|crypt15|sqlcipher|enc|mtproto",
  "status": "SUCCEEDED",
  "input_sha256": "64-hex",
  "output_sha256": "64-hex",
  "derived_artifact_id": "uuid",
  "validation": {
    "sqlite_integrity_check": "ok"
  }
}
```

## Entity-resolution contract

```json
{
  "entity_id": "uuid",
  "entity_type": "PERSON",
  "attributes": [],
  "evidence_links": [],
  "resolution_method": "string",
  "limitations": []
}
```

## Analysis finding contract

```json
{
  "finding_id": "uuid",
  "type": "string",
  "status": "OBSERVED|DERIVED|ANOMALY|CANDIDATE",
  "value": {},
  "method": "string",
  "parameters": {},
  "sources": [],
  "limitations": []
}
```

## Frontend service organization

Add service wrappers by domain:
- `recoveryService`
- `decryptionService`
- `deepCorrelationService`
- `analysisService`
- `operationsService`

Keep Axios configuration centralized.

## Compatibility

Do not break the existing Phase 0–14 endpoints without a deliberate migration. Where a new endpoint supersedes an old endpoint, document both and add regression tests.
