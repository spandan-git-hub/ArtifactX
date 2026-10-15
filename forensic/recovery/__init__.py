"""
Forensic Deleted Data Recovery Package (spec B10, master.md R4, R7, R8, R10, R11, R12).

Zero-disk read-only SQLite physical deleted message recovery, WAL historical versions,
freelist/slack carving, and primary-key gap indicators.
"""

from forensic.recovery.deduplication import (
    build_live_row_index,
    deduplicate_and_sort_findings,
    get_finding_identity_key,
)
from forensic.recovery.evaluation import evaluate_recovery
from forensic.recovery.models import (
    RecoveryFinding,
    RecoveryResult,
    ValidationStatus,
)
from forensic.recovery.orchestrator import RecoveryPipeline
from forensic.recovery.schema_guided import SchemaGuidedDecoder
from forensic.recovery.tier1_explicit import (
    extract_tier1_telegram,
    extract_tier1_whatsapp,
)
from forensic.recovery.tier2_wal import carve_tier2
from forensic.recovery.tier3_carver import carve_tier3
from forensic.recovery.tier4_gaps import detect_tier4_gaps

__all__ = [
    "RecoveryPipeline",
    "RecoveryFinding",
    "RecoveryResult",
    "ValidationStatus",
    "evaluate_recovery",
    "carve_tier2",
    "carve_tier3",
    "detect_tier4_gaps",
    "extract_tier1_whatsapp",
    "extract_tier1_telegram",
    "SchemaGuidedDecoder",
    "build_live_row_index",
    "deduplicate_and_sort_findings",
    "get_finding_identity_key",
]
