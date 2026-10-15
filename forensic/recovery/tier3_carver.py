"""
Tier 3: Freelist Pages and Intra-Page Slack Space Carving (spec B10.3, master.md R4, R7, R8, R12).

Scans:
1. SQLite freelist trunk & leaf pages (B8.3)
2. Live leaf-table page unallocated gaps and freeblocks (B8.4)
using schema-guided record decoding for WhatsApp and Telegram.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from forensic.recovery.models import RecoveryFinding
from forensic.recovery.schema_guided import SchemaGuidedDecoder
from forensic.sqlite.constants import BTREE_LEAF_TABLE
from forensic.sqlite.freelist import classify_free_page, walk_freelist
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.slack import walk_page_spans


def carve_tier3(
    image: SQLiteImage,
    app_hint: str = "whatsapp",
    evidence_id: str = "0",
    evidence_sha256: str = "",
    max_steps_per_page: int = 25000,
) -> Tuple[List[RecoveryFinding], int, int, int, List[str]]:
    """
    Execute Tier 3 physical carving across freelist pages and leaf page slack spans.

    Returns:
        (findings, freelist_pages_count, slack_spans_count, invalid_rejected_count, warnings)
    """
    decoder = SchemaGuidedDecoder(
        app_hint=app_hint,
        evidence_id=evidence_id,
        evidence_sha256=evidence_sha256,
        max_steps_per_page=max_steps_per_page,
    )

    findings: List[RecoveryFinding] = []
    freelist_pages_count = 0
    slack_spans_count = 0
    seen_payload_hashes: Set[str] = set()

    # 1. Carve Freelist Pages (Trunk and Leaf)
    free_pages = walk_freelist(image)
    freelist_pages_count = len(free_pages)

    for fp in free_pages:
        raw_bytes = fp.raw_bytes
        page_no = fp.page_no
        base_off = (page_no - 1) * image.page_size

        page_findings = decoder.scan_buffer(
            buffer=raw_bytes,
            page_no=page_no,
            base_offset=base_off,
            kind="freelist",
            tier=3,
        )

        for pf in page_findings:
            if pf.raw_payload_hash not in seen_payload_hashes:
                seen_payload_hashes.add(pf.raw_payload_hash)
                findings.append(pf)

    # 2. Carve Live Leaf-Table Spans (Unallocated Gaps and Freeblocks)
    for p_no in range(1, image.page_count + 1):
        try:
            spans = walk_page_spans(image, p_no)
        except Exception:
            continue

        if not spans:
            continue

        page_mv = image.get_page(p_no)
        page_base = (p_no - 1) * image.page_size

        for span in spans:
            slack_spans_count += 1
            if span.length < 16:
                continue

            span_data = bytes(page_mv[span.offset : span.offset + span.length])
            span_kind = "slack" if span.kind == "unallocated_gap" else "freeblock"

            span_findings = decoder.scan_buffer(
                buffer=span_data,
                page_no=p_no,
                base_offset=page_base + span.offset,
                kind=span_kind,
                tier=3,
            )

            for sf in span_findings:
                if sf.raw_payload_hash not in seen_payload_hashes:
                    seen_payload_hashes.add(sf.raw_payload_hash)
                    findings.append(sf)

    return (
        findings,
        freelist_pages_count,
        slack_spans_count,
        decoder.invalid_rejected_count,
        decoder.warnings,
    )
