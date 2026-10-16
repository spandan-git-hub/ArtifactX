"""
Backend pipeline orchestration service (spec 11_PIPELINE_AND_E2E.md §B13.2).

Coordinates:
- Concurrent run exclusion (HTTP 409 on overlap)
- Exhibit collection with R19 deferred BYTEA query discipline
- Hash-chained audit logging (PIPELINE_START, STAGE_*, PIPELINE_COMPLETE)
- Pure core execution (forensic.pipeline.run_pipeline)
- Results persistence across domain repositories (WhatsApp, Telegram, Recovery, Timeline, Correlation)
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import io
from typing import Any, Dict, List, Optional
import uuid
import zipfile

from sqlalchemy.orm import Session, load_only

from backend.models.models import (
    Case,
    DerivedArtifact,
    Evidence,
    EvidenceFile,
    PipelineRun,
    RecoveredFinding,
)
from backend.repositories.correlation_repo import CorrelationRepository
from backend.repositories.pipeline_repo import PipelineRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.repositories.timeline_repo import TimelineRepository
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.schemas.pipeline import PipelineRunRequest
from backend.services.audit_service import AuditService
from backend.services.integrity_service import (
    ensure_integrity,
    EvidenceIntegrityError,
    LegacyUnverifiableError,
)
from forensic.common.hashing import sha256_hex
from forensic.correlation.models import CorrelationFinding
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput, PipelineConfig
from forensic.recovery.models import RecoveryFinding
from forensic.telegram.models import TgParseResult
from forensic.timeline.models import TimelineEvent, SourceRef, TimeValue
from forensic.whatsapp.parser import WAParseResult


class ConcurrentPipelineRunError(Exception):
    """Raised when another pipeline run is already IN_PROGRESS for the same case (spec B13.2)."""
    pass


class PipelineService:
    """Service orchestrating end-to-end pipeline execution and persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PipelineRepository(db)
        self.wa_repo = WhatsAppRepository()
        self.tg_repo = TelegramRepository()
        self.timeline_repo = TimelineRepository()
        self.correlation_repo = CorrelationRepository()

    def execute_pipeline(
        self,
        case_id: int,
        req: Optional[PipelineRunRequest] = None,
    ) -> PipelineRun:
        """
        Execute end-to-end analysis pipeline for a case and persist findings.

        Raises:
            ConcurrentPipelineRunError: if another run is currently IN_PROGRESS for this case.
            ValueError: if case is not found or has no evidence.
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # 1. Enforce single-flight concurrency lock per case (spec B13.2)
        active_run = self.repo.get_active_run_for_case(case_id)
        if active_run:
            raise ConcurrentPipelineRunError(
                f"Pipeline run '{active_run.id}' is already IN_PROGRESS for case {case_id}."
            )

        payload = req or PipelineRunRequest()
        run_id = f"pipe_{uuid.uuid4().hex[:16]}"

        # 2. Initialize PipelineRun record
        run = self.repo.create_run(
            run_id=run_id,
            case_id=case_id,
            config_json=payload.config or {},
        )

        AuditService.append(
            db=self.db,
            action="PIPELINE_START",
            case_id=case_id,
            details={"run_id": run_id, "config": payload.config or {}},
        )

        try:
            # 3. Collect exhibits with pre-stage integrity verification (R3, R19)
            ev_query = (
                self.db.query(Evidence)
                .options(load_only(
                    Evidence.id,
                    Evidence.case_id,
                    Evidence.sha256,
                    Evidence.original_filename,
                    Evidence.evidence_type,
                    Evidence.content_bytes,
                ))
                .filter(Evidence.case_id == case_id)
            )
            if payload.evidence_ids:
                ev_query = ev_query.filter(Evidence.id.in_(payload.evidence_ids))

            evidences = ev_query.all()
            if not evidences:
                # Complete as empty COMPLETED run
                self.repo.complete_run(
                    run_id=run_id,
                    status="COMPLETED",
                    content_hash=sha256_hex(b"empty_case"),
                    summary_json={"message": "No evidence items found for case"},
                )
                AuditService.append(
                    db=self.db,
                    action="PIPELINE_COMPLETE",
                    case_id=case_id,
                    details={"run_id": run_id, "status": "COMPLETED", "summary": "Empty case"},
                )
                return self.repo.get_run_with_stages(run_id) or run

            evidence_inputs: List[EvidenceInput] = []

            for ev in evidences:
                # Pre-stage integrity verification (R3, spec B13.1, B13.4):
                # Verify cryptographic hash; if tampered or unverifiable, flags state in DB
                # and passes to pure pipeline where Stage 1 records typed INTEGRITY_FAILURE
                try:
                    ensure_integrity(ev.id, self.db, action_context="pipeline_orchestrator")
                except (EvidenceIntegrityError, LegacyUnverifiableError):
                    pass

                ev_bytes = ev.content_bytes or b""
                fn = ev.original_filename or f"evidence_{ev.id}"

                # If evidence is a ZIP archive, unpack members in-memory (R12 safety caps)
                if fn.lower().endswith(".zip") or ev.evidence_type == "media_zip":
                    evidence_inputs.append(
                        EvidenceInput(
                            evidence_id=str(ev.id),
                            sha256=ev.sha256,
                            name=fn,
                            data=ev_bytes,
                            role="media_zip",
                        )
                    )
                    try:
                        zf = zipfile.ZipFile(io.BytesIO(ev_bytes), "r")
                        members = zf.namelist()[:500]
                        for m_name in members:
                            if m_name.endswith("/"):
                                continue
                            m_bytes = zf.read(m_name)
                            m_hash = sha256_hex(m_bytes)
                            m_lower = m_name.lower()
                            role = "other"
                            if "msgstore" in m_lower and (m_lower.endswith(".db") or m_lower.endswith(".sqlite")):
                                role = "primary"
                            elif m_lower.endswith("-wal"):
                                role = "wal"
                            elif m_lower.endswith("-shm"):
                                role = "shm"
                            elif "wa.db" in m_lower or "contacts.db" in m_lower:
                                role = "wa_contacts"
                            elif any(m_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                                role = "other"

                            evidence_inputs.append(
                                EvidenceInput(
                                    evidence_id=f"{ev.id}_{m_name}",
                                    sha256=m_hash,
                                    name=m_name,
                                    data=m_bytes,
                                    role=role,
                                )
                            )
                    except Exception:
                        pass
                else:
                    role = "primary"
                    fn_lower = fn.lower()
                    if fn_lower.endswith("-wal"):
                        role = "wal"
                    elif fn_lower.endswith("-shm"):
                        role = "shm"
                    elif "wa.db" in fn_lower or "contacts.db" in fn_lower:
                        role = "wa_contacts"

                    evidence_inputs.append(
                        EvidenceInput(
                            evidence_id=str(ev.id),
                            sha256=ev.sha256,
                            name=fn,
                            data=ev_bytes,
                            role=role,
                        )
                    )

            # 4. Construct KeyMaterial objects (R5 radioactive keys)
            key_materials: List[KeyMaterial] = []
            for k in payload.keys or []:
                raw_bytes = None
                if k.key_file_b64:
                    try:
                        raw_bytes = base64.b64decode(k.key_file_b64)
                    except Exception:
                        pass
                key_materials.append(
                    KeyMaterial(
                        raw_key=raw_bytes,
                        key_hex=k.key_hex,
                        key_type=k.key_type,
                    )
                )

            # 5. Build pipeline configuration
            cfg = PipelineConfig(
                thresholds_version="1.0.0",
                max_unpacked_bytes=256 * 1024 * 1024,
                correlation_params=(payload.config or {}).get("correlation_params", {}),
                custom_keywords=tuple((payload.config or {}).get("custom_keywords", ())),
            )

            # 6. Execute pure core pipeline
            pipeline_result = run_pipeline(
                inputs=evidence_inputs,
                keys=key_materials,
                cfg=cfg,
                run_id=run_id,
            )

            # 7. Record each stage in DB and audit log
            for stage in pipeline_result.stages:
                self.repo.record_stage_run(
                    run_id=run_id,
                    stage=stage.stage,
                    status=stage.status,
                    evidence_id=stage.evidence_id,
                    error_code=stage.error_code,
                    skip_reason=stage.skip_reason,
                    counts_json=stage.counts,
                    output_hash=stage.output_hash,
                    duration_ms=stage.duration_ms,
                    errors_json=list(stage.errors),
                )
                AuditService.append(
                    db=self.db,
                    action=f"STAGE_{stage.status}",
                    case_id=case_id,
                    evidence_id=int(stage.evidence_id) if stage.evidence_id and stage.evidence_id.isdigit() else None,
                    details={
                        "stage": stage.stage,
                        "status": stage.status,
                        "counts": stage.counts,
                        "output_hash": stage.output_hash,
                        "error_code": stage.error_code,
                    },
                )

            # 8. Persist decrypted databases into DerivedArtifact
            for ev_id_str, dec_bytes in pipeline_result.data.get("decrypted_databases", {}).items():
                ev_id_int = int(ev_id_str) if ev_id_str.isdigit() else None
                if not ev_id_int or not isinstance(dec_bytes, (bytes, bytearray)):
                    continue
                dec_hash = sha256_hex(dec_bytes)
                existing = self.db.query(DerivedArtifact).filter(
                    DerivedArtifact.case_id == case_id,
                    DerivedArtifact.sha256 == dec_hash,
                ).first()
                if not existing:
                    art = DerivedArtifact(
                        case_id=case_id,
                        parent_evidence_id=ev_id_int,
                        artifact_type="decrypted_sqlite",
                        original_filename=f"decrypted_{ev_id_str}.db",
                        sha256=dec_hash,
                        size_bytes=len(dec_bytes),
                        content_bytes=dec_bytes,
                        provenance={"derived_from_evidence_id": ev_id_str},
                        created_at=datetime.now(timezone.utc),
                    )
                    self.db.add(art)
                    self.db.commit()

            # 9. Persist domain findings idempotently via repositories
            # WhatsApp
            wa_repo = WhatsAppRepository()
            for ev_id_str, wa_res in pipeline_result.data.get("parsed_wa", {}).items():
                ev_id_int = int(ev_id_str) if ev_id_str.isdigit() else None
                if ev_id_int and hasattr(wa_res, "messages"):
                    wa_repo.save_parse_result(self.db, ev_id_int, wa_res)
                    ev_obj = self.db.query(Evidence).filter(Evidence.id == ev_id_int).first()
                    if ev_obj:
                        ev_obj.analyzed_at = datetime.now(timezone.utc)
                        self.db.commit()

            # Telegram
            tg_repo = TelegramRepository()
            for ev_id_str, tg_res in pipeline_result.data.get("parsed_tg", {}).items():
                ev_id_int = int(ev_id_str) if ev_id_str.isdigit() else None
                if ev_id_int and hasattr(tg_res, "messages"):
                    tg_repo.save_parse_result(self.db, ev_id_int, tg_res)
                    ev_obj = self.db.query(Evidence).filter(Evidence.id == ev_id_int).first()
                    if ev_obj:
                        ev_obj.analyzed_at = datetime.now(timezone.utc)
                        self.db.commit()

            # Timeline
            tl_repo = TimelineRepository()
            tl_res = pipeline_result.data.get("timeline")
            if tl_res and hasattr(tl_res, "events") and tl_res.events:
                tl_repo.delete_events_by_case_id(self.db, case_id)
                db_events = []
                for ev in tl_res.events:
                    norm_dt = None
                    if ev.time.utc_ms is not None:
                        try:
                            norm_dt = datetime.fromtimestamp(ev.time.utc_ms / 1000.0, tz=timezone.utc)
                        except Exception:
                            pass

                    ev_id = None
                    for ref in ev.source_refs:
                        if ref.evidence_id and ref.evidence_id.isdigit():
                            ev_id = int(ref.evidence_id)
                            break

                    db_events.append({
                        "case_id": case_id,
                        "evidence_id": ev_id,
                        "event_type": ev.kind,
                        "source_app": ev.app,
                        "timestamp": ev.time.utc_ms if ev.time.utc_ms is not None else 0,
                        "normalized_timestamp": norm_dt,
                        "entity_id": ev.actor_ref or ev.chat_ref or str(ev_id or ""),
                        "entity_type": ev.kind,
                        "description": ev.summary,
                        "metadata_": ev.metadata,
                        "event_id": ev.event_id,
                        "utc_ms": ev.time.utc_ms,
                        "time_unit": ev.time.unit,
                        "tz_basis": ev.time.tz_basis,
                        "time_flags": list(ev.time.flags),
                        "raw_timestamp": str(ev.time.raw),
                        "actor_ref": ev.actor_ref,
                        "chat_ref": ev.chat_ref,
                        "summary": ev.summary,
                        "source_refs": [ref.to_dict() for ref in ev.source_refs],
                        "confidence_score": ev.confidence_score,
                        "strength": ev.strength,
                        "limitations": list(ev.limitations),
                    })
                tl_repo.save_events(self.db, db_events)

            # Correlation findings
            corr_repo = CorrelationRepository()
            corr_findings = pipeline_result.data.get("correlations") or []
            if corr_findings:
                findings_dicts = [f.to_dict() if hasattr(f, "to_dict") else f for f in corr_findings]
                corr_repo.save_correlation_findings(self.db, case_id, findings_dicts)

            # 10. Complete pipeline run
            self.repo.complete_run(
                run_id=run_id,
                status=pipeline_result.status,
                content_hash=pipeline_result.content_hash,
                summary_json=pipeline_result.summary,
            )

            AuditService.append(
                db=self.db,
                action="PIPELINE_COMPLETE",
                case_id=case_id,
                details={
                    "run_id": run_id,
                    "status": pipeline_result.status,
                    "content_hash": pipeline_result.content_hash,
                    "summary": pipeline_result.summary,
                },
            )

            return self.repo.get_run_with_stages(run_id) or run

        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            # Mark run as FAILED and record error
            self.repo.complete_run(
                run_id=run_id,
                status="FAILED",
                summary_json={"error": str(e)},
            )
            AuditService.append(
                db=self.db,
                action="PIPELINE_ERROR",
                case_id=case_id,
                details={"run_id": run_id, "error": str(e)},
            )
            raise
