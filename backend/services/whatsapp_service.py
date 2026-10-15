"""
WhatsApp analysis service (spec B7.5, master.md R3, R4, R12, R18).
Integrates integrity verification (ensure_integrity), pure in-memory parsing,
hash-chained audit logging, and idempotent atomic database persistence.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from backend.models.models import (
    DerivedArtifact,
    Evidence,
    EvidenceFile,
    WhatsAppChat,
    WhatsAppContact,
    WhatsAppEdit,
    WhatsAppGroup,
    WhatsAppMessage,
    WhatsAppRevocation,
)
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.services.audit_service import AuditService
from backend.services.integrity_service import LegacyUnverifiableError, ensure_integrity
from backend.services.log_service import get_log_service
from forensic.whatsapp.parser import WAParseResult, WhatsAppParser


class WhatsAppService:
    """Service for WhatsApp analysis and forensic parsing operations."""

    def __init__(self):
        self.repository = WhatsAppRepository()

    def _extract_db_sources(
        self,
        evidence: Evidence,
        db: Session,
        derived_artifact_id: Optional[str] = None,
    ) -> Tuple[Optional[bytes], Optional[bytes], Optional[str]]:
        """
        Locate msgstore.db bytes and optional wa.db bytes prioritizing pure in-memory storage (R4).
        Returns: (msgstore_bytes, wa_db_bytes, sha256_of_msgstore).
        """
        # 1. If derived_artifact_id is specified, fetch from DerivedArtifact table
        if derived_artifact_id:
            artifact = None
            try:
                art_id_int = int(derived_artifact_id)
                artifact = db.query(DerivedArtifact).filter(
                    DerivedArtifact.id == art_id_int
                ).first()
            except ValueError:
                pass
            if not artifact:
                artifact = db.query(DerivedArtifact).filter(
                    (DerivedArtifact.sha256 == derived_artifact_id)
                    | (DerivedArtifact.original_filename == derived_artifact_id)
                ).first()
            if artifact and artifact.content_bytes:
                return artifact.content_bytes, None, artifact.sha256

        # 2. Check extracted files from ZIP package in EvidenceFile
        ef_list = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence.id).all()
        msgstore_bytes: Optional[bytes] = None
        wa_db_bytes: Optional[bytes] = None
        msgstore_sha256: Optional[str] = None

        for ef in ef_list:
            name_lower = ef.relative_path.lower()
            if "msgstore" in name_lower and (name_lower.endswith(".db") or name_lower.endswith(".sqlite")):
                if ef.content_bytes:
                    msgstore_bytes = ef.content_bytes
                    msgstore_sha256 = ef.sha256
            elif "wa.db" in name_lower and ef.content_bytes:
                wa_db_bytes = ef.content_bytes

        if msgstore_bytes:
            return msgstore_bytes, wa_db_bytes, msgstore_sha256 or evidence.sha256

        # 3. Direct evidence content bytes
        if evidence.content_bytes:
            # Check if it starts with SQLite header
            if evidence.content_bytes.startswith(b"SQLite format 3\x00"):
                return evidence.content_bytes, wa_db_bytes, evidence.sha256

        # 4. Check filesystem fallback for local test fixtures
        if evidence.extracted_path:
            p = Path(evidence.extracted_path)
            if p.exists():
                for f in p.rglob("*.db"):
                    if "msgstore" in f.name.lower() and f.is_file():
                        msgstore_bytes = f.read_bytes()
                        break
                wa_file = p / "wa.db"
                if wa_file.exists() and wa_file.is_file():
                    wa_db_bytes = wa_file.read_bytes()
                if msgstore_bytes:
                    return msgstore_bytes, wa_db_bytes, evidence.sha256

        if evidence.storage_path:
            p = Path(evidence.storage_path)
            if p.exists() and p.is_file() and p.name.endswith(".db"):
                return p.read_bytes(), wa_db_bytes, evidence.sha256

        return None, None, None

    def parse_evidence_sync(
        self,
        evidence_id: int,
        db: Session,
        derived_artifact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synchronously parse WhatsApp evidence with integrity enforcement and audit chaining (B7.5).
        """
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise FileNotFoundError(f"Evidence {evidence_id} not found")

        log_service = get_log_service(db)
        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="whatsapp_parse_start",
            message="Starting WhatsApp forensic parsing",
            details={"evidence_id": evidence_id, "derived_artifact_id": derived_artifact_id},
        )

        # 1. Enforce evidence cryptographic integrity check (B5.3, master.md R3)
        if not derived_artifact_id:
            ensure_integrity(evidence_id, db, action_context="whatsapp_parse")

        # 2. Extract database bytes
        msgstore_bytes, wa_db_bytes, db_sha256 = self._extract_db_sources(evidence, db, derived_artifact_id)
        if not msgstore_bytes:
            err_msg = "No valid WhatsApp database found in evidence content"
            log_service.log_analysis(
                evidence_id=evidence_id,
                log_type="whatsapp_parse_failed",
                message=err_msg,
                details={"evidence_id": evidence_id},
            )
            raise ValueError(err_msg)

        # 3. Execute pure forensic parser (B7.0-B7.4)
        parser = WhatsAppParser(
            msgstore_source=msgstore_bytes,
            evidence_id=str(evidence_id),
            evidence_sha256=db_sha256 or evidence.sha256,
            wa_db_source=wa_db_bytes,
            derived_from_artifact_id=derived_artifact_id,
        )
        parse_result = parser.parse()

        # 4. Save to database atomically and idempotently (B7.5)
        self.repository.save_parse_result(
            db=db,
            evidence_id=evidence_id,
            parse_result=parse_result,
            derived_artifact_id=derived_artifact_id,
        )

        evidence.analyzed_at = datetime.utcnow()
        db.commit()

        # 5. Append to cryptographic hash-chained audit log (B5.5, R3, R11)
        audit_details = {
            "evidence_id": evidence_id,
            "evidence_sha256": db_sha256 or evidence.sha256,
            "schema_family": parse_result.schema_family.family,
            "messages_count": len(parse_result.messages),
            "chats_count": len(parse_result.chats),
            "contacts_count": len(parse_result.contacts),
            "revocations_count": len(parse_result.revocations),
            "edits_count": len(parse_result.edits),
            "limitations": list(parse_result.limitations),
            "derived_artifact_id": derived_artifact_id,
        }
        AuditService.append(
            db=db,
            action="whatsapp_parse",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence_id,
            details=audit_details,
        )

        # 6. Activity & analysis logs
        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="whatsapp_parse_completed",
            message="WhatsApp forensic parsing completed successfully",
            details=audit_details,
        )
        log_service.log_activity(
            case_id=evidence.case_id,
            action="parse_whatsapp",
            description=f"WhatsApp parsing completed: {len(parse_result.messages)} messages, {len(parse_result.chats)} chats, {len(parse_result.revocations)} revocations.",
        )

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "schema_family": parse_result.schema_family.family,
            "messages_count": len(parse_result.messages),
            "chats_count": len(parse_result.chats),
            "contacts_count": len(parse_result.contacts),
            "revocations_count": len(parse_result.revocations),
            "edits_count": len(parse_result.edits),
            "limitations": list(parse_result.limitations),
        }

    async def analyze_evidence(self, evidence_id: int, db: Session) -> bool:
        """Async wrapper for compatibility with existing routers."""
        try:
            self.parse_evidence_sync(evidence_id, db)
            return True
        except Exception as e:
            get_log_service(db).log_error(
                error_type="whatsapp_parse_error",
                message=f"Error during WhatsApp parsing: {str(e)}",
                evidence_id=evidence_id,
                stack_trace=traceback.format_exc(),
                endpoint=f"/api/whatsapp/parse/{evidence_id}",
                method="POST",
            )
            return False

    def get_messages(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppMessage]]:
        """Get parsed WhatsApp messages for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_messages_by_evidence_id(db, evidence_id)

    def get_chats(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppChat]]:
        """Get parsed WhatsApp chats for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_chats_by_evidence_id(db, evidence_id)

    def get_contacts(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppContact]]:
        """Get parsed WhatsApp contacts for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_contacts_by_evidence_id(db, evidence_id)

    def get_groups(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppGroup]]:
        """Get parsed WhatsApp groups for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_groups_by_evidence_id(db, evidence_id)

    def get_revocations(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppRevocation]]:
        """Get parsed WhatsApp revocation records for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_revocations_by_evidence_id(db, evidence_id)

    def get_edits(self, evidence_id: int, db: Session) -> Optional[List[WhatsAppEdit]]:
        """Get parsed WhatsApp edit records for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_edits_by_evidence_id(db, evidence_id)

    def get_media_references(self, evidence_id: int, db: Session) -> Optional[List[Dict[str, Any]]]:
        """Get media references from WhatsApp messages."""
        msgs = self.get_messages(evidence_id, db)
        if msgs is None:
            return None
        return [
            {
                "message_id": m.message_id,
                "media_path": m.media_path,
                "media_type": m.media_type,
                "timestamp": m.timestamp,
            }
            for m in msgs
            if m.media_path
        ]


whatsapp_service = WhatsAppService()