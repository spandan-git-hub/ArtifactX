"""Media analysis service for forensic analysis."""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.repositories.media_repo import MediaRepository
from forensic.media.orphan import find_orphan_media_items, find_orphan_files, mark_media_orphan_status
from backend.models.models import MediaItem, EvidenceFile, Evidence, Case
from backend.services.log_service import get_log_service


class MediaService:
    """Service for media analysis operations."""

    def __init__(self):
        self.repository = MediaRepository()

    async def analyze_media_for_evidence(self, evidence_id: int, db: Session) -> bool:
        """
        Perform media analysis on evidence to extract metadata and detect orphan media.

        Args:
            evidence_id: ID of evidence to analyze
            db: Database session

        Returns:
            bool: True if analysis started successfully, False otherwise
        """
        # Get evidence
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return False

        # Get case
        case = db.query(Case).filter(Case.id == evidence.case_id).first()
        if not case:
            return False

        # Get log service
        log_service = get_log_service(db)

        # Log analysis start
        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="media_analysis_start",
            message="Starting media analysis for evidence",
            details={"evidence_id": evidence_id}
        )

        try:
            # Run media analysis (for now, we'll run it synchronously)
            self._perform_media_analysis(evidence_id, case.id, db)

            # Log analysis success
            log_service.log_analysis(
                evidence_id=evidence_id,
                log_type="media_analysis_completed",
                message="Media analysis completed successfully",
                details={"evidence_id": evidence_id}
            )

            return True
        except Exception as e:
            # Log error
            log_service.log_error(
                error_type="media_analysis_error",
                message=f"Error during media analysis: {str(e)}",
                case_id=evidence.case_id,
                evidence_id=evidence_id,
                stack_trace=str(e.__traceback__),
                endpoint="/api/evidence/{evidence_id}/analyze/media",
                method="POST"
            )
            return False

    def _perform_media_analysis(self, evidence_id: int, case_id: int, db: Session):
        """
        Perform the actual media analysis.

        Args:
            evidence_id: ID of evidence
            case_id: ID of case
            db: Database session
        """
        # Mark orphan media status for this case
        orphan_count = mark_media_orphan_status(case_id, db)
        # Note: In a more complete implementation, we would also extract metadata
        # for media files that don't already have it

    def get_media_items(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get media items for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_media_items_by_evidence_id(db, evidence_id)

    def get_orphan_media_items(self, case_id: int, db: Session) -> List[dict]:
        """Get orphan media items for a case."""
        orphan_items = find_orphan_media_items(case_id, db)
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
            for item in orphan_items
        ]

    def get_orphan_files(self, case_id: int, evidence_id: int, db: Session) -> List[dict]:
        """Get orphan files (extracted files without media items) for evidence."""
        orphan_files = find_orphan_files(case_id, evidence_id, db)
        return [
            {
                "id": file.id,
                "evidence_id": file.evidence_id,
                "relative_path": file.relative_path,
                "sha256": file.sha256,
                "file_size": file.file_size,
                "mime_type": file.mime_type,
                "is_media": file.is_media,
                "media_type": file.media_type,
            }
            for file in orphan_files
        ]


# Singleton instance
media_service = MediaService()