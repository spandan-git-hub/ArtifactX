# ArtifactX — Empirical Evaluation and Metrics Chapter

> [!WARNING]
> **SYNTHETIC DATASET CAVEAT (master.md R1, R7, 12_METRICS_AND_EVALUATION.md):**  
> All metrics reported in this evaluation chapter were evaluated against synthetic ground-truth fixtures modelled on documented application schemas and SQLite physical storage layouts.  
> No key-less decryption is performed. Real-device hardware capture validation is deferred to V1.  
> All confidence scores are heuristic rankings and do NOT represent probabilistic proof or legal guilt.

---

## 1. Evaluation Methodology & Dev/Holdout Protocol (Spec C1.4)

To prevent overfitting on threshold tuning and pipeline development, ArtifactX maintains an anti-overfitting protocol:
1. **Dev Dataset Set (`*-dev`):** Used exclusively during algorithm development, threshold tuning, and `acceptance.yaml` target setting.
2. **Holdout Dataset Set (`*-holdout`):** Kept strictly unseen during tuning. Generated with independent pseudorandom seeds, different timestamps, altered contact phone numbers, distinct cryptographic decoy addresses, and unique perceptual images.
3. **Frozen Configuration Protocol:**
   - Before executing the holdout evaluation, `evaluation/runner.py --freeze` computes the SHA-256 digests of all scoring configurations:
     - `forensic/correlation/thresholds.py`
     - `forensic/timeline/config.py`
     - `acceptance.yaml`
   - These hashes are locked into `evaluation/FROZEN.json` alongside the current Git commit.
   - The evaluation runner **strictly refuses** to execute holdout evaluation if any configuration file hash deviates from `FROZEN.json`.
4. **Statistical Reporting:** Every metric proportion is reported alongside its exact **Wilson 95% score confidence interval** and sample size $N$ (spec C1.2).

---

## 2. Dev vs Holdout Empirical Results Side-by-Side

| Metric Domain | Metric | Target | DEV Result (Wilson 95% CI) | HOLDOUT Result (Wilson 95% CI) | Status |
|---|---|---|---|---|---|
| **Integrity** | Re-hash Stability | 100.0% | 100.0% ($N=75$, CI [95.1%, 100.0%]) | 100.0% ($N=75$, CI [95.1%, 100.0%]) | PASS |
| **Integrity** | Single-Byte Mutation Detection (DS-08) | 100.0% | 100.0% ($N=24$, CI [86.2%, 100.0%]) | 100.0% ($N=24$, CI [86.2%, 100.0%]) | PASS |
| **Integrity** | Audit Chain Tamper Detection | 100.0% | 100.0% ($N=10$, CI [72.2%, 100.0%]) | 100.0% ($N=10$, CI [72.2%, 100.0%]) | PASS |
| **Decryption** | Crypt14/Crypt15 Parity | 100.0% | 100.0% ($N=2$, CI [34.2%, 100.0%]) | 100.0% ($N=2$, CI [34.2%, 100.0%]) | PASS |
| **Decryption** | Negative Typed-Error Rate | 100.0% | 100.0% ($N=2$, CI [34.2%, 100.0%]) | 100.0% ($N=2$, CI [34.2%, 100.0%]) | PASS |
| **Decryption** | Key Redaction Compliance (Rule R5) | 100.0% | 100.0% ($N=1$, CI [20.7%, 100.0%]) | 100.0% ($N=1$, CI [20.7%, 100.0%]) | PASS |
| **Parsing** | WhatsApp Accuracy (`msgstore.db`) | $\ge 99.0\%$ | 100.0% ($N=1153$, CI [99.7%, 100.0%]) | 100.0% ($N=1153$, CI [99.7%, 100.0%]) | PASS |
| **Parsing** | Telegram Accuracy (`cache4.db`) | $\ge 99.0\%$ | 99.4% ($N=1063$, CI [98.8%, 99.7%]) | 99.4% ($N=1063$, CI [98.8%, 99.7%]) | PASS |
| **Parsing** | Overall Combined Parsing Accuracy | $\ge 99.0\%$ | 99.7% ($N=2216$, CI [99.4%, 99.9%]) | 99.7% ($N=2216$, CI [99.4%, 99.9%]) | PASS |
| **Recovery** | Negative Controls Non-Recovery Rate | 100.0% | 100.0% ($N=2$, CI [34.2%, 100.0%]) | 100.0% ($N=2$, CI [34.2%, 100.0%]) | PASS |
| **Recovery** | Benign ID-Gap Confidence Cap | $\le 0.30$ | Max: 0.00 (Strength: `none`) | Max: 0.00 (Strength: `none`) | PASS |
| **Correlation** | Planted Links Recall (DS-06) | 100.0% | 100.0% ($N=7$, CI [64.6%, 100.0%]) | 100.0% ($N=7$, CI [64.6%, 100.0%]) | PASS |
| **Correlation** | Decoys Linked Rate (DS-06) | 0.0% | 0.0% ($N=9$, CI [0.0%, 29.9%]) | 0.0% ($N=9$, CI [0.0%, 29.9%]) | PASS |
| **Correlation** | Negative Control Device FPR (DS-07) | 0.0% | 0.0% ($N=10$, CI [0.0%, 27.8%]) | 0.0% ($N=10$, CI [0.0%, 27.8%]) | PASS |
| **Timeline** | Total Order Agreement Rate | 100.0% | 100.0% ($N=2506$, CI [99.8%, 100.0%]) | 100.0% ($N=2498$, CI [99.8%, 100.0%]) | PASS |
| **Timeline** | Misplaced Events Count | 0 | 0 | 0 | PASS |

