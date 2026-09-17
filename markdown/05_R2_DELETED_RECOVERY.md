# R2 — True Deleted Message Recovery / SQLite Physical Carving

## Objective

Upgrade deletion analysis from sequence-gap detection to non-destructive physical recovery attempts.

The source roadmap calls for:
- SQLite WAL frame parsing;
- freelist leaf-page carving;
- B-tree cell slack-space extraction;
- schema-adaptive payload reconstruction.

## Safety boundary

Only process evidence the examiner is authorized to analyze.

Recovery is probabilistic at the byte level: a carved byte sequence is not automatically a valid deleted message. Every recovered record must retain:
- source file hash;
- page/frame offset;
- carving method;
- raw byte span;
- parser version;
- reconstruction status;
- validation evidence;
- uncertainty/limitations.

## 1. WAL parser

Create a pure module such as:
`forensic/deleted/wal_carver.py`

Responsibilities:
- validate WAL header;
- validate frame boundaries;
- parse frame headers;
- associate page numbers with frames;
- expose immutable page images;
- identify candidate historical pages;
- never modify the WAL or database.

Do not assume a single SQLite page size. Read it from the database header where available and validate WAL compatibility.

## 2. Freelist carver

Create:
`forensic/deleted/freelist_carver.py`

Responsibilities:
- parse SQLite database header;
- locate freelist trunk;
- validate trunk/leaf pointers;
- inspect freed pages;
- enumerate candidate cells;
- retain exact byte offsets.

Malformed pointers must produce diagnostics rather than arbitrary memory access.

## 3. Cell slack scanner

Create:
`forensic/deleted/slack_carver.py`

Responsibilities:
- parse page structure;
- distinguish cell-pointer area, cell content, freeblocks, and unused regions;
- scan residual bytes conservatively;
- produce candidate UTF-8/binary spans;
- attach offsets and source page identity.

Do not treat arbitrary printable strings as messages without structural validation.

## 4. SQLite record decoder

Create:
`forensic/deleted/sqlite_record.py`

Implement:
- varint decoding;
- serial-type decoding;
- record header parsing;
- integer/text/blob/null interpretation;
- overflow-page handling where necessary.

All decoders must enforce bounds.

## 5. WhatsApp payload reconstruction

Create a schema-adaptive reconstruction layer.

Candidate evidence may include:
- message body;
- remote JID;
- timestamp;
- media references.

Do not hard-code one protobuf layout as universally valid. Support versioned decoders and retain the raw payload.

## 6. Telegram reconstruction

Provide a separate decoder path for Telegram candidate records. Do not reuse WhatsApp assumptions.

## 7. Recovered record model

Suggested fields:
- `id`
- `case_id`
- `evidence_id`
- `source_file_id`
- `source_app`
- `method`
- `page_number`
- `byte_offset`
- `raw_payload_hash`
- `message_id`
- `chat_id`
- `sender_id`
- `body`
- `timestamp`
- `media_reference`
- `validation_status`
- `limitations`
- `created_at`

## 8. API

Suggested endpoints:
- `POST /api/cases/{case_id}/recovery/run`
- `GET /api/cases/{case_id}/recovery/runs`
- `GET /api/cases/{case_id}/recovery/findings`
- `GET /api/cases/{case_id}/recovery/findings/{finding_id}`

## 9. UI

Add a Recovery workspace showing:
- source evidence;
- recovery method;
- page/frame location;
- raw payload preview;
- reconstructed fields;
- validation status;
- provenance;
- limitations.

Use explicit labels such as:
`RECOVERED`, `PARTIALLY_RECONSTRUCTED`, `CANDIDATE`, `UNVALIDATED`.

Never display a candidate as an ordinary confirmed message.

## 10. Tests

Build synthetic SQLite fixtures that deliberately create:
- deleted rows;
- WAL-only historical states;
- freelist pages;
- freeblocks;
- cell slack;
- malformed records.

Verify:
- exact offsets;
- no source mutation;
- correct varint handling;
- false-positive resistance;
- deterministic output.
