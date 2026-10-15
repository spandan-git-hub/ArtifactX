"""Orphan media detection for forensic analysis."""

from pathlib import Path
from typing import Any, List, Optional, Set


def is_orphan_file_path(file_path: Optional[str]) -> bool:
    """Check if a file path is missing or points to a non-existent file."""
    if not file_path:
        return True
    try:
        return not Path(file_path).exists()
    except Exception:
        return True


def find_orphan_media_items(case_id: int, db: Any) -> List[Any]:
    """
    Find MediaItem records that don't correspond to actual extracted files.

    These are media items that were detected in message databases but the
    actual media files are not present in the extracted evidence.

    Args:
        case_id: ID of the case to check
        db: Database session (duck-typed to avoid cross-layer imports)

    Returns:
        List of MediaItem objects that are orphans
    """
    # Dynamically resolve MediaItem from db registry to maintain forensic purity (R18)
    media_item_cls = None
    mapper_registry = getattr(db, "registry", None)
    if mapper_registry:
        for mapper in getattr(mapper_registry, "mappers", []):
            if mapper.class_.__name__ == "MediaItem":
                media_item_cls = mapper.class_
                break

    if media_item_cls is None:
        return []

    media_items = db.query(media_item_cls).filter(media_item_cls.case_id == case_id).all()
    orphan_items = []

    for media_item in media_items:
        if is_orphan_file_path(media_item.file_path):
            media_item.is_orphan = True
            orphan_items.append(media_item)
        else:
            media_item.is_orphan = False

    return orphan_items


def find_orphan_files(case_id: int, evidence_id: int, db: Any) -> List[Any]:
    """
    Find extracted files that don't have corresponding MediaItem records.

    These are files that exist in the extracted evidence but were not
    detected as media in any message databases.

    Args:
        case_id: ID of the case
        evidence_id: ID of the evidence
        db: Database session (duck-typed to avoid cross-layer imports)

    Returns:
        List of EvidenceFile objects that are orphans (no media item)
    """
    evidence_file_cls = None
    media_item_cls = None
    mapper_registry = getattr(db, "registry", None)
    if mapper_registry:
        for mapper in getattr(mapper_registry, "mappers", []):
            if mapper.class_.__name__ == "EvidenceFile":
                evidence_file_cls = mapper.class_
            elif mapper.class_.__name__ == "MediaItem":
                media_item_cls = mapper.class_

    if evidence_file_cls is None or media_item_cls is None:
        return []

    evidence_files = db.query(evidence_file_cls).filter(evidence_file_cls.evidence_id == evidence_id).all()
    media_items = db.query(media_item_cls).filter(media_item_cls.evidence_id == evidence_id).all()

    media_file_paths: Set[str] = set()
    for media_item in media_items:
        if media_item.file_path:
            media_file_paths.add(str(Path(media_item.file_path).name))

    orphan_files = []
    for evidence_file in evidence_files:
        file_name = Path(evidence_file.relative_path).name if evidence_file.relative_path else ""
        if getattr(evidence_file, "is_media", False) and file_name not in media_file_paths:
            orphan_files.append(evidence_file)

    return orphan_files


def mark_media_orphan_status(case_id: int, db: Any) -> int:
    """
    Update the is_orphan flag for all media items in a case.

    Args:
        case_id: ID of the case to process
        db: Database session

    Returns:
        Number of media items marked as orphan
    """
    orphan_items = find_orphan_media_items(case_id, db)
    count = len(orphan_items)
    db.commit()
    return count