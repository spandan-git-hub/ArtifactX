"""
Telegram analysis service (spec B9.5, B9.6).

Orchestrates evidence integrity checks, multi-view parsing, idempotent persistence,
and hash-chained audit logging per master.md R3, R4, R8, R10, R11, R18, and R19.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, load_only

from backend.models.models import (
    Evidence,
    EvidenceFile,
    MediaItem,
    TelegramChat,
    TelegramContact,
    TelegramDialog,
    TelegramGroup,
    TelegramMessage,
    TelegramUnparsedBlob,
    TelegramUser,
)
from backend.repositories.telegram_repo import TelegramRepository
from backend.services.audit_service import AuditService
from backend.services.integrity_service import ensure_integrity
from backend.services.log_service import get_log_service
from forensic.telegram.parser import TelegramParser


class TelegramService:
    """Service for Telegram forensic analysis operations."""

    def __init__(self):
        self.repository = TelegramRepository()

    def _extract_db_sources(
        self,
        evidence: Evidence,
        db: Session,
    ) -> Tuple[Optional[bytes], Optional[bytes], Optional[bytes], Optional[str]]:
        """
        Extract main DB bytes, optional WAL bytes, and optional SHM bytes in memory (R4, R19).
        Never writes evidence to disk.
        """
        db_bytes: Optional[bytes] = None
        wal_bytes: Optional[bytes] = None
        shm_bytes: Optional[bytes] = None
        evidence_sha = evidence.sha256

        # 1. Check attached EvidenceFile records (e.g. from ZIP extraction or evidence set)
        ef_list = (
            db.query(EvidenceFile)
            .filter(EvidenceFile.evidence_id == evidence.id)
            .options(load_only(EvidenceFile.id, EvidenceFile.relative_path, EvidenceFile.content_bytes))
            .all()
        )
        by_path: Dict[str, bytes] = {}
        for ef in ef_list:
            cb = ef.content_bytes
            if cb:
                by_path[ef.relative_path.replace("\\", "/")] = cb

        db_candidates = [
            p for p in by_path.keys()
            if p.lower().endswith("cache4.db") or p.lower().endswith(".db") or p.lower().endswith(".sqlite")
        ]

        def _candidate_score(p: str) -> int:
            score = 0
            p_low = p.lower()
            if "files/cache4.db" in p_low:
                score += 1000000000
            elif "cache4.db" in p_low:
                score += 500000000
            wal_p = p + "-wal"
            if wal_p in by_path:
                score += len(by_path[wal_p])
            score += len(by_path[p])
            return score

        db_candidates.sort(key=_candidate_score, reverse=True)
        if db_candidates:
            best_db = db_candidates[0]
            db_bytes = by_path[best_db]
            wal_bytes = by_path.get(best_db + "-wal")
            shm_bytes = by_path.get(best_db + "-shm")

        # 2. Check sibling evidence items in the same evidence_set_id (B9.5)
        if evidence.evidence_set_id:
            siblings = (
                db.query(Evidence)
                .filter(
                    Evidence.case_id == evidence.case_id,
                    Evidence.evidence_set_id == evidence.evidence_set_id,
                    Evidence.id != evidence.id,
                )
                .options(load_only(Evidence.id, Evidence.original_filename, Evidence.evidence_role, Evidence.content_bytes))
                .all()
            )
            for sib in siblings:
                if not sib.content_bytes:
                    continue
                fn_lower = (sib.original_filename or "").lower()
                role = (sib.evidence_role or "").lower()
                if role == "wal" or fn_lower.endswith("-wal") or fn_lower.endswith(".db-wal"):
                    if wal_bytes is None:
                        wal_bytes = sib.content_bytes
                elif role == "shm" or fn_lower.endswith("-shm") or fn_lower.endswith(".db-shm"):
                    if shm_bytes is None:
                        shm_bytes = sib.content_bytes
                elif role in ("db", "main") and db_bytes is None:
                    db_bytes = sib.content_bytes

        # 3. Check evidence.content_bytes directly
        if db_bytes is None:
            ev_row = (
                db.query(Evidence)
                .filter(Evidence.id == evidence.id)
                .options(load_only(Evidence.id, Evidence.content_bytes))
                .first()
            )
            if ev_row and ev_row.content_bytes:
                db_bytes = ev_row.content_bytes

        # 4. Check extracted or storage path if any source is still None
        if db_bytes is None or wal_bytes is None or shm_bytes is None:
            if evidence.extracted_path:
                ext_dir = Path(evidence.extracted_path)
                if ext_dir.is_dir():
                    for p in ext_dir.rglob("cache4.db"):
                        if p.is_file():
                            if db_bytes is None:
                                db_bytes = p.read_bytes()
                            wp = p.with_name(p.name + "-wal")
                            if wal_bytes is None and wp.is_file():
                                wal_bytes = wp.read_bytes()
                            sp = p.with_name(p.name + "-shm")
                            if shm_bytes is None and sp.is_file():
                                shm_bytes = sp.read_bytes()
                            break

            if evidence.storage_path:
                p = Path(evidence.storage_path)
                if p.is_file():
                    if db_bytes is None:
                        db_bytes = p.read_bytes()
                    wp = p.with_name(p.name + "-wal")
                    if wal_bytes is None and wp.is_file():
                        wal_bytes = wp.read_bytes()
                    sp = p.with_name(p.name + "-shm")
                    if shm_bytes is None and sp.is_file():
                        shm_bytes = sp.read_bytes()

        return db_bytes, wal_bytes, shm_bytes, evidence_sha

    def parse_evidence_sync(
        self,
        evidence_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Synchronously parse Telegram evidence with cryptographic integrity enforcement and audit chaining (B9.5, B9.6).
        """
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise FileNotFoundError(f"Evidence {evidence_id} not found")

        log_service = get_log_service(db)
        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="telegram_analysis_start",
            message="Starting Telegram forensic analysis",
            details={"evidence_id": evidence_id},
        )

        # 1. Enforce cryptographic integrity before stage execution (B5.3, master.md R3)
        ensure_integrity(evidence_id, db, action_context="telegram_parse")

        # 2. Extract in-memory database and WAL/SHM sources (zero disk writes, R4)
        db_bytes, wal_bytes, shm_bytes, db_sha = self._extract_db_sources(evidence, db)
        if not db_bytes:
            err_msg = "No valid Telegram database found in evidence content"
            log_service.log_analysis(
                evidence_id=evidence_id,
                log_type="telegram_analysis_failed",
                message=err_msg,
                details={"evidence_id": evidence_id},
            )
            raise ValueError(err_msg)

        # 3. Execute pure forensic parser (B9.1-B9.5)
        parser = TelegramParser(
            db_source=db_bytes,
            wal_source=wal_bytes,
            shm_source=shm_bytes,
            evidence_id=str(evidence_id),
            evidence_sha256=db_sha or evidence.sha256,
        )
        parse_result = parser.parse()

        # 4. Save to database atomically and idempotently (B9.6)
        self.repository.save_parse_result(
            db=db,
            evidence_id=evidence_id,
            result=parse_result,
        )

        evidence.analyzed_at = datetime.utcnow()
        db.commit()

        # 5. Append to cryptographic hash-chained audit log (B5.5, R3, R11)
        audit_details = {
            "status": "success",
            "evidence_id": evidence_id,
            "evidence_sha256": db_sha or evidence.sha256,
            "schema_family": parse_result.schema_info.family,
            "messages_count": len(parse_result.messages),
            "dialogs_count": len(parse_result.dialogs),
            "users_count": len(parse_result.users),
            "chats_count": len(parse_result.chats),
            "unparsed_blobs_count": len(parse_result.unparsed_blobs),
            "views_parsed": list(parse_result.views_parsed),
            "limitations": list(parse_result.limitations),
        }
        AuditService.append(
            db=db,
            action="STAGE_COMPLETED",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence_id,
            details=audit_details,
        )

        log_service.log_analysis(
            evidence_id=evidence_id,
            log_type="telegram_analysis_completed",
            message="Telegram forensic analysis completed successfully",
            details=audit_details,
        )

        return audit_details

    async def analyze_evidence(self, evidence_id: int, db: Session) -> bool:
        """Trigger Telegram analysis on evidence asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.parse_evidence_sync, evidence_id, db)
            return True
        except Exception as e:
            evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
            log_service = get_log_service(db)
            log_service.log_error(
                error_type="telegram_analysis_error",
                message=f"Error during Telegram analysis: {str(e)}",
                case_id=evidence.case_id if evidence else None,
                evidence_id=evidence_id,
                stack_trace=traceback.format_exc(),
                endpoint=f"/api/evidence/{evidence_id}/analyze/telegram",
                method="POST",
            )
            return False

    def get_messages(self, evidence_id: int, db: Session) -> Optional[List[TelegramMessage]]:
        """Get extracted Telegram messages for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_messages_by_evidence_id(db, evidence_id)

    def get_dialogs(self, evidence_id: int, db: Session) -> Optional[List[TelegramDialog]]:
        """Get extracted Telegram dialogs for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_dialogs_by_evidence_id(db, evidence_id)

    def get_users(self, evidence_id: int, db: Session) -> Optional[List[TelegramUser]]:
        """Get extracted Telegram users for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_users_by_evidence_id(db, evidence_id)

    def get_chats(self, evidence_id: int, db: Session) -> Optional[List[TelegramChat]]:
        """Get extracted Telegram chats for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_chats_by_evidence_id(db, evidence_id)

    def get_unparsed_blobs(self, evidence_id: int, db: Session) -> Optional[List[TelegramUnparsedBlob]]:
        """Get extracted Telegram unparsed blobs for evidence."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_unparsed_blobs_by_evidence_id(db, evidence_id)

    def get_contacts(self, evidence_id: int, db: Session) -> Optional[List[TelegramContact]]:
        """Get extracted Telegram contacts for evidence (legacy compatibility)."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_contacts_by_evidence_id(db, evidence_id)

    def get_groups(self, evidence_id: int, db: Session) -> Optional[List[TelegramGroup]]:
        """Get extracted Telegram groups for evidence (legacy compatibility)."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        return self.repository.get_groups_by_evidence_id(db, evidence_id)

    def get_media_references(self, evidence_id: int, db: Session) -> Optional[List[Dict[str, Any]]]:
        """Get media references extracted from Telegram messages."""
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return None
        messages = self.repository.get_messages_by_evidence_id(db, evidence_id)
        media_refs: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.media_kind or msg.media_type:
                media_refs.append(
                    {
                        "message_id": msg.mid or msg.message_id,
                        "dialog_id": msg.dialog_id,
                        "media_type": msg.media_kind or msg.media_type,
                        "media_path": msg.media_ref or msg.media_path,
                        "timestamp": msg.date_utc_ms or msg.timestamp,
                    }
                )
        return media_refs


telegram_service = TelegramService()