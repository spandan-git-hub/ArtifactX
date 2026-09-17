# ArtifactX Testing and Phase Acceptance

## Testing philosophy

A successful build is not a successful forensic implementation.

Each phase requires:
1. unit tests;
2. malformed-input tests;
3. integration tests;
4. provenance tests;
5. zero-disk tests where relevant;
6. frontend build/lint tests;
7. API contract tests;
8. regression against previously working behavior.

## Global acceptance gates

### Repository
- no syntax/import errors;
- no dead references to removed modules;
- no secrets committed;
- deterministic dependency installation.

### Evidence
- source bytes remain unchanged;
- input hash remains stable;
- derived output hash is recorded;
- provenance is queryable.

### Storage
- no persistent evidence/report files on application disk;
- all binary artifacts are database-backed or ephemeral;
- failed operations do not leave residue.

### API
- OpenAPI reflects current routes;
- schemas validate;
- errors are structured;
- unauthorized/malformed inputs fail safely.

### Frontend
- production build succeeds;
- routes load;
- empty/loading/error states work;
- provenance is visible where a finding is displayed.

## R1 acceptance

- assistant code removed;
- assistant routes absent;
- AI UI absent;
- evidence/report storage uses DB/memory;
- zero-disk tests pass;
- legacy regression suite passes.

## R2 acceptance

- WAL fixtures recover known records;
- freelist fixtures recover known records;
- slack fixtures identify known candidate bytes;
- varint/record decoder passes boundary tests;
- false positives are labeled candidates;
- exact offsets and hashes are persisted;
- source files are unmodified.

## R3 acceptance

For each supported format:
- valid input decrypts;
- wrong key fails;
- altered ciphertext fails validation;
- truncated input fails safely;
- plaintext SQLite passes integrity validation;
- decrypted media passes file validation;
- keys/passcodes never appear in logs;
- no plaintext file remains on disk.

## R4 acceptance

- identity graph is reproducible;
- thresholds are configurable;
- every edge has source evidence;
- media hash matching is deterministic;
- artifact detectors validate formats;
- rendezvous calculations expose distance/time;
- ambiguous identity matches are not presented as facts.

## R5 acceptance

- temporal metrics reproduce from fixtures;
- centrality metrics match reference calculations;
- artifact regex/checksum validators pass;
- spatial calculations match known coordinates;
- tamper diagnostics detect synthetic inconsistencies;
- every finding has a method and source.

## Court-report acceptance

A report must:
- contain only selected deterministic sections;
- contain source/provenance identifiers;
- include cryptographic hashes;
- be generated in memory;
- persist exact output SHA-256;
- re-download to identical bytes;
- leave zero report files on server disk.

## Release gate

Do not mark a phase complete until:
- all phase-specific tests pass;
- all global gates pass;
- checklist is updated;
- implementation notes document deviations from the source specification.
