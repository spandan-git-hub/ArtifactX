"""Media analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database import get_db
from backend.services.media_service import media_service
# Note: MediaItemRead schema would need to be created, but for now we'll return dicts

router = APIRouter()


@router.post("/evidence/{evidence_id}/analyze/media", status_code=status.HTTP_202_ACCEPTED)
async def analyze_media(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Trigger media analysis on evidence."""
    result = await media_service.analyze_media_for_evidence(evidence_id, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or analysis failed"
        )
    return {"message": "Media analysis started", "evidence_id": evidence_id}


@router.get("/evidence/{evidence_id}/media")
def get_media_items(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get media items for evidence."""
    media_items = media_service.get_media_items(evidence_id, db)
    if media_items is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return [
        {
            "id": item.id,
            "case_id": item.case_id,
            "evidence_id": item.evidence_id,
            "file_path": item.file_path,
            "sha256": item.sha256,
            "mime_type": item.mime_type,
            "media_type": item.media_type,
            "file_size": item.file_size,
            "width": item.width,
            "height": item.height,
            "duration": item.duration,
            "exif_data": item.exif_data,
            "is_orphan": item.is_orphan,
            "linked_message_id": item.linked_message_id,
        }
        for item in media_items
    ]


@router.get("/cases/{case_id}/media/orphan")
def get_orphan_media(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get orphan media items for a case."""
    orphan_items = media_service.get_orphan_media_items(case_id, db)
    return orphan_items


@router.get("/evidence/{evidence_id}/files/orphan")
def get_orphan_files(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get orphan files (extracted files without media items) for evidence."""
    # We need to get the case_id for this evidence to check for orphan files
    from backend.app.database import get_db
    from backend.models.models import Evidence

    # Get a new DB session for this query (since we're in a dependency)
    db_session = next(get_db())
    try:
        evidence = db_session.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )

        orphan_files = media_service.get_orphan_files(evidence.case_id, evidence_id, db_session)
        return orphan_files
    finally:
        db_session.close()