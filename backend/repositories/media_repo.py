"""Repository for media analysis data."""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.models import MediaItem, EvidenceFile


class MediaRepository:
    """Repository for media analysis data operations."""

    def save_media_items(self, db: Session, media_items: List[dict]):
        """Save media items to database."""
        for media_item_data in media_items:
            # Check if media item already exists (by evidence_id and linked_message_id)
            existing = db.query(MediaItem).filter(
                MediaItem.evidence_id == media_item_data["evidence_id"],
                MediaItem.linked_message_id == media_item_data["linked_message_id"]
            ).first()

            if not existing:
                media_item = MediaItem(**media_item_data)
                db.add(media_item)

        db.commit()

    def get_media_items_by_evidence_id(self, db: Session, evidence_id: int) -> List[MediaItem]:
        """Get media items by evidence ID."""
        return db.query(MediaItem).filter(
            MediaItem.evidence_id == evidence_id
        ).all()

    def get_media_items_by_case_id(self, db: Session, case_id: int) -> List[MediaItem]:
        """Get media items by case ID."""
        return db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).all()

    def get_orphan_media_items(self, db: Session, case_id: int) -> List[MediaItem]:
        """Get orphan media items for a case."""
        return db.query(MediaItem).filter(
            MediaItem.case_id == case_id,
            MediaItem.is_orphan == True
        ).all()


# Singleton instance
media_repository = MediaRepository()