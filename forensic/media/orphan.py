"""Orphan media detection for forensic analysis."""

from pathlib import Path
from typing import List, Set, Tuple
from sqlalchemy.orm import Session

from backend.models.models import MediaItem, EvidenceFile


def find_orphan_media_items(case_id: int, db: Session) -> List[MediaItem]:
    """
    Find MediaItem records that don't correspond to actual extracted files.

    These are media items that were detected in message databases but the
    actual media files are not present in the extracted evidence.

    Args:
        case_id: ID of the case to check
        db: Database session

    Returns:
        List of MediaItem objects that are orphans
    """
    # Get all media items for this case
    media_items = db.query(MediaItem).filter(MediaItem.case_id == case_id).all()

    orphan_items = []

    for media_item in media_items:
        # Check if the file_path exists and is within the evidence extraction directory
        file_path = Path(media_item.file_path)

        # For now, we'll consider it an orphan if the file doesn't exist
        # In a more sophisticated implementation, we'd check if it's within the evidence directory
        if not file_path.exists():
            media_item.is_orphan = True
            orphan_items.append(media_item)
        else:
            media_item.is_orphan = False

    return orphan_items


def find_orphan_files(case_id: int, evidence_id: int, db: Session) -> List[EvidenceFile]:
    """
    Find extracted files that don't have corresponding MediaItem records.

    These are files that exist in the extracted evidence but were not
    detected as media in any message databases.

    Args:
        case_id: ID of the case
        evidence_id: ID of the evidence
        db: Database session

    Returns:
        List of EvidenceFile objects that are orphans (no media item)
    """
    # Get all evidence files for this evidence
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).all()

    # Get all media items for this evidence
    media_items = db.query(MediaItem).filter(MediaItem.evidence_id == evidence_id).all()

    # Create a set of file paths that have media items
    media_file_paths: Set[str] = set()
    for media_item in media_items:
        if media_item.file_path:
            media_file_paths.add(str(Path(media_item.file_path).name))

    # Find evidence files that don't correspond to any media item
    orphan_files = []
    for evidence_file in evidence_files:
        file_name = Path(evidence_file.relative_path).name
        # Check if this file is marked as media but doesn't have a media item
        if evidence_file.is_media and file_name not in media_file_paths:
            orphan_files.append(evidence_file)

    return orphan_files


def mark_media_orphan_status(case_id: int, db: Session) -> int:
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

    # The is_orphan flag is already set in find_orphan_media_items
    db.commit()

    return count