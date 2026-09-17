# ArtifactX Evidence Storage and Zero-Local-Disk Design

## Objective

Make database-backed evidence persistence and ephemeral processing the default architecture.

The supplied specification explicitly requires evidence packages, extracted artifacts, media, and report outputs to be stored in PostgreSQL or processed in memory, with `uploads/` and `reports/` remaining empty.

## 1. Intake pipeline

```text
HTTP upload
  -> bounded streaming reader
  -> incremental SHA-256 / SHA-1 / MD5
  -> PostgreSQL evidence blob
  -> manifest rows
  -> audit event
```

Do not first write the upload to `uploads/`.

## 2. Database representation

For each stored binary object retain:
- object ID;
- parent evidence ID;
- original filename;
- relative path where applicable;
- MIME type;
- byte length;
- SHA-256;
- optional MD5/SHA-1;
- content bytes (`BYTEA` or equivalent);
- created timestamp;
- provenance metadata.

For very large evidence, use a database-supported large-object mechanism if appropriate, while retaining the same logical model.

## 3. Archive extraction

Do not extract ZIP members to local disk.

Preferred approach:
1. stream archive bytes from database;
2. inspect archive metadata;
3. enforce path traversal protection;
4. stream each member into bounded memory;
5. hash the member;
6. persist member bytes to the database;
7. create `evidence_files` manifest row.

Never trust archive filenames.

## 4. Parser handoff

Parsers should accept one of:
- bytes;
- `BinaryIO`;
- immutable database-backed stream adapter.

A parser must not assume a filesystem path.

Where SQLite tooling requires random access, provide an in-memory or database-backed seekable abstraction.

## 5. Derived artifacts

Examples:
- decrypted SQLite database;
- decrypted media;
- recovered record payload;
- normalized media representation.

Store these as derived artifacts linked to the exact parent hash and operation.

## 6. Report generation

Generate PDF into `io.BytesIO`, hash the exact byte stream, persist report metadata, then stream the same bytes to the client.

The report history must identify:
- report ID;
- case;
- report type;
- filename;
- size;
- page count;
- SHA-256;
- generation timestamp;
- generating operation.

## 7. Zero-disk tests

Automated tests must monitor the application workspace and assert:
- no evidence files are created;
- no extracted databases are created;
- no decrypted media is created;
- no PDF is created;
- no temporary cache survives a request.

Tests should also verify database contents and output hashes.

## 8. Sensitive-memory handling

Avoid unnecessary copies of large binary evidence. Release references promptly after processing.

Keys, passcodes, and decrypted payloads should have the smallest possible lifetime in application memory.

Never log:
- raw encryption keys;
- passcodes;
- private keys;
- full credential values.

## 9. Migration strategy

Before changing existing `evidence` / `evidence_files`:
1. inspect actual models;
2. identify current `storage_path` semantics;
3. add binary/provenance fields;
4. migrate existing records safely;
5. update services;
6. remove filesystem assumptions;
7. run regression tests.

Do not drop old columns until all consumers are migrated and verified.
