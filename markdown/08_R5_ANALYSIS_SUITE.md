# R5 — Digital Forensic Analysis Suite

## Objective

Implement deterministic analysis modules so ArtifactX performs analysis rather than only extraction and viewing.

The source framework defines Modules A–E.

## Module A — Temporal and Behavioral Profiling

Create:
`forensic/analysis/temporal/`

Functions:
1. 24x7 day-of-week/hour heatmap.
2. Message-rate curves.
3. Statistical spike detection.
4. Response-latency analysis.
5. Conversation initiation statistics.
6. Communication blackout detection.

The source proposes >3 standard deviations above baseline for spike detection. Make baseline window and sigma threshold configurable and record them.

Avoid language such as "criminal behavior" or "leader" as an algorithmic fact. Report measured communication patterns.

## Module B — Social Network Analysis

Create:
`forensic/analysis/network/`

Implement:
- degree centrality;
- betweenness centrality;
- eigenvector centrality;
- community detection/modularity.

Inputs should be a graph generated from verified communication observations.

Outputs must include:
- metric value;
- graph version;
- normalization;
- source edges;
- algorithm version.

Do not convert centrality into a claim of criminal hierarchy without analyst interpretation.

## Module C — Financial/Crypto/Network Artifact Extraction

Create:
`forensic/analysis/financial/`

Deterministic detectors for:
- Bitcoin address formats;
- EVM addresses;
- Monero candidates;
- Tron/USDT candidates;
- IBAN with checksum validation;
- SWIFT/BIC;
- routing/payment identifiers;
- credit-card candidates with Luhn validation;
- `.onion` addresses;
- proxy endpoints;
- API/private-key/seed-like strings.

### Handling of secrets
Never place discovered private keys, passwords, seed phrases, or credentials into normal application logs.

Access to sensitive artifact values should be controlled and audited.

## Module D — Spatial/Trajectory Analysis

Create:
`forensic/analysis/spatial/`

Implement:
- unified geolocation timeline;
- Haversine distance;
- elapsed time;
- velocity;
- impossible-transit anomaly;
- simultaneous distant-location activity;
- proximity/rendezvous.

The source gives 900 km/h as an example threshold for land travel. Treat this as configurable, not universal physical truth.

Every anomaly should expose the two source observations and the calculation.

## Module E — Anti-Forensics/Tamper Diagnostics

Create:
`forensic/analysis/tamper/`

Implement:
- SQLite header inspection;
- page-size validation;
- change-counter inspection;
- schema-cookie inspection;
- freelist statistics;
- database/page-size consistency checks;
- timestamp ordering anomalies;
- clock-skew diagnostics.

An anomaly means "requires examination", not proof of tampering.

## Analysis run contract

Each run:
- receives a case ID;
- snapshots the relevant source hashes;
- stores parameters;
- runs deterministic algorithms;
- persists findings;
- stores errors;
- records tool version.

## UI

Add a unified Analysis page with tabs:
- Temporal
- Network
- Financial
- Spatial
- Integrity

Each visualization must have:
- data source;
- calculation/method;
- parameter display;
- exportable underlying records.

## Court export

Only validated deterministic outputs should become report sections. Experimental findings must remain explicitly separated until validation is complete.
