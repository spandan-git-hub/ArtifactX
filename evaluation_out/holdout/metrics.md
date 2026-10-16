# ArtifactX — Empirical Evaluation and Metrics Report

> [!WARNING]
> **SYNTHETIC DATASET CAVEAT (master.md R1, R7, 12_METRICS_AND_EVALUATION.md):**
> All metrics in this report were evaluated against synthetic ground-truth fixtures modelled on documented application schemas.
> No key-less decryption is performed. Real-device hardware capture validation is deferred to V1.
> All confidence scores are heuristic rankings and do NOT represent probabilistic proof or legal guilt.

**Evaluation Variant:** `holdout`  
**Git Commit:** `4bb760ded463b493e953a15bb963a67cea1f2a5f`  
**Thresholds Version:** `1.0.0`  
**Python:** `3.14.6` | **SQLite:** `3.53.1` | **OS:** `Windows`  

---
## 1. Executive Summary & Integrity Metrics

| Metric | Target | Result (Wilson 95% CI) | Status |
|---|---|---|---|
| Re-hash Stability | 100.0% | 100.0% (N=75, 95% CI [95.1%, 100.0%]) | PASS |
| False Alarm Rate | 0.0% | 0.0% (N=75, 95% CI [0.0%, 4.9%]) | PASS |
| Single-Byte Mutation Detection | 100.0% | 100.0% (N=24, 95% CI [86.2%, 100.0%]) | PASS |
| Audit Chain Tamper Detection | 100.0% | 100.0% (N=10, 95% CI [72.2%, 100.0%]) | PASS |

---
## 2. Decryption Parity & Cryptographic Handling

| Metric | Target | Result (Wilson 95% CI) | Status |
|---|---|---|---|
| Decryption Parity (Crypt14/15) | 100.0% | 100.0% (N=2, 95% CI [34.2%, 100.0%]) | PASS |
| Negative Typed-Error Rate | 100.0% | 100.0% (N=2, 95% CI [34.2%, 100.0%]) | PASS |
| Key Redaction Compliance (Rule R5) | 100.0% | 100.0% (N=1, 95% CI [20.7%, 100.0%]) | PASS |
| Succeeded Where Reference Failed | 0 | 0 | PASS |

---
## 3. Parsing Accuracy

| Domain | Target | Accuracy (Wilson 95% CI) | Miss Count | Unparsed Blobs |
|---|---|---|---|---|
| WhatsApp (`msgstore.db`) | >= 99.0% | 100.0% (N=1153, 95% CI [99.7%, 100.0%]) | 0 | 0 |
| Telegram (`cache4.db`) | >= 99.0% | 99.4% (N=1063, 95% CI [98.8%, 99.7%]) | 6 | 6 |
| Overall Combined | >= 99.0% | 99.7% (N=2216, 95% CI [99.4%, 99.9%]) | 6 | 6 |

---
## 4. Deleted-Data Recovery Metrics (Per Tier)

| Evidential Tier | TP | FP | FN | Precision (Wilson 95% CI) | Recall (Wilson 95% CI) | F1 Score |
|---|---|---|---|---|---|---|
| Tier 1 | 3 | 3 | 0 | 50.0% (N=6, 95% CI [18.8%, 81.2%]) | 100.0% (N=3, 95% CI [43.9%, 100.0%]) | 0.6667 |
| Tier 2 | 4 | 15 | 0 | 21.1% (N=19, 95% CI [8.5%, 43.3%]) | 100.0% (N=4, 95% CI [51.0%, 100.0%]) | 0.3478 |
| Tier 3 | 8 | 198 | 0 | 3.9% (N=206, 95% CI [2.0%, 7.5%]) | 100.0% (N=8, 95% CI [67.6%, 100.0%]) | 0.0748 |
| Tier 4 | 1 | 1 | 3 | 50.0% (N=2, 95% CI [9.5%, 90.5%]) | 25.0% (N=4, 95% CI [4.6%, 69.9%]) | 0.3333 |

