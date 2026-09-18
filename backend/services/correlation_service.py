"""Correlation service for forensic evidence and deep cross-platform correlation."""

import re
import traceback
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session

from backend.repositories.correlation_repo import CorrelationRepository
from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.repositories.media_repo import MediaRepository
from backend.models.models import Evidence, EvidenceFile, MediaItem as ORMMediaItem, PersonEntity, CorrelationFinding
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
from forensic.correlation.handover import PlatformHandoverDetector
from forensic.correlation.media_hash import PerceptualMediaCorrelator, compute_dhash, compute_phash
from forensic.correlation.artifacts import ArtifactStitcher, ExtractedArtifact
from forensic.correlation.rendezvous import SpatiotemporalRendezvousDetector, LocationObservation
from backend.services.log_service import get_log_service


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

            if evidence.evidence_type != "demo" and not wa_messages and not tg_messages:
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

        # Demo auto-alignment if applicable
        if any(e.evidence_type == "demo" for e in evidences):
            from datetime import datetime, timezone, timedelta
            import random
            from backend.models.models import WhatsAppMessage as ORMWhatsAppMessage, TelegramMessage as ORMTelegramMessage
            from backend.api.demo import REALISTIC_EXCHANGES

            base_time = datetime.now(timezone.utc) - timedelta(days=3)
            demo_ev_ids = [e.id for e in evidences if e.evidence_type == "demo"]
            wa_db_msgs = db.query(ORMWhatsAppMessage).filter(ORMWhatsAppMessage.evidence_id.in_(demo_ev_ids)).order_by(ORMWhatsAppMessage.id).all()
            tg_db_msgs = db.query(ORMTelegramMessage).filter(ORMTelegramMessage.evidence_id.in_(demo_ev_ids)).order_by(ORMTelegramMessage.id).all()

            if wa_db_msgs and tg_db_msgs:
                min_count = min(len(wa_db_msgs), len(tg_db_msgs))
                for idx in range(min_count):
                    pair = REALISTIC_EXCHANGES[idx % len(REALISTIC_EXCHANGES)]
                    slot_time = base_time + timedelta(minutes=idx * 20)
                    wa_sec = int(slot_time.timestamp())
                    tg_sec = int((slot_time + timedelta(seconds=random.randint(15, 45))).timestamp())

                    wa_db_msgs[idx].body = pair["wa"]
                    wa_db_msgs[idx].timestamp = wa_sec
                    tg_db_msgs[idx].body = pair["tg"]
                    tg_db_msgs[idx].timestamp = tg_sec

                db.commit()

                all_wa_messages = [WhatsAppMessage(
                    evidence_id=m.evidence_id, message_id=m.message_id, key_remote_jid=m.key_remote_jid,
                    sender_jid=m.sender_jid, participant_jid=m.participant_jid, body=m.body,
                    timestamp=m.timestamp, media_type=m.media_type, media_path=m.media_path,
                    message_type=m.message_type, status=m.status
                ) for m in wa_db_msgs]

                all_tg_messages = [TelegramMessage(
                    evidence_id=m.evidence_id, message_id=m.message_id, dialog_id=m.dialog_id,
                    sender_id=m.sender_id, body=m.body, timestamp=m.timestamp,
                    media_type=m.media_type, media_path=m.media_path, message_type=m.message_type
                ) for m in tg_db_msgs]

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

    def run_deep_correlation(self, db: Session, case_id: int, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute full R4 Deep Cross-Platform Correlation Engine:
        1. Multi-modal entity resolution (Person clusters, Phone, Handles).
        2. Cross-platform sequence handovers (configurable threshold).
        3. Perceptual media correlation (dHash / pHash, configurable Hamming threshold).
        4. Deterministic artifact stitching (Crypto, Banking, Logistics, Custom Codewords).
        5. Spatiotemporal rendezvous detection (EXIF GPS & shared location events).
        """
        params = parameters or {}
        handover_threshold = int(params.get("handover_threshold_seconds", 180))
        media_hamming_thresh = int(params.get("media_hamming_distance", 4))
        rendezvous_dist_meters = float(params.get("rendezvous_distance_meters", 50.0))
        rendezvous_time_sec = int(params.get("rendezvous_time_seconds", 1800))
        custom_keywords = params.get("custom_keywords", [])

        log_service = get_log_service(db)
        log_service.log_analysis(
            evidence_id=None,
            log_type="deep_correlation_start",
            message="Starting R4 Deep Correlation Engine",
            details={"case_id": case_id, "parameters": params}
        )

        # Clear prior findings and person entities for this case
        self.correlation_repo.delete_findings_by_case_id(db, case_id)
        self.correlation_repo.delete_person_entities_by_case_id(db, case_id)
        self.correlation_repo.delete_edges_by_case_id(db, case_id)

        wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items = self._collect_case_data(db, case_id)

        # 1. Identity Resolution Engine
        identity_engine = IdentityResolutionEngine()
        resolution_result = identity_engine.resolve(wa_cnts, tg_cnts, wa_msgs, tg_msgs)
        resolved_persons = resolution_result.get("persons", [])
        resolved_edges = resolution_result.get("edges", [])
        ambiguous_candidates = resolution_result.get("ambiguous_candidates", [])

        # Persist Person Entities
        self.correlation_repo.save_person_entities(db, case_id, resolved_persons)

        # 2. Platform Handover Detector
        handover_detector = PlatformHandoverDetector(default_threshold_seconds=handover_threshold)
        handover_candidates = handover_detector.detect_handovers(
            wa_msgs, tg_msgs, threshold_seconds=handover_threshold
        )
        handover_findings = []
        for cand in handover_candidates:
            handover_findings.append({
                "finding_uuid": cand.handover_id,
                "finding_type": "handover",
                "sub_type": f"{cand.from_platform}->{cand.to_platform}",
                "confidence_score": cand.confidence_score,
                "details": cand.to_dict(),
                "evidence_ids": [cand.from_platform, cand.to_platform],
                "limitations": cand.limitations,
                "provenance": cand.provenance,
            })
        self.correlation_repo.save_correlation_findings(db, case_id, handover_findings)

        # 3. Perceptual Media Hashing
        # Retrieve media records from ORM
        orm_media = db.query(ORMMediaItem).filter(ORMMediaItem.case_id == case_id).all()
        case_ev_ids = [e.id for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()]
        orm_files = db.query(EvidenceFile).filter(
            EvidenceFile.evidence_id.in_(case_ev_ids),
            EvidenceFile.is_media == True
        ).all() if case_ev_ids else []

        media_records = []
        for m in orm_media:
            exif = m.exif_data or {}
            dhash = exif.get("dhash")
            phash = exif.get("phash")
            # If dhash or phash not stored, check if content_bytes available
            if not dhash or not phash:
                # check file
                ef = db.query(EvidenceFile).filter(EvidenceFile.sha256 == m.sha256).first()
                if ef and ef.content_bytes:
                    try:
                        dhash = compute_dhash(ef.content_bytes)
                        phash = compute_phash(ef.content_bytes)
                        exif["dhash"] = dhash
                        exif["phash"] = phash
                        m.exif_data = exif
                    except Exception:
                        pass

            media_records.append({
                "id": m.id,
                "file_name": m.file_path.split("/")[-1].split("\\")[-1] if m.file_path else f"media_{m.id}",
                "sha256": m.sha256 or "",
                "dhash": dhash or exif.get("dhash"),
                "phash": phash or exif.get("phash"),
                "exif_data": exif,
            })

        # Pairwise perceptual comparison
        media_correlator = PerceptualMediaCorrelator(default_threshold=media_hamming_thresh)
        media_matches = media_correlator.correlate_items(media_records, threshold=media_hamming_thresh)

        media_findings = []
        for match in media_matches:
            media_findings.append({
                "finding_uuid": match["match_id"],
                "finding_type": "media_match",
                "sub_type": "perceptual_hash",
                "confidence_score": match["confidence_score"],
                "details": match,
                "evidence_ids": [match.get("source_media_id"), match.get("target_media_id")],
                "limitations": match["limitations"],
                "provenance": match["provenance"],
            })
        self.correlation_repo.save_correlation_findings(db, case_id, media_findings)

        # 4. Deterministic Artifact Stitching
        artifact_stitcher = ArtifactStitcher(custom_keywords=custom_keywords)
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

        artifact_findings = []
        for art in extracted_artifacts:
            artifact_findings.append({
                "finding_uuid": art.artifact_id,
                "finding_type": "shared_artifact",
                "sub_type": art.artifact_type,
                "confidence_score": art.confidence_score,
                "details": art.to_dict(),
                "evidence_ids": [art.evidence_id] if art.evidence_id else [],
                "limitations": art.limitations,
                "provenance": art.provenance,
            })
        self.correlation_repo.save_correlation_findings(db, case_id, artifact_findings)

        # 5. Spatiotemporal Rendezvous
        location_obs: List[LocationObservation] = []
        # Extract from Media EXIF
        for m in orm_media:
            exif = m.exif_data or {}
            lat = exif.get("GPSLatitude") or exif.get("latitude")
            lon = exif.get("GPSLongitude") or exif.get("longitude")
            if lat is not None and lon is not None:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    ts = exif.get("timestamp") or exif.get("DateTimeOriginal")
                    ts_val = None
                    if isinstance(ts, (int, float)):
                        ts_val = int(ts)
                    location_obs.append(LocationObservation(
                        observation_id=f"loc_media_{m.id}",
                        source_type="media_exif",
                        source_id=str(m.id),
                        platform="media",
                        latitude=f_lat,
                        longitude=f_lon,
                        timestamp=ts_val,
                        evidence_id=m.evidence_id,
                        label=m.file_path,
                    ))
                except (ValueError, TypeError):
                    pass

        # Extract from messages with coordinates
        coord_pattern = r"([-+]?\d{1,2}\.\d+)[,\s]+([-+]?\d{1,3}\.\d+)"
        for msg in wa_msgs:
            if msg.body:
                m_coord = re.search(coord_pattern, msg.body)
                if m_coord:
                    try:
                        location_obs.append(LocationObservation(
                            observation_id=f"loc_wa_{msg.message_id}",
                            source_type="wa_location",
                            source_id=str(msg.message_id),
                            platform="whatsapp",
                            latitude=float(m_coord.group(1)),
                            longitude=float(m_coord.group(2)),
                            timestamp=msg.timestamp // 1000 if msg.timestamp and msg.timestamp > 10_000_000_000 else msg.timestamp,
                            evidence_id=msg.evidence_id,
                            sender_id=msg.sender_jid,
                            label="Shared WhatsApp Coordinate",
                        ))
                    except (ValueError, TypeError):
                        pass

        for msg in tg_msgs:
            if msg.body:
                m_coord = re.search(coord_pattern, msg.body)
                if m_coord:
                    try:
                        location_obs.append(LocationObservation(
                            observation_id=f"loc_tg_{msg.message_id}",
                            source_type="tg_location",
                            source_id=str(msg.message_id),
                            platform="telegram",
                            latitude=float(m_coord.group(1)),
                            longitude=float(m_coord.group(2)),
                            timestamp=msg.timestamp // 1000 if msg.timestamp and msg.timestamp > 10_000_000_000 else msg.timestamp,
                            evidence_id=msg.evidence_id,
                            sender_id=str(msg.sender_id),
                            label="Shared Telegram Coordinate",
                        ))
                    except (ValueError, TypeError):
                        pass

        rendezvous_detector = SpatiotemporalRendezvousDetector(
            default_distance_threshold_meters=rendezvous_dist_meters,
            default_time_threshold_seconds=rendezvous_time_sec,
        )
        rendezvous_candidates = rendezvous_detector.detect_rendezvous(
            location_obs,
            distance_threshold_meters=rendezvous_dist_meters,
            time_threshold_seconds=rendezvous_time_sec,
        )

        rendezvous_findings = []
        for rc in rendezvous_candidates:
            rendezvous_findings.append({
                "finding_uuid": rc.rendezvous_id,
                "finding_type": "rendezvous",
                "sub_type": "spatiotemporal_cooccurrence",
                "confidence_score": rc.confidence_score,
                "details": rc.to_dict(),
                "evidence_ids": [rc.observation_a.evidence_id, rc.observation_b.evidence_id],
                "limitations": rc.limitations,
                "provenance": rc.provenance,
            })
        self.correlation_repo.save_correlation_findings(db, case_id, rendezvous_findings)

        # 6. Save combined edges into correlation_edges
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

        # Also add baseline cross-app message / contact edges
        baseline_edges = correlate_all(wa_msgs, wa_cnts, tg_msgs, tg_cnts, media_items, time_window_seconds=300)
        for be in baseline_edges:
            be["case_id"] = case_id
            all_db_edges.append(be)

        self.correlation_repo.save_edges(db, all_db_edges)
        db.commit()

        log_service.log_analysis(
            evidence_id=None,
            log_type="deep_correlation_completed",
            message="R4 Deep Correlation Engine completed successfully",
            details={
                "case_id": case_id,
                "persons_resolved": len(resolved_persons),
                "handovers_detected": len(handover_candidates),
                "media_matches": len(media_matches),
                "artifacts_extracted": len(extracted_artifacts),
                "rendezvous_detected": len(rendezvous_candidates),
            }
        )

        return {
            "status": "SUCCEEDED",
            "case_id": case_id,
            "persons_count": len(resolved_persons),
            "edges_count": len(all_db_edges),
            "handovers_count": len(handover_candidates),
            "media_matches_count": len(media_matches),
            "artifacts_count": len(extracted_artifacts),
            "rendezvous_count": len(rendezvous_candidates),
            "ambiguous_candidates_count": len(ambiguous_candidates),
            "parameters": {
                "handover_threshold_seconds": handover_threshold,
                "media_hamming_distance": media_hamming_thresh,
                "rendezvous_distance_meters": rendezvous_dist_meters,
                "rendezvous_time_seconds": rendezvous_time_sec,
                "custom_keywords": custom_keywords,
            }
        }

    def get_deep_graph(self, db: Session, case_id: int) -> Dict[str, Any]:
        """
        Generate a stable court-ready JSON graph of nodes and edges for visual forensic analysis:
        {
          "nodes": [...],
          "edges": [...],
          "metadata": {...}
        }
        """
        persons = self.correlation_repo.get_person_entities_by_case_id(db, case_id)
        edges = self.correlation_repo.get_edges_by_case_id(db, case_id)
        findings = self.correlation_repo.get_findings_by_type(db, case_id)

        nodes_dict: Dict[str, Dict[str, Any]] = {}

        # 1. Person nodes
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

            # Account sub-nodes
            for acc in p.attributes.get("resolved_accounts", []):
                acc_id = f"acc_{acc.get('platform')}_{acc.get('account_id')}"
                if acc_id not in nodes_dict:
                    nodes_dict[acc_id] = {
                        "id": acc_id,
                        "label": acc.get("display_name") or acc.get("account_id"),
                        "type": f"{acc.get('platform', 'unknown').upper()}_ACCOUNT",
                        "properties": acc,
                    }

        # 2. Add edges
        graph_edges = []
        for e in edges:
            meta = e.metadata_ or {}
            # Ensure source and target nodes exist in graph
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
                "algorithm_version": "1.0.0",
                "case_id": case_id,
                "node_count": len(nodes_dict),
                "edge_count": len(graph_edges),
                "finding_count": len(findings),
            }
        }

    def get_platform_handovers(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """Get detected cross-platform handovers."""
        findings = self.correlation_repo.get_findings_by_type(db, case_id, finding_type="handover")
        return [f.details for f in findings if f.details]

    def get_media_correlations(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """Get perceptual media matches."""
        findings = self.correlation_repo.get_findings_by_type(db, case_id, finding_type="media_match")
        return [f.details for f in findings if f.details]

    def get_shared_artifacts(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """Get extracted and shared deterministic artifacts."""
        findings = self.correlation_repo.get_findings_by_type(db, case_id, finding_type="shared_artifact")
        return [f.details for f in findings if f.details]

    def get_rendezvous_events(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """Get spatiotemporal rendezvous candidates."""
        findings = self.correlation_repo.get_findings_by_type(db, case_id, finding_type="rendezvous")
        return [f.details for f in findings if f.details]

    def get_resolved_persons(self, db: Session, case_id: int) -> List[Dict[str, Any]]:
        """Get resolved person entity clusters."""
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
        """Get correlation edges for a case as dictionaries."""
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
        """Get resolved cross-app entity contact mappings for a case (backwards compatible)."""
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
                "confidence_score": meta.get("confidence_score", meta.get("strength_score", 1.0)),
                "match_reason": meta.get("match_reason", meta.get("method", "Contact Match")),
                "wa_name": meta.get("wa_name", edge.source_id),
                "tg_name": meta.get("tg_name", edge.target_id),
                "tg_username": meta.get("tg_username", ""),
                "is_ambiguous": meta.get("is_ambiguous", False),
            })

        resolutions.sort(key=lambda x: x["confidence_score"], reverse=True)
        return resolutions

    def get_cross_app_message_matrix(self, db: Session, case_id: int, window_seconds: int = 300) -> List[dict]:
        """Get correlated cross-app message exchanges within the specified time window threshold."""
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
        """Accurately inspect evidence records, files, and parsed tables to determine WhatsApp and Telegram presence."""
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

        for e in evidences:
            app = ((e.metadata_ or {}).get("app") or "").lower()
            fn = (e.original_filename or "").lower()
            sp = (e.storage_path or "").lower()

            if app == "whatsapp" or "whatsapp" in fn or "wa_demo" in sp or "msgstore" in fn or "wa.db" in sp:
                has_whatsapp = True
            if app == "telegram" or "telegram" in fn or "tg_demo" in sp or "cache4" in fn or "tg.db" in sp or "userconf" in fn:
                has_telegram = True

            files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == e.id).all()
            for f in files:
                rp = (f.file_path or "").lower()
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