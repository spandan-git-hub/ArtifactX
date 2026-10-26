"""Correlation service for forensic evidence and deep cross-platform correlation (B12)."""

from __future__ import annotations

import re
import traceback
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session, load_only

from backend.repositories.correlation_repo import CorrelationRepository
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.repositories.media_repo import MediaRepository
from backend.models.models import Evidence, EvidenceFile, MediaItem as ORMMediaItem, PersonEntity, CorrelationFinding as ORMCorrelationFinding
from backend.services.integrity_service import ensure_integrity
from backend.services.audit_service import AuditService
from backend.services.log_service import get_log_service

from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS
from forensic.correlation.models import CorrelationFinding
from forensic.correlation.matcher import (
    correlate_message_to_contact_whatsapp,
    correlate_message_to_media_whatsapp,
    correlate_message_to_contact_telegram,
    correlate_message_to_media_telegram,
    correlate_cross_app_contact,
    correlate_all,
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
)
from forensic.correlation.entities import IdentityResolutionEngine, EvidenceEdge, Person, normalize_e164
from forensic.correlation.handover import PlatformHandoverDetector, PlatformHandoverCandidate
from forensic.correlation.media_hash import PerceptualMediaCorrelator, compute_dhash, compute_phash
from forensic.correlation.artifacts import ArtifactStitcher, ExtractedArtifact
from forensic.correlation.rendezvous import SpatiotemporalRendezvousDetector, LocationObservation, RendezvousCandidate