### Negative Controls Verification
- **Vacuumed Control False Recoveries:** `0` (Target: 0)
- **Secure-Delete Control False Recoveries:** `0` (Target: 0)
- **Controls Non-Recovery Rate:** `100.0% (N=2, 95% CI [34.2%, 100.0%])`
- **Benign ID-Gap Compliance:** Max confidence `0.0` (Strength: `none`, Capped <= 0.30 per DEC-014)

---
## 5. Cross-Platform Correlation Metrics

| Correlation Type | Planted | Discovered | Recall (Wilson 95% CI) | Decoys | Decoys Linked | False Positive Rate |
|---|---|---|---|---|---|---|
| Crypto | 3 | 3 | 100.0% (N=3, 95% CI [43.9%, 100.0%]) | 3 | 0 | 0.0% (N=3, 95% CI [0.0%, 56.1%]) |
| Phone | 1 | 1 | 100.0% (N=1, 95% CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (N=1, 95% CI [0.0%, 79.3%]) |
| Url | 1 | 1 | 100.0% (N=1, 95% CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (N=1, 95% CI [0.0%, 79.3%]) |
| Media | 1 | 1 | 100.0% (N=1, 95% CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (N=1, 95% CI [0.0%, 79.3%]) |
| Rendezvous | 1 | 1 | 100.0% (N=1, 95% CI [20.7%, 100.0%]) | 3 | 0 | 0.0% (N=3, 95% CI [0.0%, 56.1%]) |

- **Planted Links Total Recall:** `100.0% (N=7, 95% CI [64.6%, 100.0%])`
- **Decoy False Link Rate:** `0.0% (N=9, 95% CI [0.0%, 29.9%])` (Target: 0.0%)
- **Negative Control Device (DS-07) FPR:** `0.0% (N=10, 95% CI [0.0%, 27.8%])` (Target: 0.0%)

---
## 6. Timeline Determinism & Order Agreement

- **Total Events Evaluated:** `2498`
- **Order Agreement Rate:** `100.0% (N=2498, 95% CI [99.8%, 100.0%])`
- **Misplaced Events:** `0`
- **Total Anomalies Detected:** `10`

---
## 7. Confidence Calibration & Reliability Table

**Expected Calibration Error (ECE):** `0.4999` | **Status:** `HEURISTIC_ORDERING`  
**Policy Statement:** *scores are heuristic ordering, not calibrated probabilities*  

| Bin | Confidence Range | N | Mean Predicted | Observed Accuracy | Calibration Gap |
|---|---|---|---|---|---|
| 0 | [0.0, 0.1) | 0 | 0.0000 | 0.0000 | 0.0000 |
| 1 | [0.1, 0.2) | 0 | 0.0000 | 0.0000 | 0.0000 |
| 2 | [0.2, 0.3) | 2 | 0.2500 | 0.5000 | 0.2500 |
| 3 | [0.3, 0.4) | 0 | 0.0000 | 0.0000 | 0.0000 |
| 4 | [0.4, 0.5) | 0 | 0.0000 | 0.0000 | 0.0000 |
| 5 | [0.5, 0.6) | 0 | 0.0000 | 0.0000 | 0.0000 |
| 6 | [0.6, 0.7) | 18 | 0.6500 | 0.0000 | 0.6500 |
| 7 | [0.7, 0.8) | 33 | 0.7068 | 0.3333 | 0.3735 |
| 8 | [0.8, 0.9) | 17 | 0.8294 | 0.5294 | 0.3000 |
| 9 | [0.9, 1.0] | 370 | 0.9009 | 0.3865 | 0.5144 |

---
## 8. Runtime & Peak Memory Profile

| Pipeline Stage | Duration (ms) | Peak Memory (MiB) |
|---|---|---|
| integrity | 71.0 ms | 3.803 MiB |
| decryption | 1191.06 ms | 5.938 MiB |
| parsing | 883.55 ms | 4.86 MiB |
| recovery | 28918.87 ms | 4.398 MiB |
| correlation | 2800.87 ms | 6.546 MiB |
| timeline | 25803.3 ms | 8.278 MiB |
| calibration | 25836.74 ms | 8.277 MiB |
| **Total Pipeline** | **85505.39 ms** | **Max Peak: 8.278 MiB** |