---

## 3. Deleted-Data Recovery Breakdown Per Evidential Tier

Recovery metrics are tracked across the 4 evidential tiers defined in master.md §R7 and 08_DELETED_DATA_RECOVERY.md:

| Evidential Tier | Method Description | Dev Precision | Dev Recall | Holdout Precision | Holdout Recall |
|---|---|---|---|---|---|
| **Tier 1** | Explicit Application Markers (revocations, tombstones) | 50.0% ($N=6$, CI [18.8%, 81.2%]) | 100.0% ($N=3$, CI [43.9%, 100.0%]) | 50.0% ($N=6$, CI [18.8%, 81.2%]) | 100.0% ($N=3$, CI [43.9%, 100.0%]) |
| **Tier 2** | WAL Frame Forensics (committed transaction history) | 15.4% ($N=26$, CI [6.2%, 33.5%]) | 100.0% ($N=4$, CI [51.0%, 100.0%]) | 21.1% ($N=19$, CI [8.5%, 43.3%]) | 100.0% ($N=4$, CI [51.0%, 100.0%]) |
| **Tier 3** | B-Tree Page Carving (freelist, unallocated slack) | 4.0% ($N=200$, CI [2.0%, 7.7%]) | 100.0% ($N=8$, CI [67.6%, 100.0%]) | 3.9% ($N=206$, CI [2.0%, 7.5%]) | 100.0% ($N=8$, CI [67.6%, 100.0%]) |
| **Tier 4** | Autoincrement Primary Key ID-Gaps | 50.0% ($N=2$, CI [9.5%, 90.5%]) | 25.0% ($N=4$, CI [4.6%, 69.9%]) | 50.0% ($N=2$, CI [9.5%, 90.5%]) | 25.0% ($N=4$, CI [4.6%, 69.9%]) |

### Negative Controls Verification (Spec C1.2):
- **Vacuumed Database Control (`DS-01-vacuumed`):** 0 records recovered.
- **Secure-Delete Enabled Control (`DS-01-secure-delete`):** 0 records recovered.
- **Benign Sequence Gap Cap (DEC-014):** Gaps without temporal anomalies or deleted transaction markers receive confidence 0.00 (strength `none`), strictly below the 0.30 reporting threshold.

---

## 4. Cross-Platform Correlation Metrics (Per Entity Type)

Evaluated on `DS-06` (cross-platform device with planted shared entities and decoy records) and `DS-07` (control device with unrelated exhibits):

| Correlation Type | Planted Links | Planted Recall | Decoys Planted | Decoys Linked | False Positive Rate |
|---|---|---|---|---|---|
| **Crypto** (BTC Base58Check, EVM EIP-55, IBAN Mod-97) | 3 | 100.0% (CI [43.9%, 100.0%]) | 3 | 0 | 0.0% (CI [0.0%, 56.1%]) |
| **Phone Identity** (E.164 normalization, union-find) | 1 | 100.0% (CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (CI [0.0%, 79.3%]) |
| **Canonical URL** (tracking-stripped URL normalizer) | 1 | 100.0% (CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (CI [0.0%, 79.3%]) |
| **Perceptual Media** (dHash distance $\le 4$) | 1 | 100.0% (CI [20.7%, 100.0%]) | 1 | 0 | 0.0% (CI [0.0%, 79.3%]) |
| **Spatiotemporal Rendezvous** (Haversine $\le 250$m, $\Delta t \le 2$h) | 1 | 100.0% (CI [20.7%, 100.0%]) | 3 | 0 | 0.0% (CI [0.0%, 56.1%]) |

---

## 5. Confidence Calibration & Honest Policy Decision (Spec C1.3, DEC-039)

### 10-Bin Calibration Table (Holdout Dataset Set, $N=438$):
- **Expected Calibration Error (ECE):** `0.4999`
- **Maximum Calibration Error (MCE):** `0.6500`
- **Status Classification:** `HEURISTIC_ORDERING`

| Bin | Confidence Range | Bin Count ($N$) | Mean Predicted Score | Observed Accuracy | Calibration Gap |
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

### Policy Decision DEC-039 (Honest Wording):
Because the empirical ECE ($0.4999$) exceeds the $0.10$ calibration threshold (due to heuristic scoring designed for conservative investigator ranking rather than frequentist probabilistic prediction), ArtifactX enforces the following rules across all UI components, API responses, and generated reports:
1. Confidence scores are **never** referred to as "calibrated probabilities".
2. All documentation and UI badges must state: **"scores are heuristic ordering, not calibrated probabilities"**.
3. Confidence scores must never be presented as mathematical probabilities of factual truth or legal guilt.

---

## 6. Determinism Contract (Spec C4)

When identical evidence files and pipeline configurations are processed, ArtifactX guarantees:
- Byte-identical stage output digests (`output_hash`).
- Identical finding IDs, sort orders, and content digests (`content_hash`).

### Excluded Wall-Clock Fields:
The following execution metadata fields are intentionally excluded from deterministic content hashes:
- `started_at`, `finished_at`, `timestamp_utc` (wall-clock execution timestamps).
- `duration_ms` (system performance timing).
- `peak_memory_mib` (process memory allocation).
- Host system environment details (OS version, interpreter PID).
