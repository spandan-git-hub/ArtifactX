"""Timeline reconstruction service (B11 Timeline & Time Handling, Rules R3, R8, R10, R11, R18, R19)."""

import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, load_only

from backend.models.models import (
    Evidence,
    DerivedArtifact,
    MediaItem,
    RecoveredFinding,
    TelegramMessage,
    WhatsAppEdit,
    WhatsAppMessage,
    WhatsAppRevocation,
)
from backend.repositories.timeline_repo import TimelineRepository
from backend.services.audit_service import AuditService
from backend.services.integrity_service import ensure_integrity, LegacyUnverifiableError
from backend.services.log_service import get_log_service
from forensic.timeline import (
    PureTimelineBuilder,
    TimelineConfig,
    TimelineResult,
)


class TimelineService:
    """Service for timeline reconstruction operations."""

    def __init__(self, config: Optional[TimelineConfig] = None):
        self.timeline_repo = TimelineRepository()
        self.config = config or TimelineConfig()
        self.builder = PureTimelineBuilder(self.config)

    def build_timeline_for_case(self, db: Session, case_id: int) -> Dict[str, Any]:
        """
        Build and deterministically order timeline events for a case.
        
        Orchestration flow:
        1. Pre-stage integrity verification: calls ensure_integrity() for each evidence item (Rule R3).
        2. Retrieves parsed WhatsApp, Telegram, Recovered records, and Media items (load_only without BYTEA, R19).
        3. Invokes PureTimelineBuilder to generate canonical events, flags, total order, and timeline_hash.
        4. Replaces stored timeline events atomically (idempotent rebuild, Rule R11).
        5. Logs TIMELINE_BUILD into cryptographic hash-chained audit log (spec B5.5, Rule R3).
        """
        log_service = get_log_service(db)
        log_service.log_analysis(
            evidence_id=None,
            log_type="timeline_building_start",
            message="Starting timeline building for case",
            details={"case_id": case_id},
        )

        try:
            # 1. Query evidence records with deferred/excluded BYTEA (Rule R19)
            evidences = (
                db.query(Evidence)
                .options(load_only(
                    Evidence.id,
                    Evidence.case_id,
                    Evidence.sha256,
                    Evidence.original_filename,
                    Evidence.evidence_type,
                    Evidence.uploaded_at,
                ))
                .filter(Evidence.case_id == case_id)
                .all()
            )

            # Pre-stage integrity verification (Rule R3)
            for ev in evidences:
                try:
                    ensure_integrity(ev.id, db, action_context="timeline_stage")
                except LegacyUnverifiableError:
                    pass

            evidence_ids = [ev.id for ev in evidences]
            evidence_records = []
            ingest_time_map: Dict[str, int] = {}

            for ev in evidences:
                up_dt = ev.uploaded_at
                up_ms = (
                    int(up_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
                    if up_dt and up_dt.tzinfo
                    else (int(up_dt.timestamp() * 1000) if up_dt else 0)
                )
                evidence_records.append({
                    "evidence_id": ev.id,
                    "sha256": ev.sha256,
                    "original_filename": ev.original_filename,
                    "evidence_type": ev.evidence_type,
                    "uploaded_at_ms": up_ms,
                })
                if ev.sha256:
                    ingest_time_map[ev.sha256] = up_ms

            # Query derived artifacts (decrypted databases from exhibits)
            derived_artifacts = db.query(DerivedArtifact).filter(DerivedArtifact.case_id == case_id).all()
            derived_ids = [str(da.id) for da in derived_artifacts]

            from backend.services.whatsapp_service import whatsapp_service
            from backend.services.telegram_service import telegram_service

            # Ensure decrypted SQLite databases in DerivedArtifact are parsed
            for da in derived_artifacts:
                if da.artifact_type == "decrypted_sqlite":
                    has_msgs = db.query(WhatsAppMessage).filter(WhatsAppMessage.derived_artifact_id == str(da.id)).first()
                    if not has_msgs:
                        try:
                            whatsapp_service.parse_evidence_sync(
                                evidence_id=da.parent_evidence_id,
                                db=db,
                                derived_artifact_id=str(da.id),
                            )
                        except Exception:
                            pass

            # Ensure evidence items with missing WhatsApp/Telegram parsed messages are extracted
            ev_map = {ev.id: ev for ev in evidences}
            for eid in evidence_ids:
                ev_obj = ev_map.get(eid)
                fname = (ev_obj.original_filename or "").lower() if ev_obj else ""

                if "whatsapp" in fname or "wa" in fname:
                    has_wa = db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == eid).first()
                    if not has_wa:
                        try:
                            whatsapp_service.parse_evidence_sync(eid, db)
                        except Exception:
                            pass

                if "telegram" in fname or "tg" in fname:
                    has_tg = db.query(TelegramMessage).filter(TelegramMessage.evidence_id == eid).first()
                    if not has_tg:
                        try:
                            telegram_service.parse_evidence_sync(eid, db)
                        except Exception:
                            pass

            # 2. Query WhatsApp messages, revocations, and edits
            wa_cond = WhatsAppMessage.evidence_id.in_(evidence_ids) if evidence_ids else False
            if derived_ids:
                wa_cond = wa_cond | WhatsAppMessage.derived_artifact_id.in_(derived_ids)
            wa_messages = db.query(WhatsAppMessage).filter(wa_cond).all()

            wa_rev_cond = WhatsAppRevocation.evidence_id.in_(evidence_ids) if evidence_ids else False
            if derived_ids:
                wa_rev_cond = wa_rev_cond | WhatsAppRevocation.derived_artifact_id.in_(derived_ids)
            wa_revocations = db.query(WhatsAppRevocation).filter(wa_rev_cond).all()

            wa_edit_cond = WhatsAppEdit.evidence_id.in_(evidence_ids) if evidence_ids else False
            if derived_ids:
                wa_edit_cond = wa_edit_cond | WhatsAppEdit.derived_artifact_id.in_(derived_ids)
            wa_edits = db.query(WhatsAppEdit).filter(wa_edit_cond).all()

            # 3. Query Telegram messages
            tg_messages = []
            if evidence_ids:
                tg_messages = (
                    db.query(TelegramMessage)
                    .filter(TelegramMessage.evidence_id.in_(evidence_ids))
                    .all()
                )

            # 4. Query Recovered findings (B10)
            recovered_findings = (
                db.query(RecoveredFinding)
                .filter(RecoveredFinding.case_id == case_id)
                .all()
            )

            # 5. Query Media items with EXIF metadata
            media_items = (
                db.query(MediaItem)
                .filter(MediaItem.case_id == case_id)
                .all()
            )
            media_records = []
            for m in media_items:
                exif = m.exif_data or {}
                media_records.append({
                    "id": m.id,
                    "evidence_id": m.evidence_id,
                    "filename": m.file_path or f"media_{m.id}",
                    "sha256": m.sha256,
                    "date_time_original": exif.get("DateTimeOriginal") or exif.get("DateTime") or exif.get("date_time"),
                    "offset_time_original": exif.get("OffsetTimeOriginal"),
                    "gps_date_stamp": exif.get("GPSDateStamp"),
                    "gps_time_stamp": exif.get("GPSTimeStamp"),
                    "exif_type": exif.get("exif_type", "naive_dt"),
                    "gps_coords": exif.get("gps_coords"),
                })

            # 6. Assemble timeline via PureTimelineBuilder (Rule R18)
            result: TimelineResult = self.builder.build_timeline(
                evidence_records=evidence_records,
                whatsapp_messages=wa_messages,
                whatsapp_revocations=wa_revocations,
                whatsapp_edits=wa_edits,
                telegram_messages=tg_messages,
                recovered_records=recovered_findings,
                media_exif_records=media_records,
                ingest_time_map=ingest_time_map,
            )

            # 7. Replace timeline events for case in one transaction (Rule R11 idempotent rebuild)
            self.timeline_repo.delete_events_by_case_id(db, case_id)

            db_event_dicts = []
            for ev in result.events:
                norm_dt = None
                if ev.time.utc_ms is not None:
                    try:
                        norm_dt = datetime(1970, 1, 1) + timedelta(milliseconds=ev.time.utc_ms)
                    except (OverflowError, ValueError):
                        norm_dt = None

                primary_ev_id = ev.source_refs[0].evidence_id if ev.source_refs else None

                db_event_dicts.append({
                    "case_id": case_id,
                    "evidence_id": primary_ev_id,
                    "event_type": ev.kind,
                    "source_app": ev.app,
                    "timestamp": ev.time.utc_ms if ev.time.utc_ms is not None else 0,
                    "normalized_timestamp": norm_dt,
                    "entity_id": ev.actor_ref or ev.chat_ref or str(primary_ev_id or ""),
                    "entity_type": ev.kind,
                    "description": ev.summary,
                    "metadata_": ev.metadata,
                    # Additive forensic fields
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

            self.timeline_repo.save_events(db, db_event_dicts)

            # 8. Cryptographic hash-chained audit logging (spec B5.5, Rule R3)
            primary_evidence_id = evidence_ids[0] if evidence_ids else None
            AuditService.append(
                db=db,
                case_id=case_id,
                evidence_id=primary_evidence_id,
                action="TIMELINE_BUILD",
                details={
                    "case_id": case_id,
                    "events_created": len(result.events),
                    "timeline_hash": result.timeline_hash,
                    "unplaced_indicators_count": len(result.unplaced_indicators),
                },
            )

            log_service.log_analysis(
                evidence_id=None,
                log_type="timeline_building_completed",
                message="Timeline building completed successfully",
                details={
                    "case_id": case_id,
                    "events_created": len(result.events),
                    "timeline_hash": result.timeline_hash,
                },
            )

            return {
                "case_id": case_id,
                "events_created": len(result.events),
                "timeline_hash": result.timeline_hash,
                "unplaced_indicators": list(result.unplaced_indicators),
            }

        except Exception as e:
            db.rollback()
            log_service.log_error(
                error_type="timeline_building_error",
                message=f"Error during timeline building: {str(e)}",
                case_id=case_id,
                evidence_id=None,
                stack_trace=traceback.format_exc(),
                endpoint="/api/cases/{case_id}/timeline/build",
                method="POST",
            )
            raise

    def get_timeline_for_case(self, db: Session, case_id: int) -> List[dict]:
        """Get timeline events for a case, auto-building only if no events exist yet."""
        events = self.timeline_repo.get_events_by_case_id(db, case_id)
        if not events:
            self.build_timeline_for_case(db, case_id)
            events = self.timeline_repo.get_events_by_case_id(db, case_id)

        return [
            {
                "id": e.id,
                "case_id": e.case_id,
                "evidence_id": e.evidence_id,
                "event_type": e.event_type,
                "source_app": e.source_app,
                "timestamp": e.timestamp,
                "normalized_timestamp": e.normalized_timestamp.isoformat() if e.normalized_timestamp else None,
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "description": e.description,
                "metadata_": e.metadata_,
                # Additive forensic fields
                "event_id": e.event_id,
                "utc_ms": e.utc_ms,
                "time_unit": e.time_unit,
                "tz_basis": e.tz_basis,
                "time_flags": e.time_flags or [],
                "raw_timestamp": e.raw_timestamp,
                "actor_ref": e.actor_ref,
                "chat_ref": e.chat_ref,
                "summary": e.summary,
                "source_refs": e.source_refs or [],
                "confidence_score": e.confidence_score if e.confidence_score is not None else 1.0,
                "strength": e.strength or "deterministic",
                "limitations": e.limitations or [],
            }
            for e in events
        ]

    def filter_timeline(
        self,
        db: Session,
        case_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        source_app: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Filter timeline events for a case."""
        events = self.timeline_repo.filter_events(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            entity_type=entity_type,
            search=search,
        )
        if not events and not start_date and not end_date and not search:
            self.build_timeline_for_case(db, case_id)
            events = self.timeline_repo.filter_events(
                db,
                case_id=case_id,
                start_date=start_date,
                end_date=end_date,
                event_type=event_type,
                source_app=source_app,
                entity_type=entity_type,
                search=search,
            )

        return [
            {
                "id": e.id,
                "case_id": e.case_id,
                "evidence_id": e.evidence_id,
                "event_type": e.event_type,
                "source_app": e.source_app,
                "timestamp": e.timestamp,
                "normalized_timestamp": e.normalized_timestamp.isoformat() if e.normalized_timestamp else None,
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "description": e.description,
                "metadata_": e.metadata_,
                # Additive forensic fields
                "event_id": e.event_id,
                "utc_ms": e.utc_ms,
                "time_unit": e.time_unit,
                "tz_basis": e.tz_basis,
                "time_flags": e.time_flags or [],
                "raw_timestamp": e.raw_timestamp,
                "actor_ref": e.actor_ref,
                "chat_ref": e.chat_ref,
                "summary": e.summary,
                "source_refs": e.source_refs or [],
                "confidence_score": e.confidence_score if e.confidence_score is not None else 1.0,
                "strength": e.strength or "deterministic",
                "limitations": e.limitations or [],
            }
            for e in events
        ]

    def get_histogram(
        self,
        db: Session,
        case_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        source_app: Optional[str] = None,
        search: Optional[str] = None,
        interval: str = "day",
    ) -> dict:
        """Get histogram data for a case."""
        events = self.timeline_repo.get_events_by_case_id(db, case_id)
        if not events:
            self.build_timeline_for_case(db, case_id)

        return self.timeline_repo.get_histogram_data(
            db,
            case_id=case_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            source_app=source_app,
            search=search,
            interval=interval,
        )


timeline_service = TimelineService()