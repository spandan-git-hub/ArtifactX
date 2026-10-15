"""
Tier 2: Write-Ahead Log (WAL) Historical Page Versions (spec B10.2, master.md R4, R7, R8, R10).

Carves deleted or prior versions of records from:
- committed-superseded frames
- uncommitted-tail frames
- stale-generation frames
using schema-guided record decoding and B8 wal_page_history.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from forensic.recovery.models import RecoveryFinding
from forensic.recovery.schema_guided import SchemaGuidedDecoder
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.wal import WalFile, parse_wal, wal_page_history


def carve_tier2(
    main_image: SQLiteImage,
    wal_bytes: Optional[bytes],
    app_hint: str = "whatsapp",
    evidence_id: str = "0",
    evidence_sha256: str = "",
    max_steps_per_page: int = 25000,
) -> Tuple[List[RecoveryFinding], int, int, List[str]]:
    """
    Execute Tier 2 recovery across historical and uncheckpointed WAL frames.

    Returns:
        (findings, wal_pages_count, invalid_rejected_count, warnings)
    """
    if not wal_bytes or len(wal_bytes) < 32:
        return ([], 0, 0, [])

    try:
        wal = parse_wal(wal_bytes, page_size_hint=main_image.page_size)
    except Exception as exc:
        return ([], 0, 0, [f"Failed to parse WAL: {str(exc)}"])

    decoder = SchemaGuidedDecoder(
        app_hint=app_hint,
        evidence_id=evidence_id,
        evidence_sha256=evidence_sha256,
        max_steps_per_page=max_steps_per_page,
    )

    findings: List[RecoveryFinding] = []
    seen_payload_hashes: Set[str] = set()

    # Track multi-version pages and all frames
    for frame in wal.frames:
        if not frame.valid:
            continue

        frame_type = (
            "stale-generation"
            if frame.stale_generation
            else ("uncommitted-tail" if not frame.committed else "committed-superseded")
        )

        frame_findings = decoder.scan_buffer(
            buffer=frame.data,
            page_no=frame.page_no,
            base_offset=frame.offset,
            kind="wal_resident",
            tier=2,
        )

        for ff in frame_findings:
            if ff.raw_payload_hash in seen_payload_hashes:
                continue
            seen_payload_hashes.add(ff.raw_payload_hash)

            # Enrich provenance and limitations with frame details
            limitations = list(ff.limitations)
            limitations.append(
                f"extracted from {frame_type} WAL frame {frame.index} (commit_size={frame.commit_size})"
            )

            updated = RecoveryFinding(
                finding_id=ff.finding_id,
                confidence_score=ff.confidence_score,
                strength="strong" if ff.validation_status == "FULL_RECORD_VALID" else "moderate",
                limitations=tuple(limitations),
                provenance=ff.provenance,
                tier=2,
                kind="wal_resident",
                validation_status=ff.validation_status,
                table_name=ff.table_name,
                row_id=ff.row_id,
                page_no=frame.page_no,
                byte_offset=ff.byte_offset,
                frame_index=frame.index,
                view="wal_history",
                recovered_fields=ff.recovered_fields,
                raw_payload_hash=ff.raw_payload_hash,
                raw_payload_preview=ff.raw_payload_preview,
            )
            findings.append(updated)

    return (findings, len(wal.frames), decoder.invalid_rejected_count, decoder.warnings)
