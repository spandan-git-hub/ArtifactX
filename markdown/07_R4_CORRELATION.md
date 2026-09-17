# R4 — Deep Cross-Platform Correlation Engine

## Objective

Replace the prototype's simple phone-number/time-window correlation with a multi-entity, multi-artifact correlation system.

The source roadmap calls for:
- Person entity graph;
- platform handover detection;
- perceptual media hashing;
- shared artifact stitching.

## 1. Identity graph

Create:
`forensic/correlation/entities.py`

Entity types:
- Person
- Account
- PhoneNumber
- WhatsAppJID
- TelegramUser
- TelegramHandle
- ContactAlias
- MediaIdentity

A Person node is a hypothesis-backed resolution object, not an assertion of real-world identity.

Each edge must have:
- relation type;
- source observations;
- method;
- strength/score if mathematically defined;
- provenance;
- limitations.

## 2. Identity resolution

Candidate signals:
- normalized E.164 phone;
- Telegram user ID;
- username;
- address-book relationships;
- aliases;
- avatar/media fingerprints;
- co-occurrence patterns.

Never merge two identities solely because names look similar.

## 3. Platform handover

Create:
`forensic/correlation/handover.py`

Detect:
- conversation end on one platform;
- conversation start on another;
- temporal proximity;
- explicit handover language.

The source proposes a 180-second temporal threshold. Make this configurable and record the actual threshold in the operation parameters.

Do not label a handover as surveillance evasion merely because it meets a time threshold. Use neutral wording such as `PLATFORM_HANDOVER_CANDIDATE`.

## 4. Perceptual media correlation

Create:
`forensic/correlation/media_hash.py`

Compute pHash/dHash where applicable.

The source proposes Hamming distance <= 4 as a linkage threshold. Treat that as a configurable hypothesis until validated against representative data.

Record:
- algorithm;
- hash;
- image normalization parameters;
- distance;
- threshold;
- source media hashes.

## 5. Shared artifact stitching

Create:
`forensic/correlation/artifacts.py`

Extract deterministic artifact classes such as:
- cryptocurrency addresses;
- IBANs;
- SWIFT/BIC;
- UPI handles;
- tracking codes;
- flight numbers;
- analyst-configured code words.

Every regex hit must undergo format validation where possible.

## 6. Spatiotemporal rendezvous

Create:
`forensic/correlation/rendezvous.py`

Inputs:
- EXIF GPS;
- shared locations;
- Telegram location events;
- timestamps.

The source proposes:
- <50 meters;
- <30 minutes.

Make thresholds configurable and retain uncertainty/error margins.

## 7. Graph output

Return a stable JSON graph:
```json
{
  "nodes": [],
  "edges": [],
  "metadata": {
    "algorithm_version": "",
    "parameters": {}
  }
}
```

## 8. API

Suggested:
- `POST /api/cases/{case_id}/correlation/deep/run`
- `GET /api/cases/{case_id}/correlation/entities`
- `GET /api/cases/{case_id}/correlation/handover`
- `GET /api/cases/{case_id}/correlation/media`
- `GET /api/cases/{case_id}/correlation/artifacts`
- `GET /api/cases/{case_id}/correlation/rendezvous`

Preserve compatibility with existing correlation endpoints where feasible.

## 9. UI

Show:
- identity graph;
- evidence behind each edge;
- thresholds;
- source artifacts;
- cross-platform handovers;
- media matches;
- shared artifacts;
- geographic co-occurrence.

Every graph edge must be drillable to its underlying evidence.
