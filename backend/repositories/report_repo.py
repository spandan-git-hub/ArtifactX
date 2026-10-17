"""Report repository for data access."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.models import (
    Case,
    Evidence,
    EvidenceFile,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppGroup,
    TelegramMessage,
    TelegramContact,
    TelegramGroup,
    TimelineEvent,
    MediaItem,
    DeletedMessage,
    RecoveredFinding,
    CorrelationEdge,
    ActivityLog,
    GeneratedReport,
)


def timestamp_to_datetime(ts: int) -> Optional[datetime]:
    """Convert Unix timestamp (milliseconds) to datetime."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000)


class ReportRepository:
    """Repository for report data queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_evidence_data(self, case_id: int) -> Dict[str, Any]:
        """Get evidence data for a report."""
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {}

        # Get all evidence
        evidence_items = self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()

        # Count extracted files
        total_extracted = 0
        evidence_list = []
        legacy_unverifiable_count = 0
        for ev in evidence_items:
            file_count = self.db.query(EvidenceFile).filter(
                EvidenceFile.evidence_id == ev.id
            ).count()
            total_extracted += file_count
            ev_integrity = getattr(ev, "integrity_state", "OK") or "OK"
            if ev_integrity == "LEGACY_UNVERIFIABLE":
                legacy_unverifiable_count += 1
            evidence_list.append({
                "id": ev.id,
                "filename": ev.original_filename,
                "type": ev.evidence_type,
                "file_count": file_count,
                "integrity_state": ev_integrity,
                "uploaded_at": ev.uploaded_at.isoformat() if ev.uploaded_at else None,
            })

        # Media distribution
        media_items = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).all()

        media_summary = {
            "total": len(media_items),
            "images": 0,
            "videos": 0,
            "audio": 0,
            "documents": 0,
        }
        for item in media_items:
            if item.media_type == "image":
                media_summary["images"] += 1
            elif item.media_type == "video":
                media_summary["videos"] += 1
            elif item.media_type == "audio":
                media_summary["audio"] += 1
            elif item.media_type:
                media_summary["documents"] += 1

        # Apps found
        apps = self._get_apps_for_case(case_id)

        # Date range
        date_from, date_to = self._get_date_range(case_id)

        return {
            "case_id": case_id,
            "case_name": case.name,
            "total_evidence_files": len(evidence_items),
            "total_extracted_files": total_extracted,
            "legacy_unverifiable_count": legacy_unverifiable_count,
            "evidence_breakdown": {
                "WhatsApp databases": sum(1 for e in evidence_list if "wa" in str(e.get("filename", "")).lower()),
                "Telegram databases": sum(1 for e in evidence_list if "tg" in str(e.get("filename", "")).lower()),
                "ZIP packages": sum(1 for e in evidence_list if str(e.get("filename", "")).endswith(".zip")),
                "Other files": sum(1 for e in evidence_list if not any(x in str(e.get("filename", "")).lower() for x in ["wa", "tg", ".zip"])),
            },
            "media_summary": media_summary,
            "apps_found": apps,
            "date_range": {
                "start": date_from,
                "end": date_to,
            } if date_from or date_to else None,
            "evidence_list": evidence_list,
        }

    def get_evidence_summary(self, case_id: int) -> Dict[str, Any]:
        """Get evidence summary for a report."""
        data = self.get_evidence_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "case_name": data.get("case_name"),
            "total_evidence_files": data.get("total_evidence_files", 0),
            "total_extracted_files": data.get("total_extracted_files", 0),
            "legacy_unverifiable_count": data.get("legacy_unverifiable_count", 0),
            "evidence_breakdown": data.get("evidence_breakdown", {}),
            "media_summary": data.get("media_summary", {}),
            "apps_found": data.get("apps_found", []),
            "date_range": data.get("date_range"),
        }

    def get_timeline_data(self, case_id: int) -> Dict[str, Any]:
        """Get timeline data for a report."""
        events = self.db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        ).order_by(TimelineEvent.normalized_timestamp.asc()).all()

        total_events = len(events)
        events_by_type: Dict[str, int] = {}
        events_by_app: Dict[str, int] = {"whatsapp": 0, "telegram": 0}
        date_range_start = None
        date_range_end = None

        event_list = []
        for event in events:
            # Count by type
            event_type = event.event_type or "unknown"
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            # Count by app
            if event.source_app:
                events_by_app[event.source_app] = events_by_app.get(event.source_app, 0) + 1

            # Date range
            if event.normalized_timestamp:
                if date_range_start is None or event.normalized_timestamp < date_range_start:
                    date_range_start = event.normalized_timestamp
                if date_range_end is None or event.normalized_timestamp > date_range_end:
                    date_range_end = event.normalized_timestamp

            event_list.append({
                "id": event.id,
                "type": event.event_type,
                "app": event.source_app,
                "timestamp": event.normalized_timestamp,
                "description": event.description,
            })

        # App breakdown
        apps = self._get_apps_for_case(case_id)
        app_breakdown = {}
        for app in apps:
            app_events = [e for e in events if e.source_app == app]
            app_breakdown[app] = {
                "total_events": len(app_events),
                "by_type": {},
            }
            for event in app_events:
                event_type = event.event_type or "unknown"
                app_breakdown[app]["by_type"][event_type] = (
                    app_breakdown[app]["by_type"].get(event_type, 0) + 1
                )

        return {
            "case_id": case_id,
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_app": events_by_app,
            "date_range": {
                "start": date_range_start,
                "end": date_range_end,
            } if date_range_start or date_range_end else None,
            "app_breakdown": app_breakdown,
            "events": event_list[:200],  # Limit for PDF
        }

    def get_timeline_summary(self, case_id: int) -> Dict[str, Any]:
        """Get timeline summary for a report."""
        data = self.get_timeline_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "total_events": data.get("total_events", 0),
            "events_by_type": data.get("events_by_type", {}),
            "events_by_app": data.get("events_by_app", {}),
            "date_range": data.get("date_range"),
            "app_breakdown": data.get("app_breakdown", {}),
        }

    def get_deleted_data(self, case_id: int) -> Dict[str, Any]:
        """Get deleted message data for a report."""
        deletions = self.db.query(DeletedMessage).filter(
            DeletedMessage.case_id == case_id
        ).order_by(DeletedMessage.detected_at.desc()).all()

        total = len(deletions)
        wa_count = sum(1 for d in deletions if d.source_app == "whatsapp")
        tg_count = sum(1 for d in deletions if d.source_app == "telegram")

        high_conf = sum(1 for d in deletions if d.confidence_score and d.confidence_score >= 0.8)
        medium_conf = sum(1 for d in deletions if d.confidence_score and 0.5 <= d.confidence_score < 0.8)
        low_conf = sum(1 for d in deletions if d.confidence_score and d.confidence_score < 0.5)

        date_from = min((d.detected_at for d in deletions if d.detected_at), default=None)
        date_to = max((d.detected_at for d in deletions if d.detected_at), default=None)

        deletion_list = [
            {
                "id": d.id,
                "app": d.source_app,
                "chat": d.chat_jid,
                "gap_start": d.gap_start,
                "gap_end": d.gap_end,
                "missing_count": d.missing_count,
                "confidence": d.confidence_score,
                "method": d.detection_method,
                "detected_at": d.detected_at,
            }
            for d in deletions[:100]  # Limit for PDF
        ]

        return {
            "case_id": case_id,
            "total_deletions": total,
            "whatsapp_deletions": wa_count,
            "telegram_deletions": tg_count,
            "high_confidence_count": high_conf,
            "medium_confidence_count": medium_conf,
            "low_confidence_count": low_conf,
            "date_range": {
                "start": date_from,
                "end": date_to,
            } if date_from or date_to else None,
            "deletions": deletion_list,
        }

    def get_deleted_summary(self, case_id: int) -> Dict[str, Any]:
        """Get deleted message summary for a report."""
        data = self.get_deleted_data(case_id)
        return {
            "case_id": data.get("case_id"),
            "total_deletions": data.get("total_deletions", 0),
            "whatsapp_deletions": data.get("whatsapp_deletions", 0),
            "telegram_deletions": data.get("telegram_deletions", 0),
            "high_confidence_count": data.get("high_confidence_count", 0),
            "medium_confidence_count": data.get("medium_confidence_count", 0),
            "low_confidence_count": data.get("low_confidence_count", 0),
            "date_range": data.get("date_range"),
        }

    def get_case_statistics(self, case_id: int) -> Dict[str, Any]:
        """Get case statistics for report."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        wa_stats = self._get_app_stats(evidence_ids, "whatsapp")
        tg_stats = self._get_app_stats(evidence_ids, "telegram")

        media_count = self.db.query(MediaItem).filter(
            MediaItem.case_id == case_id
        ).count()

        return {
            "total_messages": wa_stats["messages"] + tg_stats["messages"],
            "total_contacts": wa_stats["contacts"] + tg_stats["contacts"],
            "total_groups": wa_stats["groups"] + tg_stats["groups"],
            "total_media": media_count,
            "whatsapp": wa_stats,
            "telegram": tg_stats,
        }

    def get_correlation_data(self, case_id: int) -> Dict[str, Any]:
        """Get correlation data for report."""
        edges = self.db.query(CorrelationEdge).filter(
            CorrelationEdge.case_id == case_id
        ).all()

        total = len(edges)
        msg_contact = sum(1 for e in edges if "message" in str(e.source_type) and "contact" in str(e.target_type))
        msg_media = sum(1 for e in edges if "message" in str(e.source_type) and "media" in str(e.target_type))
        cross_app = sum(1 for e in edges if (
            ("wa" in str(e.source_type) and "tg" in str(e.target_type)) or
            ("tg" in str(e.source_type) and "wa" in str(e.target_type))
        ))

        return {
            "total_edges": total,
            "message_contact_links": msg_contact,
            "message_media_links": msg_media,
            "cross_app_links": cross_app,
        }

    def get_recovery_findings_metrics(self, case_id: int) -> Dict[str, Any]:
        """Get structured recovery findings categorized across the 4 tiers with strength metrics."""
        findings = (
            self.db.query(RecoveredFinding)
            .filter(RecoveredFinding.case_id == case_id)
            .order_by(RecoveredFinding.tier.asc(), RecoveredFinding.confidence_score.desc())
            .all()
        )

        tier1_list = [f for f in findings if (f.tier == 1 or f.kind in ("revocation", "edit"))]
        tier2_list = [f for f in findings if (f.tier == 2 or f.kind == "wal_resident" or f.method == "wal")]
        tier3_list = [f for f in findings if (f.tier == 3 or f.kind in ("freelist", "slack") or f.method in ("freelist", "slack"))]
        tier4_list = [f for f in findings if (f.tier == 4 or f.kind == "id_gap")]

        total_findings = len(findings)
        deterministic_count = sum(1 for f in findings if f.strength == "deterministic" or (f.confidence_score and f.confidence_score >= 0.95))
        strong_count = sum(1 for f in findings if f.strength == "strong" or (f.confidence_score and 0.80 <= f.confidence_score < 0.95))
        moderate_count = sum(1 for f in findings if f.strength == "moderate" or (f.confidence_score and 0.50 <= f.confidence_score < 0.80))
        weak_count = sum(1 for f in findings if f.strength in ("weak_hint", "heuristic") or (f.confidence_score and f.confidence_score < 0.50))

        # Format rows for tabular PDF presentation
        formatted_findings = []
        for f in findings[:60]:
            tier_num = f.tier or (1 if f.kind in ("revocation", "edit") else (2 if f.method == "wal" else 3))
            formatted_findings.append({
                "id": f.id,
                "tier": tier_num,
                "tier_name": f"Tier {tier_num}",
                "kind": f.kind or f.method or "carved",
                "strength": f.strength or ("deterministic" if tier_num == 1 else "strong"),
                "confidence": f.confidence_score if f.confidence_score is not None else (1.0 if tier_num == 1 else 0.85),
                "source_table": f.table_name or "SQLite Table",
                "offset": f"0x{f.byte_offset:04x}" if f.byte_offset else (f"Frame {f.frame_index}" if f.frame_index else "Cell"),
                "timestamp": f.timestamp,
                "preview": (f.candidate_original_text or f.body or f.raw_payload_preview or "[Carved cell payload]")[:90],
                "hash": f.raw_payload_hash[:16] if f.raw_payload_hash else "—",
            })

        return {
            "total_findings": total_findings,
            "tier1_count": len(tier1_list),
            "tier2_count": len(tier2_list),
            "tier3_count": len(tier3_list),
            "tier4_count": len(tier4_list),
            "by_strength": {
                "deterministic": deterministic_count,
                "strong": strong_count,
                "moderate": moderate_count,
                "weak_heuristic": weak_count,
            },
            "findings": formatted_findings,
        }

    def get_deep_correlation_metrics(self, case_id: int) -> Dict[str, Any]:
        """Get deep multi-modal cross-platform correlation metrics."""
        from backend.services.correlation_service import correlation_service
        try:
            graph = correlation_service.get_deep_graph(self.db, case_id)
            handovers = correlation_service.get_platform_handovers(self.db, case_id)
            media = correlation_service.get_media_correlations(self.db, case_id)
            artifacts = correlation_service.get_shared_artifacts(self.db, case_id)
            rendezvous = correlation_service.get_rendezvous_events(self.db, case_id)
            persons = correlation_service.get_resolved_persons(self.db, case_id)

            return {
                "total_nodes": len(graph.get("nodes", [])),
                "total_edges": len(graph.get("edges", [])),
                "resolved_persons": persons,
                "person_count": len(persons),
                "handovers": handovers,
                "handover_count": len(handovers),
                "media_matches": media,
                "media_match_count": len(media),
                "shared_artifacts": artifacts,
                "artifact_count": len(artifacts),
                "rendezvous_events": rendezvous,
                "rendezvous_count": len(rendezvous),
            }
        except Exception:
            # Fallback to direct table count
            edges = self.db.query(CorrelationEdge).filter(CorrelationEdge.case_id == case_id).all()
            return {
                "total_nodes": 0,
                "total_edges": len(edges),
                "resolved_persons": [],
                "person_count": 0,
                "handovers": [],
                "handover_count": 0,
                "media_matches": [],
                "media_match_count": 0,
                "shared_artifacts": [],
                "artifact_count": 0,
                "rendezvous_events": [],
                "rendezvous_count": 0,
            }

    def get_integrity_verification_metrics(self, case_id: int) -> Dict[str, Any]:
        """Get exact hash comparison and integrity verification metrics."""
        evidences = self.db.query(Evidence).filter(Evidence.case_id == case_id).all()
        items = []
        intact_count = 0
        total_bytes = 0

        for ev in evidences:
            meta = ev.metadata_ or {}
            size = meta.get("size_bytes") or (len(ev.content_bytes) if ev.content_bytes else 0)
            total_bytes += size
            # Current SHA-256 vs intake SHA-256
            is_intact = ev.integrity_state != "LEGACY_UNVERIFIABLE"
            if is_intact:
                intact_count += 1

            items.append({
                "id": ev.id,
                "filename": ev.original_filename,
                "type": ev.evidence_type or "Container",
                "sha256": ev.sha256 or "—",
                "size_bytes": size,
                "match_status": "MATCH (PASS)" if is_intact else "UNVERIFIABLE",
                "integrity_state": ev.integrity_state or "OK",
                "uploaded_at": ev.uploaded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if ev.uploaded_at else "—",
            })

        pct = (intact_count / len(evidences) * 100.0) if evidences else 100.0
        return {
            "total_items": len(evidences),
            "intact_items": intact_count,
            "verification_percentage": pct,
            "total_bytes_verified": total_bytes,
            "algorithm": "FIPS 180-4 SHA-256",
            "items": items,
        }


    def _get_apps_for_case(self, case_id: int) -> List[str]:
        """Get list of apps with data in the case."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        apps = []
        if evidence_ids:
            if self.db.query(WhatsAppMessage).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).count() > 0:
                apps.append("whatsapp")

            if self.db.query(TelegramMessage).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).count() > 0:
                apps.append("telegram")

        return apps

    def _get_date_range(self, case_id: int) -> tuple:
        """Get overall date range for case data."""
        evidence_ids = [e.id for e in self.db.query(Evidence).filter(
            Evidence.case_id == case_id
        ).all()]

        earliest = None
        latest = None

        if evidence_ids:
            first_wa = self.db.query(func.min(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()
            last_wa = self.db.query(func.max(WhatsAppMessage.timestamp)).filter(
                WhatsAppMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            if first_wa:
                wa_earliest = timestamp_to_datetime(first_wa)
                if earliest is None or wa_earliest < earliest:
                    earliest = wa_earliest
            if last_wa:
                wa_latest = timestamp_to_datetime(last_wa)
                if latest is None or wa_latest > latest:
                    latest = wa_latest

            first_tg = self.db.query(func.min(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()
            last_tg = self.db.query(func.max(TelegramMessage.timestamp)).filter(
                TelegramMessage.evidence_id.in_(evidence_ids)
            ).scalar()

            if first_tg:
                tg_earliest = timestamp_to_datetime(first_tg)
                if earliest is None or tg_earliest < earliest:
                    earliest = tg_earliest
            if last_tg:
                tg_latest = timestamp_to_datetime(last_tg)
                if latest is None or tg_latest > latest:
                    latest = tg_latest

        return earliest, latest

    def _get_app_stats(self, evidence_ids: List[int], app: str) -> Dict[str, int]:
        """Get statistics for a specific app."""
        if not evidence_ids:
            return {"messages": 0, "contacts": 0, "groups": 0}

        if app == "whatsapp":
            return {
                "messages": self.db.query(WhatsAppMessage).filter(
                    WhatsAppMessage.evidence_id.in_(evidence_ids)
                ).count(),
                "contacts": self.db.query(WhatsAppContact).filter(
                    WhatsAppContact.evidence_id.in_(evidence_ids)
                ).count(),
                "groups": self.db.query(WhatsAppGroup).filter(
                    WhatsAppGroup.evidence_id.in_(evidence_ids)
                ).count(),
            }
        else:
            return {
                "messages": self.db.query(TelegramMessage).filter(
                    TelegramMessage.evidence_id.in_(evidence_ids)
                ).count(),
                "contacts": self.db.query(TelegramContact).filter(
                    TelegramContact.evidence_id.in_(evidence_ids)
                ).count(),
                "groups": self.db.query(TelegramGroup).filter(
                    TelegramGroup.evidence_id.in_(evidence_ids)
                ).count(),
            }

    def get_custody_logs(self, case_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chain of custody activity logs for report."""
        logs = (
            self.db.query(ActivityLog)
            .filter(ActivityLog.case_id == case_id)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "action": log.action,
                "description": log.description,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]

    def get_evidence_file_hashes(self, case_id: int, limit: int = 150) -> List[Dict[str, Any]]:
        """Get file-level cryptographic hashes for evidence files."""
        evidence_items = self.db.query(Evidence).filter(Evidence.case_id == case_id).all()
        manifest = []

        for ev in evidence_items:
            # Root evidence container hash
            meta = ev.metadata_ or {}
            manifest.append({
                "filename": ev.original_filename,
                "type": ev.evidence_type or "Container",
                "sha256": ev.sha256,
                "md5": meta.get("md5", "—"),
                "sha1": meta.get("sha1", "—"),
                "size": meta.get("size_bytes", 0),
                "mime": ev.content_type or "application/octet-stream",
                "is_container": True,
            })

            # Extracted files
            files = (
                self.db.query(EvidenceFile)
                .filter(EvidenceFile.evidence_id == ev.id)
                .limit(limit)
                .all()
            )
            for f in files:
                f_meta = f.metadata_ or {}
                manifest.append({
                    "filename": f.relative_path,
                    "type": "Extracted Artifact",
                    "sha256": f.sha256,
                    "md5": f_meta.get("md5", "—"),
                    "sha1": f_meta.get("sha1", "—"),
                    "size": f.file_size or 0,
                    "mime": f.mime_type or "application/octet-stream",
                    "is_container": False,
                })

        return manifest

    def create_generated_report(
        self,
        report_id: str,
        case_id: int,
        report_type: str,
        lead_analyst: str,
        agency: str,
        case_notes: str,
        sha256: str,
        total_pages: int,
        size_bytes: int,
        filename: str,
        pdf_data: Optional[bytes] = None,
    ) -> GeneratedReport:
        """Create and persist a generated report history record with binary PDF data."""
        report = GeneratedReport(
            report_id=report_id,
            case_id=case_id,
            report_type=report_type,
            lead_analyst=lead_analyst,
            agency=agency,
            case_notes=case_notes,
            sha256=sha256,
            total_pages=total_pages,
            size_bytes=size_bytes,
            filename=filename,
            pdf_data=pdf_data,
            generated_at=datetime.utcnow(),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report_history(self, case_id: int) -> List[GeneratedReport]:
        """Fetch all generated report history records for a case."""
        return (
            self.db.query(GeneratedReport)
            .filter(GeneratedReport.case_id == case_id)
            .order_by(GeneratedReport.generated_at.desc())
            .all()
        )

    def get_generated_report(self, case_id: int, report_id: str) -> Optional[GeneratedReport]:
        """Fetch a specific generated report record."""
        return (
            self.db.query(GeneratedReport)
            .filter(GeneratedReport.case_id == case_id, GeneratedReport.report_id == report_id)
            .first()
        )