"""WhatsApp analysis service."""

import asyncio
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.config import UPLOADS_DIR
from forensic.whatsapp.detector import is_whatsapp_database
from forensic.whatsapp.message_parser import extract_messages
from forensic.whatsapp.contact_parser import extract_contacts
from forensic.whatsapp.group_parser import extract_groups
from forensic.whatsapp.media_parser import extract_media_references
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.models.models import Evidence, WhatsAppMessage, WhatsAppContact, WhatsAppGroup, EvidenceFile
from datetime import datetime


class WhatsAppService:
    """Service for WhatsApp analysis operations."""

    def __init__(self):
        self.repository = WhatsAppRepository()

    async def analyze_evidence(self, evidence_id: int, db: Session) -> bool:
        """
        Trigger WhatsApp analysis on evidence.

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

        # Check if evidence has extracted path (for ZIP files)
        if not evidence.extracted_path:
            # For non-ZIP evidence, check if the storage file itself is a WhatsApp DB
            db_path = Path(evidence.storage_path)
        else:
            # For ZIP evidence, we need to find WhatsApp database in extracted files
            # For now, we'll look for any .db files in the extracted path
            # In a more sophisticated implementation, we'd scan for WhatsApp-specific files
            db_path = None
            extracted_dir = Path(evidence.extracted_path)
            if extracted_dir.exists():
                # Look for WhatsApp database files
                for db_file in extracted_dir.rglob("*.db"):
                    if is_whatsapp_database(db_file):
                        db_path = db_file
                        break
                # If no specific WhatsApp DB found, try the first .db file
                if not db_path:
                    db_files = list(extracted_dir.rglob("*.db"))
                    if db_files:
                        db_path = db_files[0]

        if not db_path or not db_path.exists():
            return False

        # Verify it's a WhatsApp database
        if not is_whatsapp_database(db_path):
            return False

        # Run analysis (for now, we'll run it synchronously)
        self._perform_analysis(evidence_id, db_path, evidence, db)

        # Update evidence analyzed timestamp
        evidence.analyzed_at = datetime.utcnow()
        db.commit()

        return True

    def _perform_analysis(self, evidence_id: int, db_path: Path, evidence: Evidence, db: Session):
        """
        Perform the actual WhatsApp analysis.

        Args:
            evidence_id: ID of evidence
            db_path: Path to WhatsApp database
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

            # Build MediaItem record
            media_item = MediaItem(
                case_id=evidence.case_id,
                evidence_id=evidence_id,
                file_path=str(Path(evidence.extracted_path or evidence.storage_path) / ef.relative_path),
                sha256=ef.sha256,
                mime_type=ef.mime_type,
                media_type=media_type,
                file_size=ef.file_size,
                width=None,  # To be filled by media analysis phase
                height=None,
                duration=None,
                exif_data={},  # To be filled by media analysis phase
                is_orphan=False,  # Will be determined by correlation phase
                linked_message_id=ref["message_id"],
            )
            db.add(media_item)
        db.commit()

    def get_messages(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get WhatsApp messages for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_messages_by_evidence_id(db, evidence_id)

    def get_contacts(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get WhatsApp contacts for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_contacts_by_evidence_id(db, evidence_id)

    def get_groups(self, evidence_id: int, db: Session) -> Optional[List]:
        """Get WhatsApp groups for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_groups_by_evidence_id(db, evidence_id)

    def get_media_references(self, evidence_id: int, db: Session) -> List[dict]:
        """Get media references from WhatsApp messages for evidence."""
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
whatsapp_service = WhatsAppService()