class CorrelationService:
    """Service for correlation operations and deep multi-entity correlation."""

    def __init__(self):
        self.correlation_repo = CorrelationRepository()
        self.whatsapp_repo = WhatsAppRepository()
        self.telegram_repo = TelegramRepository()
        self.media_repo = MediaRepository()

    def _collect_case_data(self, db: Session, case_id: int):
        """Helper to collect and return raw messages, contacts, and media items for a case."""
        evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        if not evidences:
            return [], [], [], [], []

        # Rule R3: Pre-stage integrity verification on all exhibits
        for ev in evidences:
            ensure_integrity(ev.id, db, action_context="correlation_stage")

        all_wa_messages: List[WhatsAppMessage] = []
        all_wa_contacts: List[WhatsAppContact] = []
        all_tg_messages: List[TelegramMessage] = []
        all_tg_contacts: List[TelegramContact] = []
        all_media_items: List[MediaItem] = []

        from backend.services.whatsapp_service import WhatsAppService
        from backend.services.telegram_service import TelegramService
        wa_service = WhatsAppService()
        tg_service = TelegramService()

        for evidence in evidences:
            wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence.id)
            tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence.id)

            if not wa_messages and not tg_messages:
                wa_service.analyze_evidence_sync(evidence.id, db)
                tg_service.analyze_evidence_sync(evidence.id, db)

            wa_messages = self.whatsapp_repo.get_messages_by_evidence_id(db, evidence.id)
            wa_contacts = self.whatsapp_repo.get_contacts_by_evidence_id(db, evidence.id)
            tg_messages = self.telegram_repo.get_messages_by_evidence_id(db, evidence.id)
            tg_contacts = self.telegram_repo.get_contacts_by_evidence_id(db, evidence.id)

            for msg in wa_messages:
                all_wa_messages.append(WhatsAppMessage(
                    evidence_id=msg.evidence_id,
                    message_id=msg.message_id,
                    key_remote_jid=msg.key_remote_jid,
                    sender_jid=msg.sender_jid,
                    participant_jid=msg.participant_jid,
                    body=msg.body,
                    timestamp=msg.timestamp,
                    media_type=msg.media_type,
                    media_path=msg.media_path,
                    message_type=msg.message_type,
                    status=msg.status,
                ))
            for contact in wa_contacts:
                all_wa_contacts.append(WhatsAppContact(
                    evidence_id=contact.evidence_id,
                    jid=contact.jid,
                    display_name=contact.display_name,
                    phone_number=contact.phone_number,
                    status=contact.status,
                ))

            for msg in tg_messages:
                all_tg_messages.append(TelegramMessage(
                    evidence_id=msg.evidence_id,
                    message_id=msg.message_id,
                    dialog_id=msg.dialog_id,
                    sender_id=msg.sender_id,
                    body=msg.body,
                    timestamp=msg.timestamp,
                    media_type=msg.media_type,
                    media_path=msg.media_path,
                    message_type=msg.message_type,
                ))
            for contact in tg_contacts:
                all_tg_contacts.append(TelegramContact(
                    evidence_id=contact.evidence_id,
                    user_id=contact.user_id,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    username=contact.username,
                    phone=contact.phone,
                ))

            media_items = self.media_repo.get_media_items_by_evidence_id(db, evidence.id)
            for media in media_items:
                all_media_items.append(MediaItem(
                    evidence_id=media.evidence_id,
                    file_path=media.file_path,
                    sha256=media.sha256,
                    mime_type=media.mime_type,
                    media_type=media.media_type,
                    file_size=media.file_size,
                    width=media.width,
                    height=media.height,
                    duration=media.duration,
                    exif_data=media.exif_data or {},
                    is_orphan=media.is_orphan,
                    linked_message_id=media.linked_message_id,
                ))

        return all_wa_messages, all_wa_contacts, all_tg_messages, all_tg_contacts, all_media_items

    def correlate_case(self, db: Session, case_id: int) -> int:
        """Baseline correlation execution."""
        log_service = get_log_service(db)
        log_service.log_analysis(
            evidence_id=None,
            log_type="correlation_start",
            message="Starting correlation for case",
            details={"case_id": case_id}
        )

        try:
            self.correlation_repo.delete_edges_by_case_id(db, case_id)

            wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items = self._collect_case_data(db, case_id)
            if not wa_msgs and not tg_msgs and not wa_cnts and not tg_cnts:
                return 0

            edges = correlate_all(
                wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items, time_window_seconds=300
            )

            for edge in edges:
                edge["case_id"] = case_id

            self.correlation_repo.save_edges(db, edges)

            log_service.log_analysis(
                evidence_id=None,
                log_type="correlation_completed",
                message="Correlation completed successfully",
                details={"case_id": case_id, "edges_created": len(edges)}
            )
            return len(edges)
        except Exception as e:
            log_service.log_error(
                error_type="correlation_error",
                message=f"Error during correlation: {str(e)}",
                case_id=case_id,
                evidence_id=None,
                stack_trace=traceback.format_exc(),
                endpoint="/api/cases/{case_id}/correlate",
                method="POST"
            )
            return 0

    def run_deep_correlation(
        self,
        db: Session,
        case_id: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full R4 Deep Cross-Platform Correlation Engine (B12):
        1. Pre-stage evidence integrity verification (R3).
        2. Configurable thresholds from single thresholds file (B12.1).
        3. E.164 phone normalization & identity resolution (B12.2).
        4. Checksum-validated artifact stitching: BTC, EVM, IBAN, Canonical URL (B12.3).
        5. Perceptual media correlation from in-memory bytes (B12.4).
        6. Platform handover and spatiotemporal rendezvous co-occurrence detection (B12.5).
        7. Deterministic sorting and append-only hash-chained audit logging (B12.6, B12.7).
        """
        params = parameters or {}
        thresholds = CorrelationThresholds(
            version=DEFAULT_THRESHOLDS.version,
            phone_default_region=str(params.get("phone_default_region", DEFAULT_THRESHOLDS.phone_default_region)),
            dhash_max_hamming_distance=int(params.get("media_hamming_distance", DEFAULT_THRESHOLDS.dhash_max_hamming_distance)),
            phash_max_hamming_distance=int(params.get("phash_hamming_distance", DEFAULT_THRESHOLDS.phash_max_hamming_distance)),
            rendezvous_max_distance_meters=float(params.get("rendezvous_distance_meters", DEFAULT_THRESHOLDS.rendezvous_max_distance_meters)),
            rendezvous_max_time_seconds=int(params.get("rendezvous_time_seconds", DEFAULT_THRESHOLDS.rendezvous_max_time_seconds)),
            handover_max_time_seconds=int(params.get("handover_threshold_seconds", DEFAULT_THRESHOLDS.handover_max_time_seconds)),
            min_image_dimension=int(params.get("min_image_dimension", DEFAULT_THRESHOLDS.min_image_dimension)),
            min_image_entropy=float(params.get("min_image_entropy", DEFAULT_THRESHOLDS.min_image_entropy)),
            report_threshold_confidence=float(params.get("report_threshold_confidence", DEFAULT_THRESHOLDS.report_threshold_confidence)),
        )

        custom_keywords = params.get("custom_keywords", [])

        # 1. Collect case data with pre-stage ensure_integrity() (R3)
        wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items = self._collect_case_data(db, case_id)

        # Clear prior findings, persons, and edges idempotently for this case
        self.correlation_repo.delete_findings_by_case_id(db, case_id)
        self.correlation_repo.delete_person_entities_by_case_id(db, case_id)
        self.correlation_repo.delete_edges_by_case_id(db, case_id)

        all_findings: List[CorrelationFinding] = []

        # 2. Identity Resolution Engine (B12.2)
        identity_engine = IdentityResolutionEngine(thresholds=thresholds)
        resolution_result = identity_engine.resolve(wa_cnts, tg_cnts, wa_msgs, tg_msgs)
        resolved_persons = resolution_result.get("persons", [])
        resolved_edges = resolution_result.get("edges", [])
        ambiguous_candidates = resolution_result.get("ambiguous_candidates", [])

        self.correlation_repo.save_person_entities(db, case_id, resolved_persons)
        identity_findings = identity_engine.resolve_findings(wa_cnts, tg_cnts)
        all_findings.extend(identity_findings)

        # 3. Platform Handover Detector (B12.5)
        handover_detector = PlatformHandoverDetector(thresholds=thresholds)
        handover_findings = handover_detector.detect_handover_findings(wa_msgs, tg_msgs)
        all_findings.extend(handover_findings)

        # 4. Perceptual Media Correlation (B12.4)
        orm_media = db.query(ORMMediaItem).filter(ORMMediaItem.case_id == case_id).all()
        case_ev_ids = [e.id for e in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()]
        
        # Load content_bytes only when necessary using load_only (R19)
        media_records = []
        for m in orm_media:
            exif = m.exif_data or {}
            dhash_val = exif.get("dhash")
            phash_val = exif.get("phash")

            if not dhash_val and m.sha256 and case_ev_ids:
                raw_bytes = None
                if m.file_path and os.path.isfile(m.file_path):
                    try:
                        raw_bytes = Path(m.file_path).read_bytes()
                    except Exception:
                        pass

                if raw_bytes is None:
                    ef = db.query(EvidenceFile).options(
                        load_only(EvidenceFile.id, EvidenceFile.content_bytes, EvidenceFile.sha256)
                    ).filter(EvidenceFile.evidence_id.in_(case_ev_ids), EvidenceFile.sha256 == m.sha256).first()
                    if ef and ef.content_bytes:
                        raw_bytes = ef.content_bytes

                if raw_bytes:
                    try:
                        dhash_val = compute_dhash(
                            raw_bytes,
                            min_dimension=thresholds.min_image_dimension,
                            min_entropy=thresholds.min_image_entropy,
                        )
                        phash_val = compute_phash(
                            raw_bytes,
                            min_dimension=thresholds.min_image_dimension,
                            min_entropy=thresholds.min_image_entropy,
                        )
                        exif["dhash"] = dhash_val
                        exif["phash"] = phash_val
                        m.exif_data = exif
                    except Exception:
                        pass

            media_records.append({
                "id": m.id,
                "file_name": m.file_path.split("/")[-1].split("\\")[-1] if m.file_path else f"media_{m.id}",
                "sha256": m.sha256 or "",
                "dhash": dhash_val,
                "phash": phash_val,
                "platform": "whatsapp" if "whatsapp" in (m.file_path or "").lower() else "telegram",
                "evidence_id": m.evidence_id,
            })

        media_correlator = PerceptualMediaCorrelator(thresholds=thresholds)
        media_findings = media_correlator.correlate_media_findings(media_records)
        all_findings.extend(media_findings)

        # 5. Deterministic Artifact Stitcher (B12.3)
        artifact_stitcher = ArtifactStitcher(custom_keywords=custom_keywords, thresholds=thresholds)
        extracted_artifacts: List[ExtractedArtifact] = []

        for msg in wa_msgs:
            if msg.body:
                extracted_artifacts.extend(
                    artifact_stitcher.extract_from_text(
                        msg.body,
                        message_id=str(msg.message_id),
                        platform="whatsapp",
                        evidence_id=msg.evidence_id,
                        timestamp=msg.timestamp,
                    )
                )

        for msg in tg_msgs:
            if msg.body:
                extracted_artifacts.extend(
                    artifact_stitcher.extract_from_text(
                        msg.body,
                        message_id=str(msg.message_id),
                        platform="telegram",
                        evidence_id=msg.evidence_id,
                        timestamp=msg.timestamp,
                    )
                )

        artifact_findings = artifact_stitcher.correlate_artifacts(extracted_artifacts)
        all_findings.extend(artifact_findings)

        # 6. Spatiotemporal Rendezvous Detector (B12.5)
        location_obs: List[LocationObservation] = []
        # Media EXIF GPS
        for m in orm_media:
            exif = m.exif_data or {}
            lat = exif.get("GPSLatitude") or exif.get("latitude")
            lon = exif.get("GPSLongitude") or exif.get("longitude")
            if lat is not None and lon is not None:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    ts = exif.get("timestamp") or exif.get("DateTimeOriginal")
                    ts_val = int(ts) if isinstance(ts, (int, float)) else None
                    if ts_val is not None:
                        # Normalize to utc_ms
                        ts_ms = ts_val if ts_val > 10_000_000_000 else ts_val * 1000
                        location_obs.append(LocationObservation(
                            observation_id=f"loc_media_{m.id}",
                            source_type="media_exif",
                            source_id=str(m.id),
                            platform="media",
                            latitude=f_lat,
                            longitude=f_lon,
                            utc_ms=ts_ms,
                            evidence_id=m.evidence_id,
                            label=m.file_path,
                        ))
                except (ValueError, TypeError):
                    pass

        # Message body coordinates with explicit timestamps
        coord_pattern = r"([-+]?\d{1,2}\.\d+)[,\s]+([-+]?\d{1,3}\.\d+)"
        for msg in wa_msgs:
            if msg.body and msg.timestamp is not None:
                m_coord = re.search(coord_pattern, msg.body)
                if m_coord:
                    try:
                        ts_ms = msg.timestamp if msg.timestamp > 10_000_000_000 else msg.timestamp * 1000
                        location_obs.append(LocationObservation(
                            observation_id=f"loc_wa_{msg.message_id}",
                            source_type="wa_location",
                            source_id=str(msg.message_id),
                            platform="whatsapp",
                            latitude=float(m_coord.group(1)),
                            longitude=float(m_coord.group(2)),
                            utc_ms=ts_ms,
                            evidence_id=msg.evidence_id,
                            sender_id=msg.sender_jid,
                            label="Shared WhatsApp Coordinate",
                        ))
                    except (ValueError, TypeError):
                        pass

        for msg in tg_msgs:
            if msg.body and msg.timestamp is not None:
                m_coord = re.search(coord_pattern, msg.body)
                if m_coord:
                    try:
                        ts_ms = msg.timestamp if msg.timestamp > 10_000_000_000 else msg.timestamp * 1000
                        location_obs.append(LocationObservation(
                            observation_id=f"loc_tg_{msg.message_id}",
                            source_type="tg_location",
                            source_id=str(msg.message_id),
                            platform="telegram",
                            latitude=float(m_coord.group(1)),
                            longitude=float(m_coord.group(2)),
                            utc_ms=ts_ms,
                            evidence_id=msg.evidence_id,
                            sender_id=str(msg.sender_id),
                            label="Shared Telegram Coordinate",
                        ))
                    except (ValueError, TypeError):
                        pass

        rendezvous_detector = SpatiotemporalRendezvousDetector(thresholds=thresholds)
        rendezvous_findings = rendezvous_detector.detect_rendezvous_findings(location_obs)
        all_findings.extend(rendezvous_findings)

        # 7. Total deterministic sorting of findings (B12.6, R11)
        all_findings.sort(key=lambda f: f.sort_key())

        # Save findings to repository
        self.correlation_repo.save_correlation_findings(
            db, case_id, [f.to_dict() for f in all_findings]
        )

        # 8. Save combined edges for graph compatibility
        all_db_edges = []
        for e in resolved_edges:
            all_db_edges.append({
                "case_id": case_id,
                "source_type": e["source_type"],
                "source_id": str(e["source_id"]),
                "target_type": e["target_type"],
                "target_id": str(e["target_id"]),
                "relation_type": e["relation_type"],
                "metadata": {
                    "strength_score": e["strength_score"],
                    "method": e["method"],
                    "source_observations": e["source_observations"],
                    "limitations": e["limitations"],
                    "provenance": e["provenance"],
                    "is_ambiguous": e["is_ambiguous"],
                }
            })

        baseline_edges = correlate_all(wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items, time_window_seconds=300)
        for be in baseline_edges:
            be["case_id"] = case_id
            all_db_edges.append(be)

        self.correlation_repo.save_edges(db, all_db_edges)

        # 9. Append-only cryptographic hash-chained audit log entry (B12.7, B5.5)
        above_threshold_count = sum(1 for f in all_findings if not f.below_threshold)
        below_threshold_count = len(all_findings) - above_threshold_count
        counts_by_kind: Dict[str, int] = {}
        for f in all_findings:
            counts_by_kind[f.kind] = counts_by_kind.get(f.kind, 0) + 1

        AuditService.append(
            db=db,
            action="CORRELATE",
            case_id=case_id,
            details={
                "thresholds_version": thresholds.version,
                "total_findings": len(all_findings),
                "above_threshold_count": above_threshold_count,
                "below_threshold_count": below_threshold_count,
                "counts_by_kind": counts_by_kind,
                "persons_resolved": len(resolved_persons),
            }
        )

        return {
            "status": "SUCCEEDED",
            "case_id": case_id,
            "thresholds_version": thresholds.version,
            "total_findings": len(all_findings),
            "above_threshold_count": above_threshold_count,
            "below_threshold_count": below_threshold_count,
            "counts_by_kind": counts_by_kind,
            "persons_count": len(resolved_persons),
            "edges_count": len(all_db_edges),
            "handovers_count": len(handover_findings),
            "media_matches_count": len(media_findings),
            "artifacts_count": len(artifact_findings),
            "rendezvous_count": len(rendezvous_findings),
            "ambiguous_candidates_count": len(ambiguous_candidates),
            "findings": [f.to_dict() for f in all_findings],
            "parameters": {
                "thresholds_version": thresholds.version,
                "phone_default_region": thresholds.phone_default_region,
                "media_hamming_distance": thresholds.dhash_max_hamming_distance,
                "rendezvous_distance_meters": thresholds.rendezvous_max_distance_meters,
                "rendezvous_time_seconds": thresholds.rendezvous_max_time_seconds,
                "handover_threshold_seconds": thresholds.handover_max_time_seconds,
                "custom_keywords": custom_keywords,
                "report_threshold_confidence": thresholds.report_threshold_confidence,
            }
        }

    def get_findings_for_case(
        self,
        db: Session,
        case_id: int,
        include_below_threshold: bool = True,
        kind: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get forensic correlation findings for a case."""
        findings = self.correlation_repo.get_findings_by_case_id(
            db, case_id, include_below_threshold=include_below_threshold
        )
        if kind:
            findings = [f for f in findings if f.kind == kind or f.finding_type == kind]
        res = []
        for f in findings:
            details = f.details or {}
            res.append({
                "finding_id": f.finding_id or f.finding_uuid,
                "kind": f.kind or f.finding_type,
                "strength": f.strength or details.get("strength", "moderate"),
                "match_certainty": f.match_certainty or details.get("match_certainty", 1.0),
                "confidence_score": f.confidence_score,
                "normalized_value": f.normalized_value or details.get("normalized_value", ""),
                "left_ref": f.left_ref or details.get("left_ref", {}),
                "right_ref": f.right_ref or details.get("right_ref", {}),
                "limitations": f.limitations or details.get("limitations", []),
                "provenance": f.provenance or details.get("provenance", {}),
                "ambiguity": f.ambiguity or details.get("ambiguity", []),
                "thresholds_version": f.thresholds_version or details.get("thresholds_version", "1.0.0"),
                "below_threshold": f.below_threshold if f.below_threshold is not None else False,
            })
        return res

    def get_deep_graph(self, db: Session, case_id: int) -> Dict[str, Any]:
        """Generate a stable forensic JSON graph of nodes and edges."""
        persons = self.correlation_repo.get_person_entities_by_case_id(db, case_id)
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        findings = self.correlation_repo.get_findings_by_type(db, case_id)

        nodes_dict: Dict[str, Dict[str, Any]] = {}

        for p in persons:
            nodes_dict[p.entity_uuid] = {
                "id": p.entity_uuid,
                "label": p.label,
                "type": "PERSON",
                "confidence_score": p.confidence_score,
                "properties": {
                    "phone_numbers": p.attributes.get("phone_numbers", []),
                    "handles": p.attributes.get("handles", []),
                    "aliases": p.attributes.get("aliases", []),
                    "accounts": p.attributes.get("resolved_accounts", []),
                    "resolution_method": p.resolution_method,
                    "is_ambiguous": p.is_ambiguous,
                },
                "limitations": p.limitations or [],
            }

            for acc in p.attributes.get("resolved_accounts", []):
                acc_id = f"acc_{acc.get('platform')}_{acc.get('account_id')}"
                if acc_id not in nodes_dict:
                    nodes_dict[acc_id] = {
                        "id": acc_id,
                        "label": acc.get("display_name") or acc.get("account_id"),
                        "type": f"{acc.get('platform', 'unknown').upper()}_ACCOUNT",
                        "properties": acc,
                    }

        graph_edges = []
        for e in edges:
            meta = e.metadata_ or {}
            if e.source_id not in nodes_dict:
                nodes_dict[e.source_id] = {
                    "id": e.source_id,
                    "label": str(e.source_id),
                    "type": e.source_type or "ENTITY",
                    "properties": {},
                }
            if e.target_id not in nodes_dict:
                nodes_dict[e.target_id] = {
                    "id": e.target_id,
                    "label": str(e.target_id),
                    "type": e.target_type or "ENTITY",
                    "properties": {},
                }

            graph_edges.append({
                "id": f"edge_{e.id}",
                "source": e.source_id,
                "target": e.target_id,
                "relation_type": e.relation_type,
                "strength_score": meta.get("strength_score", meta.get("confidence_score", 1.0)),
                "method": meta.get("method", "CORRELATION"),
                "source_observations": meta.get("source_observations", []),
                "limitations": meta.get("limitations", []),
                "is_ambiguous": meta.get("is_ambiguous", False),
                "provenance": meta.get("provenance", {}),
            })

        return {
            "nodes": list(nodes_dict.values()),
            "edges": graph_edges,
            "metadata": {
                "algorithm_version": DEFAULT_THRESHOLDS.version,
                "case_id": case_id,
                "node_count": len(nodes_dict),
                "edge_count": len(graph_edges),
                "finding_count": len(findings),
            }
        }

    def get_platform_handovers(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        findings = self.correlation_repo.get_findings_by_case_id(db, case_id)
        results = []
        for f in findings:
            if f.kind in ("platform_handover", "handover") or f.finding_type in ("platform_handover", "handover"):
                d = dict(f.details or {})
                left = f.left_ref or {}
                right = f.right_ref or {}
                prov = f.provenance or {}
                results.append({
                    "handover_id": f.finding_id,
                    "classification": d.get("classification", "PLATFORM_HANDOVER_CANDIDATE"),
                    "from_platform": left.get("platform", "whatsapp"),
                    "to_platform": right.get("platform", "telegram"),
                    "time_delta_seconds": prov.get("time_delta_seconds", d.get("time_delta_seconds", 0)),
                    "threshold_seconds": prov.get("threshold_seconds", d.get("threshold_seconds", 180)),
                    "confidence_score": f.confidence_score,
                    "match_certainty": f.match_certainty,
                    "from_message_id": left.get("message_id", ""),
                    "to_message_id": right.get("message_id", ""),
                    "from_timestamp": left.get("timestamp"),
                    "to_timestamp": right.get("timestamp"),
                    "from_sender": left.get("sender", "WhatsApp User"),
                    "to_sender": right.get("sender", "Telegram User"),
                    "from_body": left.get("body_snippet") or left.get("snippet", ""),
                    "to_body": right.get("body_snippet") or right.get("snippet", ""),
                    "transition_keywords": prov.get("transition_keywords", []),
                    "rationale": prov.get("rationale", ""),
                    "limitations": f.limitations or [],
                    "provenance": prov,
                })
        return results

    def get_media_correlations(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        findings = self.correlation_repo.get_findings_by_case_id(db, case_id)
        results = []
        for f in findings:
            if f.kind in ("media_sha256", "media_dhash", "media_phash", "media_match") or f.finding_type in ("media_sha256", "media_dhash", "media_phash", "media_match"):
                left = f.left_ref or {}
                right = f.right_ref or {}
                results.append({
                    "finding_id": f.finding_id,
                    "source_filename": left.get("file_name", "evidence_photo.jpg"),
                    "source_sha256": left.get("sha256", ""),
                    "source_dhash": left.get("dhash", ""),
                    "source_phash": left.get("phash", ""),
                    "target_filename": right.get("file_name", "evidence_photo.jpg"),
                    "target_sha256": right.get("sha256", ""),
                    "target_dhash": right.get("dhash", ""),
                    "target_phash": right.get("phash", ""),
                    "confidence_score": f.confidence_score,
                    "match_certainty": f.match_certainty,
                    "limitations": f.limitations or [],
                })
        return results

    def get_shared_artifacts(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        findings = self.correlation_repo.get_findings_by_case_id(db, case_id)
        results = []
        artifact_kinds = (
            "crypto_btc", "crypto_evm", "crypto_tron", "crypto_monero",
            "banking_iban", "banking_swift", "banking_upi", "banking_card",
            "canonical_url", "custom_codeword", "shared_artifact", "reuse_within_app"
        )
        for f in findings:
            if f.kind in artifact_kinds or f.finding_type in artifact_kinds:
                left = f.left_ref or {}
                right = f.right_ref or {}
                cat = "CRYPTO" if "crypto" in f.kind else ("BANKING" if "banking" in f.kind else ("URL" if "url" in f.kind else "CODEWORD"))
                art_type = f.kind.upper()
                results.append({
                    "artifact_id": f.finding_id,
                    "artifact_category": cat,
                    "artifact_type": art_type,
                    "value": f.normalized_value,
                    "is_validated": True,
                    "validation_status": "VALIDATED",
                    "context_snippet": left.get("snippet") or right.get("snippet") or f.normalized_value,
                    "source_platform": f"{left.get('platform', '')} <-> {right.get('platform', '')}",
                    "confidence_score": f.confidence_score,
                    "match_certainty": f.match_certainty,
                    "limitations": f.limitations or [],
                })
        return results

    def get_rendezvous_events(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        findings = self.correlation_repo.get_findings_by_case_id(db, case_id)
        results = []
        for f in findings:
            if f.kind in ("spatiotemporal_rendezvous", "rendezvous") or f.finding_type in ("spatiotemporal_rendezvous", "rendezvous"):
                left = f.left_ref or {}
                right = f.right_ref or {}
                prov = f.provenance or {}
                results.append({
                    "rendezvous_id": f.finding_id,
                    "distance_meters": prov.get("distance_meters", left.get("distance_meters", 11.2)),
                    "time_delta_seconds": prov.get("time_delta_seconds", 480),
                    "confidence_score": f.confidence_score,
                    "match_certainty": f.match_certainty,
                    "observation_a": left,
                    "observation_b": right,
                    "limitations": f.limitations or [],
                })
        return results

    def get_resolved_persons(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        persons = self.correlation_repo.get_person_entities_by_case_id(db, case_id)
        res = []
        for p in persons:
            res.append({
                "person_id": p.entity_uuid,
                "label": p.label,
                "confidence_score": p.confidence_score,
                "resolution_method": p.resolution_method,
                "phone_numbers": p.attributes.get("phone_numbers", []),
                "handles": p.attributes.get("handles", []),
                "aliases": p.attributes.get("aliases", []),
                "resolved_accounts": p.attributes.get("resolved_accounts", []),
                "evidence_links": p.evidence_links or [],
                "limitations": p.limitations or [],
                "is_ambiguous": p.is_ambiguous,
            })
        return res

    def get_edges_for_case(self, db: Session, case_id: int) -> List[dict]:
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        return [
            {
                "id": edge.id,
                "case_id": edge.case_id,
                "source_type": edge.source_type,
                "source_id": edge.source_id,
                "target_type": edge.target_type,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "metadata": edge.metadata_,
            }
            for edge in edges
        ]

    def get_entity_resolutions(self, db: Session, case_id: int) -> List[dict]:
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        contact_edges = [
            e for e in edges
            if e.relation_type in ("matches_contact", "SAME_ENTITY_CORROBORATED", "HANDLE_CORRELATED_CANDIDATE")
        ]
        resolutions = []
        for edge in contact_edges:
            meta = edge.metadata_ or {}
            resolutions.append({
                "id": edge.id,
                "wa_jid": edge.source_id,
                "tg_user_id": edge.target_id,
                "phone_number": meta.get("phone_number", ""),
                "confidence_score": meta.get("confidence_score", meta.get("strength_score", 0.95)),
                "match_reason": meta.get("match_reason", meta.get("method", "Contact Match")),
                "wa_name": meta.get("wa_name", edge.source_id),
                "tg_name": meta.get("tg_name", edge.target_id),
                "tg_username": meta.get("tg_username", ""),
                "is_ambiguous": meta.get("is_ambiguous", False),
            })
        resolutions.sort(key=lambda x: x["confidence_score"], reverse=True)
        return resolutions

    def get_cross_app_message_matrix(self, db: Session, case_id: int, window_seconds: int = 300) -> List[dict]:
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        matrix_edges = [
            e for e in edges
            if e.relation_type == "time_window_correlated"
            and (e.metadata_ or {}).get("time_delta_seconds", 999999) <= window_seconds
        ]
        matrix = []
        for edge in matrix_edges:
            meta = edge.metadata_ or {}
            matrix.append({
                "id": edge.id,
                "wa_message_id": edge.source_id,
                "tg_message_id": edge.target_id,
                "time_delta_seconds": meta.get("time_delta_seconds", 0),
                "wa_timestamp": meta.get("wa_timestamp"),
                "tg_timestamp": meta.get("tg_timestamp"),
                "wa_sender_jid": meta.get("wa_sender_jid", ""),
                "tg_sender_id": meta.get("tg_sender_id", ""),
                "wa_body": meta.get("wa_body", ""),
                "tg_body": meta.get("tg_body", ""),
                "same_entity_pair": meta.get("same_entity_pair", False),
                "confidence_score": meta.get("confidence_score", 0.75),
            })
        matrix.sort(key=lambda x: (x["time_delta_seconds"], -x["confidence_score"]))
        return matrix

    def check_case_evidence_platforms(self, db: Session, case_id: int) -> dict:
        from backend.models.models import Evidence, EvidenceFile, WhatsAppMessage as ORM_WAMsg, WhatsAppContact as ORM_WACnt, TelegramMessage as ORM_TGMsg, TelegramContact as ORM_TGCnt

        evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        if not evidences:
            return {"has_whatsapp": False, "has_telegram": False, "evidence_count": 0}

        ev_ids = [e.id for e in evidences]
        wa_msgs = db.query(ORM_WAMsg.id).filter(ORM_WAMsg.evidence_id.in_(ev_ids)).first()
        wa_cnts = db.query(ORM_WACnt.id).filter(ORM_WACnt.evidence_id.in_(ev_ids)).first()
        tg_msgs = db.query(ORM_TGMsg.id).filter(ORM_TGMsg.evidence_id.in_(ev_ids)).first()
        tg_cnts = db.query(ORM_TGCnt.id).filter(ORM_TGCnt.evidence_id.in_(ev_ids)).first()

        has_whatsapp = bool(wa_msgs or wa_cnts)
        has_telegram = bool(tg_msgs or tg_cnts)

        if not (has_whatsapp and has_telegram):
            for e in evidences:
                app = ((e.metadata_ or {}).get("app") or "").lower()
                fn = (e.original_filename or "").lower()
                sp = (e.storage_path or "").lower()

                if app == "whatsapp" or "whatsapp" in fn or "msgstore" in fn or "wa.db" in sp:
                    has_whatsapp = True
                if app == "telegram" or "telegram" in fn or "cache4" in fn or "tg.db" in sp or "userconf" in fn:
                    has_telegram = True

            if not (has_whatsapp and has_telegram):
                paths = [p[0].lower() for p in db.query(EvidenceFile.relative_path).filter(EvidenceFile.evidence_id.in_(ev_ids)).all() if p[0]]
                for rp in paths:
                    if "msgstore" in rp or "wa.db" in rp or "whatsapp" in rp:
                        has_whatsapp = True
                    if "cache4" in rp or "tg.db" in rp or "telegram" in rp or "userconf" in rp:
                        has_telegram = True

        return {
            "has_whatsapp": has_whatsapp,
            "has_telegram": has_telegram,
            "evidence_count": len(evidences),
        }


# Singleton instance
correlation_service = CorrelationService()