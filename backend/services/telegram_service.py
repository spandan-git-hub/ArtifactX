"""Telegram analysis service."""

import asyncio
import traceback
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.config import UPLOADS_DIR
from forensic.telegram.detector import is_telegram_database
from forensic.telegram.message_parser import extract_messages
from forensic.telegram.contact_parser import extract_contacts
from forensic.telegram.group_parser import extract_groups
from forensic.telegram.media_parser import extract_media_references
from backend.repositories.telegram_repo import TelegramRepository
from backend.models.models import Evidence, TelegramMessage, TelegramContact, TelegramGroup, EvidenceFile, MediaItem
from backend.services.log_service import get_log_service
from datetime import datetime


class TelegramService:
    """Service for Telegram analysis operations."""

    def __init__(self):
        self.repository = TelegramRepository()

    async def analyze_evidence(self, evidence_id: int, db: Session) -> bool:
        """
        Trigger Telegram analysis on evidence.

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

        # Get log service
        log_service = get_log_service(db)

        # Log analysis start
        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="telegram_analysis_start",
            message="Starting Telegram analysis",
            details={"evidence_id": evidence_id}
        )

        try:
            # Check if evidence has extracted path (for ZIP files)
            if not evidence.extracted_path:
                # For non-ZIP evidence, check if the storage file itself is a Telegram DB
                db_path = Path(evidence.storage_path)
            else:
                # For ZIP evidence, we need to find Telegram database in extracted files
                # For now, we'll look for any .db files in the extracted path
                # In a more sophisticated implementation, we'd scan for Telegram-specific files
                db_path = None
                extracted_dir = Path(evidence.extracted_path)
                if extracted_dir.exists():
                    # Look for Telegram database files
                    for db_file in extracted_dir.rglob("*.db"):
                        if is_telegram_database(db_file):
                            db_path = db_file
                            break
                    # If no specific Telegram DB found, try the first .db file
                    if not db_path:
                        db_files = list(extracted_dir.rglob("*.db"))
                        if db_files:
                            db_path = db_files[0]

            if not db_path or not db_path.exists():
                # Log analysis failure
                log_service.log_analysis(
                    evidence_id=evidence_id,
                    log_type="telegram_analysis_failed",
                    message="Telegram analysis failed: No database file found",
                    details={"evidence_id": evidence_id, "reason": "no_db_file"}
                )
                return False

            # Verify it's a Telegram database
            if not is_telegram_database(db_path):
                # Log analysis failure
                log_service.log_analysis(
                    evidence_id=evidence_id,
                    log_type="telegram_analysis_failed",
                    message="Telegram analysis failed: Not a Telegram database",
                    details={"evidence_id": evidence_id, "reason": "not_telegram_db"}
                )
                return False

            # Run analysis (for now, we'll run it synchronously)
            self._perform_analysis(evidence_id, db_path, evidence, db)

            # Update evidence analyzed timestamp
            evidence.analyzed_at = datetime.utcnow()
            db.commit()

            # Log analysis success
            log_service.log_analysis(
                evidence_id=evidence_id,
                log_type="telegram_analysis_completed",
                message="Telegram analysis completed successfully",
                details={"evidence_id": evidence_id}
            )
            log_service.log_activity(
                case_id=evidence.case_id,
                action="analyze_telegram",
                description=f"Telegram forensic parser completed for evidence: {evidence.original_filename}"
            )

            return True
        except Exception as e:
            # Log error
            log_service.log_error(
                error_type="telegram_analysis_error",
                message=f"Error during Telegram analysis: {str(e)}",
                case_id=evidence.case_id if evidence else None,
                evidence_id=evidence_id,
                stack_trace=traceback.format_exc(),
                endpoint="/api/evidence/{evidence_id}/analyze/telegram",
                method="POST"
            )
            return False

    def _perform_analysis(self, evidence_id: int, db_path: Path, evidence: Evidence, db: Session):
        """
        Perform the actual Telegram analysis.

        Args:
            evidence_id: ID of evidence
            db_path: Path to Telegram database
            evidence: Evidence object
            db: Database session
        """
        # Extract data using parsers
        messages = extract_messages(db_path, evidence_id)
        contacts = extract_contacts(db_path, evidence_id)
        groups = extract_groups(db_path, evidence_id)
        media_refs = extract_media_references(db_path, evidence_id)

        # Save to database using repository
        if messages:
            self.repository.save_messages(db, messages)
        if contacts:
            self.repository.save_contacts(db, contacts)
        if groups:
            self.repository.save_groups(db, groups)
        if media_refs:
            self._save_media_items(evidence_id, media_refs, evidence, db)

    def _find_evidence_file_by_filename(self, evidence_id: int, filename: str, db: Session) -> Optional[EvidenceFile]:
        """Find an EvidenceFile by evidence_id and filename (basename match)."""
        if not filename:
            return None
        # Get all files for this evidence
        files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).all()
        for ef in files:
            # Check if the relative_path ends with '/' + filename or equals filename
            if ef.relative_path == filename or ef.relative_path.endswith('/' + filename):
                return ef
        return None

    def _save_media_items(self, evidence_id: int, media_refs: List[dict], evidence: Evidence, db: Session):
        """Save media items from media references."""
        from backend.models.models import MediaItem

        for ref in media_refs:
            # Try to find the actual file in the extracted evidence
            ef = self._find_evidence_file_by_filename(evidence_id, Path(ref["media_path"]).name, db)
            if not ef:
                # If not found, we can still create a MediaItem with placeholder? But we should skip.
                continue

            # Determine media type from mime type or from ref
            media_type = ref.get("message_type")
            if not media_type:
                mime = ef.mime_type or ""
                if mime.startswith("image/"):
                    media_type = "image"
                elif mime.startswith("video/"):
                    media_type = "video"
                elif mime.startswith("audio/"):
                    media_type = "audio"
                else:
                    media_type = "other"

            # Get the actual file path
            file_path = Path(evidence.extracted_path or evidence.storage_path) / ef.relative_path

            # Detect media type more accurately using file content
            detected_media_type = detect_media_type(file_path) or media_type

            # Extract metadata from the file
            metadata = extract_media_metadata(file_path, detected_media_type)

            # Build MediaItem record with actual metadata
            media_item = MediaItem(
                case_id=evidence.case_id,
                evidence_id=evidence_id,
                file_path=str(file_path),
                sha256=ef.sha256,
                mime_type=ef.mime_type,
                media_type=detected_media_type,
                file_size=ef.file_size,
                width=metadata.get("width"),
                height=metadata.get("height"),
                duration=metadata.get("duration"),
                exif_data=metadata.get("exif_data", {}),
                is_orphan=False,  # Will be determined by correlation phase
                linked_message_id=ref["message_id"],
            )
            db.add(media_item)
        db.commit()

    def get_messages(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get Telegram messages for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_messages_by_evidence_id(db, evidence_id)

    def get_contacts(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get Telegram contacts for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_contacts_by_evidence_id(db, evidence_id)

    def get_groups(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get Telegram groups for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_groups_by_evidence_id(db, evidence_id)

    def get_media_references(self, evidence_id: int, db: Session) -> List[dict]:
        """Get media references from Telegram messages for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None

        messages = self.repository.get_messages_by_evidence_id(db, evidence_id)
        media_refs = []

        for msg in messages:
            if msg.media_path and msg.media_type:
                media_refs.append({
                    "message_id": msg.message_id,
                    "media_path": msg.media_path,
                    "media_type": msg.media_type,
                    "file_size": getattr(msg, 'file_size', None),
                    "width": getattr(msg, 'width', None),
                    "height": getattr(msg, 'height', None),
                    "duration": getattr(msg, 'duration', None)
                })

        return media_refs


# Singleton instance
telegram_service = TelegramService()