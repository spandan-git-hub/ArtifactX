"""
Recovery Pipeline Orchestrator (spec B10, master.md R4, R7, R8, R10, R11).

Coordinates Tier 1 explicit deletion markers, Tier 2 WAL page versions,
Tier 3 freelist and intra-page slack carving, and Tier 4 ID-gap indicators.
Applies deduplication, validation status tagging, and deterministic ordering.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.recovery.deduplication import (
    build_live_row_index,
    deduplicate_and_sort_findings,
)
from forensic.recovery.models import RecoveryFinding, RecoveryResult
from forensic.recovery.tier1_explicit import (
    extract_tier1_telegram,
    extract_tier1_whatsapp,
)
from forensic.recovery.tier2_wal import carve_tier2
from forensic.recovery.tier3_carver import carve_tier3
from forensic.recovery.tier4_gaps import detect_tier4_gaps
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.wal import apply_wal, parse_wal


class RecoveryPipeline:
    """
    Pure-Python non-destructive SQLite deleted data recovery pipeline.
    Zero disk writes (R4); full cryptographic provenance (R8).
    """

    def __init__(
        self,
        db_bytes: bytes,
        wal_bytes: Optional[bytes] = None,
        app_hint: Optional[str] = None,
        evidence_id: str = "0",
        evidence_sha256: str = "",
        max_steps_per_page: int = 25000,
    ):
        self.db_bytes = db_bytes
        self.wal_bytes = wal_bytes
        self.evidence_id = str(evidence_id)
        self.evidence_sha256 = evidence_sha256 or hashlib.sha256(db_bytes).hexdigest()
        self.max_steps_per_page = max_steps_per_page

        # Infer app hint if not explicitly given
        if app_hint:
            self.app_hint = app_hint.lower()
        else:
            self.app_hint = "telegram" if (b"messages_v2" in db_bytes or b"cache4" in db_bytes) else "whatsapp"

    def run(self) -> RecoveryResult:
        """Execute full four-tier recovery pipeline."""
        warnings: List[str] = []
        raw_candidates: List[RecoveryFinding] = []

        # 1. Initialize SQLiteImage for the main database
        main_image = SQLiteImage(self.db_bytes)

        # 2. Build live row identity index across main database view
        live_keys = build_live_row_index(self.db_bytes, self.app_hint)

        # 3. Tier 1: Explicit deletion evidence
        if "telegram" in self.app_hint or "tg" in self.app_hint:
            t1_findings = extract_tier1_telegram(
                db_bytes=self.db_bytes,
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
            )
        else:
            t1_findings = extract_tier1_whatsapp(
                db_bytes=self.db_bytes,
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
            )
        raw_candidates.extend(t1_findings)

        # 4. Tier 2: WAL historical page versions
        t2_findings, wal_pages_count, t2_rejected, t2_warn = carve_tier2(
            main_image=main_image,
            wal_bytes=self.wal_bytes,
            app_hint=self.app_hint,
            evidence_id=self.evidence_id,
            evidence_sha256=self.evidence_sha256,
            max_steps_per_page=self.max_steps_per_page,
        )
        raw_candidates.extend(t2_findings)
        warnings.extend(t2_warn)

        # 5. Tier 3: Freelist and Intra-page Slack Carving
        t3_findings, freelist_count, slack_count, t3_rejected, t3_warn = carve_tier3(
            image=main_image,
            app_hint=self.app_hint,
            evidence_id=self.evidence_id,
            evidence_sha256=self.evidence_sha256,
            max_steps_per_page=self.max_steps_per_page,
        )
        raw_candidates.extend(t3_findings)
        warnings.extend(t3_warn)

        # Collect row IDs already explained by Tiers 1-3 to suppress redundant ID gaps
        explained_rowids: Set[int] = set()
        for f in raw_candidates:
            if f.row_id is not None:
                explained_rowids.add(f.row_id)
            if "mid" in f.recovered_fields and f.recovered_fields["mid"] is not None:
                explained_rowids.add(int(f.recovered_fields["mid"]))

        # 6. Tier 4: ID-gap indicators
        t4_findings = detect_tier4_gaps(
            db_bytes=self.db_bytes,
            app_hint=self.app_hint,
            evidence_id=self.evidence_id,
            evidence_sha256=self.evidence_sha256,
            stronger_tier_rowids=explained_rowids,
        )
        raw_candidates.extend(t4_findings)

        # 7. Deduplication, Live Row tagging, and Deterministic Sorting (B10.5)
        final_findings = deduplicate_and_sort_findings(raw_candidates, live_keys)

        # 8. Compute per-tier and status summary statistics
        tier_counts: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
        status_counts: Dict[str, int] = {}
        actionable_count = 0

        for f in final_findings:
            st = f.validation_status
            status_counts[st] = status_counts.get(st, 0) + 1

            # Counts are never summed across tiers into one "deleted messages" number (B10.0)
            # DUPLICATE_OF_LIVE and DUPLICATE_OF_OTHER_TIER are excluded from finding counts (B10.5)
            if st in ("FULL_RECORD_VALID", "PARTIAL"):
                tier_counts[f.tier] = tier_counts.get(f.tier, 0) + 1
                if f.tier != 4:  # Tier 4 weak hints are excluded from deleted totals per B10.4
                    actionable_count += 1

        total_rejected = t2_rejected + t3_rejected

        return RecoveryResult(
            findings=tuple(final_findings),
            total_findings_count=actionable_count,
            tier_counts=tier_counts,
            validation_status_counts=status_counts,
            invalid_rejected_count=total_rejected,
            wal_pages_analyzed=wal_pages_count,
            freelist_pages_analyzed=freelist_count,
            slack_spans_analyzed=slack_count,
            warnings=tuple(warnings),
        )
