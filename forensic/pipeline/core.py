"""
Pure forensic pipeline orchestration core (spec 11_PIPELINE_AND_E2E.md §B13.1).

Coordinates end-to-end evidence processing from raw bytes to forensic findings:
  integrity → detect → decrypt → parse → recover → timeline → correlate → summary

Strict adherence to:
- master.md R4: Zero disk writes; pure in-memory execution.
- master.md R5: Keys are radioactive. Redacted strings, no secrets in logs/results.
- master.md R7: No fake capability; honest failure states (ENCRYPTED_KEY_REQUIRED, etc.).
- master.md R8: Complete forensic provenance, confidence scores (< 1.0 for inferences).
- master.md R11: Total determinism; wall-clock fields excluded from cryptographic content hashes.
- master.md R12: Untrusted input hardening (PRAGMA query_only=ON, trusted_schema=OFF, ZIP limits).
- master.md R18: Pure module without DB or FastAPI dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import zipfile

from forensic.common.hashing import sha256_hex
from forensic.correlation.artifacts import ArtifactStitcher, ExtractedArtifact
from forensic.correlation.entities import IdentityResolutionEngine
from forensic.correlation.handover import PlatformHandoverDetector
from forensic.correlation.matcher import (
    MediaItem,
    TelegramContact,
    TelegramMessage,
    WhatsAppContact,
    WhatsAppMessage,
)
from forensic.correlation.media_hash import PerceptualMediaCorrelator, compute_dhash, compute_phash
from forensic.correlation.models import CorrelationFinding
from forensic.correlation.rendezvous import LocationObservation, SpatiotemporalRendezvousDetector
from forensic.correlation.thresholds import DEFAULT_THRESHOLDS, CorrelationThresholds
from forensic.decryption.whatsapp.crypt14 import Crypt14Decryptor
from forensic.decryption.whatsapp.crypt15 import Crypt15Decryptor
from forensic.decryption.whatsapp.errors import (
    DecryptionAuthFailed,
    DecompressionFailed,
    TruncatedInput,
    UnsupportedVersion,
)
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.detectors.format_detector import FormatDetection, detect_format
from forensic.pipeline.models import (
    EvidenceInput,
    PipelineConfig,
    PipelineResult,
    PipelineStatus,
    StageResult,
    StageStatus,
)
from forensic.recovery.models import RecoveryFinding, RecoveryResult
from forensic.recovery.orchestrator import RecoveryPipeline
from forensic.telegram.models import TgParseResult, UnsupportedSchemaError as TgUnsupportedSchemaError
from forensic.telegram.parser import TelegramParser
from forensic.timeline.builder import PureTimelineBuilder, TimelineResult
from forensic.timeline.config import TimelineConfig
from forensic.whatsapp.models import UnsupportedSchemaError as WaUnsupportedSchemaError
from forensic.whatsapp.parser import WAParseResult, WhatsAppParser


def _canonical_stage_hash(stage_name: str, evidence_id: Optional[str], status: str, counts: Dict[str, int], data_to_hash: Any) -> str:
    """Compute deterministic cryptographic SHA-256 for a stage output (R11)."""
    obj = {
        "stage": stage_name,
        "evidence_id": evidence_id,
        "status": status,
        "counts": dict(sorted(counts.items())),
        "payload": data_to_hash,
    }
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_hex(raw)


def run_pipeline(
    inputs: Sequence[EvidenceInput],
    keys: Sequence[KeyMaterial] = (),
    cfg: Optional[PipelineConfig] = None,
    run_id: Optional[str] = None,
) -> PipelineResult:
    """
    Execute the deterministic pure forensic analysis pipeline.

    Args:
        inputs: Sequence of evidence exhibits (bytes in memory).
        keys: Sequence of cryptographic key material (radioactive, never persisted).
        cfg: Optional pipeline configuration and thresholds.
        run_id: Optional identifier for this execution run.

    Returns:
        PipelineResult with structured stages, findings, timeline, and cryptographic content hash.
    """
    start_wall_time = time.time()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    config = cfg or PipelineConfig()
    actual_run_id = run_id or f"run_{int(start_wall_time * 1000)}"

    stages: List[StageResult] = []
    failed_evidence_ids: Set[str] = set()
    skipped_downstream_evidence_ids: Set[str] = set()

    # R11 Input Ordering Determinism: sort inputs deterministically by (name, sha256, evidence_id)
    sorted_inputs = sorted(inputs, key=lambda x: (x.name, x.sha256, str(x.evidence_id)))

    # In-memory working state
    verified_inputs: Dict[str, EvidenceInput] = {}
    detected_formats: Dict[str, FormatDetection] = {}
    decrypted_databases: Dict[str, bytes] = {}  # evidence_id -> decrypted SQLite bytes
    primary_databases: Dict[str, bytes] = {}    # evidence_id -> SQLite bytes (plain or decrypted)

    parsed_wa: Dict[str, WAParseResult] = {}
    parsed_tg: Dict[str, TgParseResult] = {}
    recovered_data: Dict[str, RecoveryResult] = {}
    extracted_media_items: List[MediaItem] = []
    media_exif_records: List[Dict[str, Any]] = []

    # =========================================================================
    # STAGE 1: Integrity Verification (Re-hash vs claimed sha256)
    # =========================================================================
    for inp in sorted_inputs:
        t0 = time.time()
        actual_hash = sha256_hex(inp.data)
        if actual_hash.lower() != inp.sha256.lower():
            failed_evidence_ids.add(inp.evidence_id)
            err_msg = f"Evidence {inp.name} (ID: {inp.evidence_id}) hash mismatch: claimed {inp.sha256}, actual {actual_hash}"
            counts = {"verified": 0, "mismatched": 1}
            stages.append(
                StageResult(
                    stage="integrity",
                    status="FAILED_HONEST",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=(),
                    errors=(err_msg,),
                    output_hash=_canonical_stage_hash("integrity", inp.evidence_id, "FAILED_HONEST", counts, err_msg),
                    evidence_id=inp.evidence_id,
                    error_code="INTEGRITY_FAILURE",
                )
            )
        else:
            verified_inputs[inp.evidence_id] = inp
            counts = {"verified": 1, "mismatched": 0}
            stages.append(
                StageResult(
                    stage="integrity",
                    status="COMPLETED",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=(),
                    errors=(),
                    output_hash=_canonical_stage_hash("integrity", inp.evidence_id, "COMPLETED", counts, actual_hash),
                    evidence_id=inp.evidence_id,
                    details={"verified_sha256": actual_hash},
                )
            )

    # =========================================================================
    # STAGE 2: Format & Artifact Detection
    # =========================================================================
    for inp in sorted_inputs:
        if inp.evidence_id in failed_evidence_ids:
            stages.append(
                StageResult(
                    stage="detect",
                    status="SKIPPED",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=0.0,
                    counts={"detected": 0},
                    warnings=(),
                    errors=(),
                    output_hash=_canonical_stage_hash("detect", inp.evidence_id, "SKIPPED", {"detected": 0}, "integrity_failure"),
                    evidence_id=inp.evidence_id,
                    skip_reason="dependency:integrity_failure",
                )
            )
            continue

        t0 = time.time()
        detection = detect_format(inp.data, filename=inp.name)
        detected_formats[inp.evidence_id] = detection
        counts = {
            "detected": 1,
            "conflicts": len(detection.conflicts),
            "extension_conflicts": len(detection.conflicts),
        }
        stages.append(
            StageResult(
                stage="detect",
                status="COMPLETED",
                started_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=round((time.time() - t0) * 1000, 3),
                counts=counts,
                warnings=tuple(detection.conflicts),
                errors=(),
                output_hash=_canonical_stage_hash("detect", inp.evidence_id, "COMPLETED", counts, detection.to_dict()),
                evidence_id=inp.evidence_id,
                details=detection.to_dict(),
            )
        )

    # =========================================================================
    # STAGE 3: Decryption (WhatsApp Crypt14 / Crypt15)
    # =========================================================================
    for inp in sorted_inputs:
        ev_id = inp.evidence_id
        if ev_id in failed_evidence_ids:
            continue

        detection = detected_formats.get(ev_id)
        if not detection:
            continue

        fmt = detection.format
        if fmt not in ("WHATSAPP_CRYPT14", "WHATSAPP_CRYPT15"):
            # If it's a plain database or other file, decryption stage is skipped or not required
            continue

        t0 = time.time()

        # Rule R7: Check if keys are available
        if not keys:
            failed_evidence_ids.add(ev_id)
            skipped_downstream_evidence_ids.add(ev_id)
            counts = {"decrypted": 0}
            stages.append(
                StageResult(
                    stage="decrypt",
                    status="FAILED_HONEST",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=(),
                    errors=(f"No cryptographic key provided for encrypted container {inp.name} ({fmt})",),
                    output_hash=_canonical_stage_hash("decrypt", ev_id, "FAILED_HONEST", counts, "ENCRYPTED_KEY_REQUIRED"),
                    evidence_id=ev_id,
                    error_code="ENCRYPTED_KEY_REQUIRED",
                )
            )
            continue

        # Attempt decryption with provided keys
        decrypt_success = False
        last_error_code: Optional[str] = None
        last_error_msg: str = ""

        decryptor = Crypt14Decryptor() if fmt == "WHATSAPP_CRYPT14" else Crypt15Decryptor()

        for key_mat in keys:
            # Pre-stage integrity re-check before decryption (spec B13.1)
            if sha256_hex(inp.data).lower() != inp.sha256.lower():
                last_error_code = "INTEGRITY_FAILURE"
                last_error_msg = "Integrity re-check failed prior to decryption"
                break

            try:
                decrypted_res = decryptor.decrypt(
                    inp.data,
                    key_mat,
                    max_decompressed_size=config.max_unpacked_bytes,
                )
                decrypted_bytes = decrypted_res.plaintext
                decrypted_databases[ev_id] = decrypted_bytes
                primary_databases[ev_id] = decrypted_bytes
                decrypt_success = True

                # R5 compliance: records only key_type and truncated fingerprint
                key_details = {
                    "key_type": key_mat.key_type,
                    "key_fingerprint": key_mat.fingerprint(),
                    "decrypted_size": len(decrypted_bytes),
                    "output_sha256": decrypted_res.output_sha256,
                }
                counts = {"decrypted": 1, "size_bytes": len(decrypted_bytes)}
                stages.append(
                    StageResult(
                        stage="decrypt",
                        status="COMPLETED",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=(),
                        errors=(),
                        output_hash=_canonical_stage_hash("decrypt", ev_id, "COMPLETED", counts, sha256_hex(decrypted_bytes)),
                        evidence_id=ev_id,
                        details=key_details,
                    )
                )
                break
            except DecryptionAuthFailed as e:
                last_error_code = "AUTH_FAILED"
                last_error_msg = str(e)
            except TruncatedInput as e:
                last_error_code = "TRUNCATED_INPUT"
                last_error_msg = str(e)
            except UnsupportedVersion as e:
                last_error_code = "UNSUPPORTED_VERSION"
                last_error_msg = str(e)
            except DecompressionFailed as e:
                last_error_code = "TRUNCATED_INPUT"
                last_error_msg = str(e)
            except Exception as e:
                last_error_code = "ERROR"
                last_error_msg = f"Unexpected decryption error: {type(e).__name__}"

        if not decrypt_success:
            failed_evidence_ids.add(ev_id)
            skipped_downstream_evidence_ids.add(ev_id)
            err_code = last_error_code or "AUTH_FAILED"
            status: StageStatus = "ERROR" if err_code == "ERROR" else "FAILED_HONEST"
            counts = {"decrypted": 0}
            stages.append(
                StageResult(
                    stage="decrypt",
                    status=status,
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=(),
                    errors=(last_error_msg or f"Decryption failed for {inp.name}",),
                    output_hash=_canonical_stage_hash("decrypt", ev_id, status, counts, err_code),
                    evidence_id=ev_id,
                    error_code=err_code,
                )
            )

    # Register unencrypted SQLite databases into primary_databases
    for inp in sorted_inputs:
        ev_id = inp.evidence_id
        if ev_id in failed_evidence_ids:
            continue
        detection = detected_formats.get(ev_id)
        if detection and detection.format in (
            "WHATSAPP_MSGSTORE",
            "TELEGRAM_CACHE4",
            "SQLITE_PLAIN",
        ):
            primary_databases[ev_id] = inp.data

    # Helper: Find auxiliary evidence (WAL, SHM, Contacts, Media)
    wal_by_stem: Dict[str, bytes] = {}
    shm_by_stem: Dict[str, bytes] = {}
    contacts_bytes: Optional[bytes] = None

    for inp in sorted_inputs:
        if inp.evidence_id in failed_evidence_ids:
            continue
        lower_name = inp.name.lower()
        detection = detected_formats.get(inp.evidence_id)
        if lower_name.endswith("-wal") or (detection and detection.format == "SQLITE_WAL"):
            stem = inp.name[:-4] if inp.name.endswith("-wal") else inp.name
            wal_by_stem[stem.lower()] = inp.data
        elif lower_name.endswith("-shm"):
            stem = inp.name[:-4]
            shm_by_stem[stem.lower()] = inp.data
        elif lower_name in ("wa.db", "contacts.db") or inp.role == "wa_contacts" or (detection and detection.format == "WHATSAPP_WADB"):
            contacts_bytes = inp.data
        elif lower_name.endswith(".zip") or inp.role == "media_zip":
            # Extract media items safely from ZIP
            try:
                zf = zipfile.ZipFile(io.BytesIO(inp.data), "r")
                members = zf.namelist()[:500]  # Cap at 500 members (R12)
                for member_name in members:
                    if member_name.endswith("/"):
                        continue
                    m_data = zf.read(member_name)
                    if len(m_data) > config.max_unpacked_bytes:
                        continue
                    m_lower = member_name.lower()
                    if any(m_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                        m_hash = sha256_hex(m_data)
                        extracted_media_items.append(
                            MediaItem(
                                evidence_id=int(inp.evidence_id) if inp.evidence_id.isdigit() else 0,
                                file_path=member_name,
                                sha256=m_hash,
                                mime_type="image/jpeg" if "jp" in m_lower else "image/png",
                                media_type="image",
                            )
                        )
                        # Compute perceptual hash in-memory
                        dh = compute_dhash(m_data)
                        ph = compute_phash(m_data)
                        media_exif_records.append({
                            "evidence_id": inp.evidence_id,
                            "evidence_sha256": inp.sha256,
                            "file_name": member_name.split("/")[-1],
                            "sha256": m_hash,
                            "dhash": dh,
                            "phash": ph,
                            "data_bytes": m_data,
                        })
            except Exception:
                pass
        elif any(lower_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
            try:
                m_data = inp.data
                m_lower = lower_name
                m_hash = sha256_hex(m_data)
                extracted_media_items.append(
                    MediaItem(
                        evidence_id=int(inp.evidence_id) if inp.evidence_id.isdigit() else 0,
                        file_path=inp.name,
                        sha256=m_hash,
                        mime_type="image/jpeg" if "jp" in m_lower else "image/png",
                        media_type="image",
                    )
                )
                dh = compute_dhash(m_data)
                ph = compute_phash(m_data)
                plat = "whatsapp" if ("whatsapp" in m_lower or "wa" in m_lower) else "telegram"
                media_exif_records.append({
                    "evidence_id": inp.evidence_id,
                    "evidence_sha256": inp.sha256,
                    "file_name": inp.name,
                    "sha256": m_hash,
                    "dhash": dh,
                    "phash": ph,
                    "platform": plat,
                    "data_bytes": m_data,
                })
            except Exception:
                pass

    # =========================================================================
    # STAGE 4: Parsing (WhatsApp msgstore & Telegram cache4)
    # =========================================================================
    for inp in sorted_inputs:
        ev_id = inp.evidence_id
        if ev_id in failed_evidence_ids or ev_id in skipped_downstream_evidence_ids:
            if ev_id in skipped_downstream_evidence_ids:
                stages.append(
                    StageResult(
                        stage="parse",
                        status="SKIPPED",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=0.0,
                        counts={"messages": 0},
                        warnings=(),
                        errors=(),
                        output_hash=_canonical_stage_hash("parse", ev_id, "SKIPPED", {"messages": 0}, "dependency"),
                        evidence_id=ev_id,
                        skip_reason="dependency:decrypt",
                    )
                )
            continue

        detection = detected_formats.get(ev_id)
        if not detection:
            continue

        db_bytes = primary_databases.get(ev_id)
        if not db_bytes:
            continue

        # Pre-stage integrity verification (R3, spec B13.1)
        if sha256_hex(inp.data).lower() != inp.sha256.lower():
            failed_evidence_ids.add(ev_id)
            continue

        t0 = time.time()
        # Find matching WAL/SHM
        base_stem = inp.name.replace(".crypt14", "").replace(".crypt15", "").lower()
        wal_data = wal_by_stem.get(base_stem)
        shm_data = shm_by_stem.get(base_stem)

        fmt = detection.format
        is_wa = fmt in ("WHATSAPP_MSGSTORE", "WHATSAPP_CRYPT14", "WHATSAPP_CRYPT15") or (
            fmt == "SQLITE_PLAIN" and b"message" in db_bytes and b"chat" in db_bytes
        )
        is_tg = fmt in ("TELEGRAM_CACHE4",) or (
            fmt == "SQLITE_PLAIN" and b"messages_v2" in db_bytes
        )

        if is_wa:
            try:
                wa_parser = WhatsAppParser(
                    msgstore_source=db_bytes,
                    evidence_id=ev_id,
                    evidence_sha256=inp.sha256,
                    wa_db_source=contacts_bytes,
                    derived_from_artifact_id=f"derived_{ev_id}" if ev_id in decrypted_databases else None,
                )
                wa_result = wa_parser.parse()
                parsed_wa[ev_id] = wa_result
                counts = {
                    "messages": len(wa_result.messages),
                    "chats": len(wa_result.chats),
                    "contacts": len(wa_result.contacts),
                    "revocations": len(wa_result.revocations),
                    "edits": len(wa_result.edits),
                }
                stages.append(
                    StageResult(
                        stage="parse",
                        status="COMPLETED",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=tuple(wa_result.limitations),
                        errors=(),
                        output_hash=_canonical_stage_hash(
                            "parse",
                            ev_id,
                            "COMPLETED",
                            counts,
                            [m.key_id for m in wa_result.messages[:200]],
                        ),
                        evidence_id=ev_id,
                        details={"schema_family": wa_result.schema_family.family},
                    )
                )
            except WaUnsupportedSchemaError as e:
                failed_evidence_ids.add(ev_id)
                counts = {"messages": 0}
                stages.append(
                    StageResult(
                        stage="parse",
                        status="FAILED_HONEST",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=(),
                        errors=(str(e),),
                        output_hash=_canonical_stage_hash("parse", ev_id, "FAILED_HONEST", counts, "UNSUPPORTED_SCHEMA"),
                        evidence_id=ev_id,
                        error_code="UNSUPPORTED_SCHEMA",
                    )
                )
            except Exception as e:
                failed_evidence_ids.add(ev_id)
                counts = {"messages": 0}
                stages.append(
                    StageResult(
                        stage="parse",
                        status="ERROR",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=(),
                        errors=(f"WhatsApp parser error: {str(e)}",),
                        output_hash=_canonical_stage_hash("parse", ev_id, "ERROR", counts, "PARSE_ERROR"),
                        evidence_id=ev_id,
                        error_code="PARSE_ERROR",
                    )
                )

        elif is_tg:
            try:
                tg_parser = TelegramParser(
                    db_source=db_bytes,
                    evidence_id=ev_id,
                    wal_source=wal_data,
                    shm_source=shm_data,
                    evidence_sha256=inp.sha256,
                )
                tg_result = tg_parser.parse()
                parsed_tg[ev_id] = tg_result
                counts = {
                    "messages": len(tg_result.messages),
                    "dialogs": len(tg_result.dialogs),
                    "users": len(tg_result.users),
                    "chats": len(tg_result.chats),
                    "unparsed_blobs": len(tg_result.unparsed_blobs),
                }
                stages.append(
                    StageResult(
                        stage="parse",
                        status="COMPLETED",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=tuple(tg_result.limitations),
                        errors=(),
                        output_hash=_canonical_stage_hash(
                            "parse",
                            ev_id,
                            "COMPLETED",
                            counts,
                            [m.mid for m in tg_result.messages[:200]],
                        ),
                        evidence_id=ev_id,
                        details={"unparsed_blobs_count": len(tg_result.unparsed_blobs)},
                    )
                )
            except TgUnsupportedSchemaError as e:
                failed_evidence_ids.add(ev_id)
                counts = {"messages": 0}
                stages.append(
                    StageResult(
                        stage="parse",
                        status="FAILED_HONEST",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=(),
                        errors=(str(e),),
                        output_hash=_canonical_stage_hash("parse", ev_id, "FAILED_HONEST", counts, "UNSUPPORTED_SCHEMA"),
                        evidence_id=ev_id,
                        error_code="UNSUPPORTED_SCHEMA",
                    )
                )
            except Exception as e:
                failed_evidence_ids.add(ev_id)
                counts = {"messages": 0}
                stages.append(
                    StageResult(
                        stage="parse",
                        status="ERROR",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=round((time.time() - t0) * 1000, 3),
                        counts=counts,
                        warnings=(),
                        errors=(f"Telegram parser error: {str(e)}",),
                        output_hash=_canonical_stage_hash("parse", ev_id, "ERROR", counts, "PARSE_ERROR"),
                        evidence_id=ev_id,
                        error_code="PARSE_ERROR",
                    )
                )

    # =========================================================================
    # STAGE 5: Deleted-Data Recovery (B10)
    # =========================================================================
    for inp in sorted_inputs:
        ev_id = inp.evidence_id
        if ev_id in failed_evidence_ids or ev_id in skipped_downstream_evidence_ids:
            if ev_id in skipped_downstream_evidence_ids:
                stages.append(
                    StageResult(
                        stage="recover",
                        status="SKIPPED",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=0.0,
                        counts={"recovered_findings": 0},
                        warnings=(),
                        errors=(),
                        output_hash=_canonical_stage_hash("recover", ev_id, "SKIPPED", {"recovered_findings": 0}, "dependency"),
                        evidence_id=ev_id,
                        skip_reason="dependency:decrypt",
                    )
                )
            continue

        db_bytes = primary_databases.get(ev_id)
        if not db_bytes:
            continue

        detection = detected_formats.get(ev_id)
        if not detection:
            continue

        # Pre-stage integrity verification (R3, spec B13.1)
        if sha256_hex(inp.data).lower() != inp.sha256.lower():
            failed_evidence_ids.add(ev_id)
            continue

        t0 = time.time()
        base_stem = inp.name.replace(".crypt14", "").replace(".crypt15", "").lower()
        wal_data = wal_by_stem.get(base_stem)
        app_hint = "telegram" if (detection.format == "TELEGRAM_CACHE4" or b"messages_v2" in db_bytes) else "whatsapp"

        try:
            recovery_pipe = RecoveryPipeline(
                db_bytes=db_bytes,
                wal_bytes=wal_data,
                app_hint=app_hint,
                evidence_id=ev_id,
                evidence_sha256=inp.sha256,
            )
            rec_result = recovery_pipe.run()
            recovered_data[ev_id] = rec_result

            tier_counts = {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0}
            for f in rec_result.findings:
                tier_counts[f"tier{f.tier}"] = tier_counts.get(f"tier{f.tier}", 0) + 1

            counts = {
                "recovered_findings": len(rec_result.findings),
                **tier_counts,
            }
            stages.append(
                StageResult(
                    stage="recover",
                    status="COMPLETED",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=tuple(rec_result.warnings),
                    errors=(),
                    output_hash=_canonical_stage_hash(
                        "recover",
                        ev_id,
                        "COMPLETED",
                        counts,
                        [f.finding_id for f in rec_result.findings],
                    ),
                    evidence_id=ev_id,
                    details={"warnings": list(rec_result.warnings)},
                )
            )
        except Exception as e:
            counts = {"recovered_findings": 0}
            stages.append(
                StageResult(
                    stage="recover",
                    status="ERROR",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=round((time.time() - t0) * 1000, 3),
                    counts=counts,
                    warnings=(),
                    errors=(f"Recovery pipeline error: {str(e)}",),
                    output_hash=_canonical_stage_hash("recover", ev_id, "ERROR", counts, "RECOVERY_ERROR"),
                    evidence_id=ev_id,
                    error_code="RECOVERY_ERROR",
                )
            )

    # =========================================================================
    # STAGE 6: Timeline & Time Handling (B11)
    # =========================================================================
    t0_tl = time.time()
    evidence_records_tl: List[Dict[str, Any]] = []
    for inp in sorted_inputs:
        evidence_records_tl.append({
            "evidence_id": inp.evidence_id,
            "evidence_sha256": inp.sha256,
            "filename": inp.name,
            "uploaded_at_ms": None,
            "evidence_type": detected_formats.get(inp.evidence_id, FormatDetection(format="UNKNOWN", confidence_basis="none")).format,
        })

    all_wa_msgs_tl: List[Dict[str, Any]] = []
    all_wa_revocations_tl: List[Dict[str, Any]] = []
    all_wa_edits_tl: List[Dict[str, Any]] = []
    for wa_res in parsed_wa.values():
        all_wa_msgs_tl.extend([m.to_dict() for m in wa_res.messages])
        all_wa_revocations_tl.extend([r.to_dict() for r in wa_res.revocations])
        all_wa_edits_tl.extend([e.to_dict() for e in wa_res.edits])

    all_tg_msgs_tl: List[Dict[str, Any]] = []
    for tg_res in parsed_tg.values():
        all_tg_msgs_tl.extend([m.to_dict() for m in tg_res.messages])

    all_recovered_records_tl: List[Dict[str, Any]] = []
    for rec_res in recovered_data.values():
        all_recovered_records_tl.extend([f.to_dict() for f in rec_res.findings])

    tl_builder = PureTimelineBuilder(config=config.timeline_cfg or TimelineConfig())
    timeline_result = tl_builder.build_timeline(
        evidence_records=evidence_records_tl,
        whatsapp_messages=all_wa_msgs_tl,
        whatsapp_revocations=all_wa_revocations_tl,
        whatsapp_edits=all_wa_edits_tl,
        telegram_messages=all_tg_msgs_tl,
        recovered_records=all_recovered_records_tl,
        media_exif_records=media_exif_records,
    )

    tl_counts = {
        "total_events": len(timeline_result.events),
        "unplaced_indicators": len(timeline_result.unplaced_indicators),
    }
    stages.append(
        StageResult(
            stage="timeline",
            status="COMPLETED",
            started_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=round((time.time() - t0_tl) * 1000, 3),
            counts=tl_counts,
            warnings=(),
            errors=(),
            output_hash=timeline_result.timeline_hash,
            details={"timeline_hash": timeline_result.timeline_hash},
        )
    )

    # =========================================================================
    # STAGE 7: Cross-Platform Correlation (B12)
    # =========================================================================
    t0_corr = time.time()
    all_wa_messages_corr: List[WhatsAppMessage] = []
    all_wa_contacts_corr: List[WhatsAppContact] = []
    all_tg_messages_corr: List[TelegramMessage] = []
    all_tg_contacts_corr: List[TelegramContact] = []

    for wa_res in parsed_wa.values():
        for m in wa_res.messages:
            all_wa_messages_corr.append(
                WhatsAppMessage(
                    evidence_id=int(m.provenance.evidence_id) if m.provenance.evidence_id.isdigit() else 0,
                    message_id=str(m.row_id),
                    key_remote_jid=m.chat_jid or "",
                    sender_jid=m.sender_jid or "",
                    participant_jid=m.sender_jid or "",
                    body=m.text or "",
                    timestamp=m.ts_utc_ms or 0,
                    media_type=m.message_type_name,
                    media_path=m.media_ref.file_path if m.media_ref else None,
                    message_type=m.message_type_name,
                    status=str(m.status),
                )
            )
        for c in wa_res.contacts:
            all_wa_contacts_corr.append(
                WhatsAppContact(
                    evidence_id=int(c.provenance.evidence_id) if c.provenance.evidence_id.isdigit() else 0,
                    jid=c.jid,
                    display_name=c.display_name or c.jid,
                    phone_number=c.phone_number or "",
                    status="active",
                )
            )

    for tg_res in parsed_tg.values():
        for m in tg_res.messages:
            all_tg_messages_corr.append(
                TelegramMessage(
                    evidence_id=int(m.provenance.evidence_id) if m.provenance.evidence_id.isdigit() else 0,
                    message_id=int(m.mid),
                    dialog_id=str(m.dialog_id),
                    sender_id=int(m.from_id or 0),
                    body=m.text or "",
                    timestamp=m.date_utc_ms or 0,
                    media_type=m.media_kind,
                    media_path=None,
                    message_type=m.media_kind or "text",
                )
            )
        for u in tg_res.users:
            all_tg_contacts_corr.append(
                TelegramContact(
                    evidence_id=int(u.provenance.evidence_id) if u.provenance.evidence_id.isdigit() else 0,
                    user_id=int(u.uid),
                    first_name=u.first_name or "",
                    last_name=u.last_name or "",
                    username=u.username or "",
                    phone=u.phone or "",
                )
            )

    correlation_thresholds = CorrelationThresholds(
        version=DEFAULT_THRESHOLDS.version,
        phone_default_region=str(config.correlation_params.get("phone_default_region", DEFAULT_THRESHOLDS.phone_default_region)),
        dhash_max_hamming_distance=int(config.correlation_params.get("dhash_max_hamming_distance", DEFAULT_THRESHOLDS.dhash_max_hamming_distance)),
        phash_max_hamming_distance=int(config.correlation_params.get("phash_max_hamming_distance", DEFAULT_THRESHOLDS.phash_max_hamming_distance)),
        rendezvous_max_distance_meters=float(config.correlation_params.get("rendezvous_max_distance_meters", DEFAULT_THRESHOLDS.rendezvous_max_distance_meters)),
        rendezvous_max_time_seconds=int(config.correlation_params.get("rendezvous_max_time_seconds", DEFAULT_THRESHOLDS.rendezvous_max_time_seconds)),
        handover_max_time_seconds=int(config.correlation_params.get("handover_max_time_seconds", DEFAULT_THRESHOLDS.handover_max_time_seconds)),
        min_image_dimension=int(config.correlation_params.get("min_image_dimension", DEFAULT_THRESHOLDS.min_image_dimension)),
        min_image_entropy=float(config.correlation_params.get("min_image_entropy", DEFAULT_THRESHOLDS.min_image_entropy)),
        report_threshold_confidence=float(config.correlation_params.get("report_threshold_confidence", DEFAULT_THRESHOLDS.report_threshold_confidence)),
    )

    all_correlation_findings: List[CorrelationFinding] = []

    # 1. Identity resolution
    identity_engine = IdentityResolutionEngine(thresholds=correlation_thresholds)
    identity_findings = identity_engine.resolve_findings(all_wa_contacts_corr, all_tg_contacts_corr)
    all_correlation_findings.extend(identity_findings)

    # 2. Handover detection
    handover_detector = PlatformHandoverDetector(thresholds=correlation_thresholds)
    handover_findings = handover_detector.detect_handover_findings(all_wa_messages_corr, all_tg_messages_corr)
    all_correlation_findings.extend(handover_findings)

    # 3. Media correlation
    media_correlator = PerceptualMediaCorrelator(thresholds=correlation_thresholds)
    media_records_for_corr = []
    for idx, m_exif in enumerate(media_exif_records):
        media_records_for_corr.append({
            "id": idx + 1,
            "file_name": m_exif.get("file_name", f"media_{idx}"),
            "sha256": m_exif.get("sha256", ""),
            "dhash": m_exif.get("dhash"),
            "phash": m_exif.get("phash"),
            "platform": m_exif.get("platform") or ("whatsapp" if ("wa" in m_exif.get("file_name", "").lower() or "whatsapp" in m_exif.get("file_name", "").lower()) else "telegram"),
            "evidence_id": m_exif.get("evidence_id", "0"),
        })
    media_findings = media_correlator.correlate_media_findings(media_records_for_corr)
    all_correlation_findings.extend(media_findings)

    # 4. Artifact stitching (BTC, EVM, IBAN, Canonical URL)
    artifact_stitcher = ArtifactStitcher(
        custom_keywords=list(config.custom_keywords),
        thresholds=correlation_thresholds,
    )
    extracted_artifacts: List[ExtractedArtifact] = []
    for msg in all_wa_messages_corr:
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
    for msg in all_tg_messages_corr:
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
    all_correlation_findings.extend(artifact_findings)

    # 5. Spatiotemporal Rendezvous
    rendezvous_detector = SpatiotemporalRendezvousDetector(thresholds=correlation_thresholds)
    loc_obs: List[LocationObservation] = []
    for wa_res in parsed_wa.values():
        for m in wa_res.messages:
            if m.location_ref and m.ts_utc_ms is not None:
                loc_obs.append(
                    LocationObservation(
                        observation_id=f"wa_loc_{m.row_id}",
                        source_type="wa_location",
                        source_id=str(m.row_id),
                        platform="whatsapp",
                        latitude=m.location_ref.latitude,
                        longitude=m.location_ref.longitude,
                        utc_ms=m.ts_utc_ms,
                        evidence_id=int(m.provenance.evidence_id) if m.provenance.evidence_id.isdigit() else 0,
                        sender_id=m.sender_jid or m.chat_jid,
                        label=m.location_ref.place_name,
                    )
                )
    for tg_res in parsed_tg.values():
        for m in tg_res.messages:
            if m.geo_lat is not None and m.geo_lon is not None and m.date_utc_ms is not None:
                loc_obs.append(
                    LocationObservation(
                        observation_id=f"tg_loc_{m.mid}",
                        source_type="tg_location",
                        source_id=str(m.mid),
                        platform="telegram",
                        latitude=m.geo_lat,
                        longitude=m.geo_lon,
                        utc_ms=m.date_utc_ms,
                        evidence_id=int(m.provenance.evidence_id) if m.provenance.evidence_id.isdigit() else 0,
                        sender_id=str(m.from_id or m.dialog_id),
                    )
                )
    rendezvous_findings = rendezvous_detector.detect_rendezvous_findings(loc_obs)
    all_correlation_findings.extend(rendezvous_findings)

    # Filter findings by reporting threshold (default 0.70)
    reported_findings = [
        f for f in all_correlation_findings
        if f.confidence_score >= correlation_thresholds.report_threshold_confidence
    ]

    # Deterministic sorting (R11): kind, -confidence_score, finding_id
    reported_findings.sort(key=lambda f: (f.kind, -f.confidence_score, f.finding_id))

    corr_counts = {
        "total_findings": len(reported_findings),
        "identity_findings": len([f for f in reported_findings if f.kind == "phone_identity_resolution"]),
        "handover_findings": len([f for f in reported_findings if f.kind == "platform_handover"]),
        "media_findings": len([f for f in reported_findings if f.kind == "cross_platform_media_hash"]),
        "artifact_findings": len([f for f in reported_findings if "artifact" in f.kind or "reuse" in f.kind]),
        "rendezvous_findings": len([f for f in reported_findings if f.kind == "spatiotemporal_rendezvous"]),
    }

    stages.append(
        StageResult(
            stage="correlate",
            status="COMPLETED",
            started_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=round((time.time() - t0_corr) * 1000, 3),
            counts=corr_counts,
            warnings=(),
            errors=(),
            output_hash=_canonical_stage_hash(
                "correlate",
                None,
                "COMPLETED",
                corr_counts,
                [f.finding_id for f in reported_findings],
            ),
            details={"findings_count": len(reported_findings)},
        )
    )

    # =========================================================================
    # STAGE 8: Summary & Pipeline Result Assembly
    # =========================================================================
    completed_at_iso = datetime.now(timezone.utc).isoformat()
    total_duration_ms = round((time.time() - start_wall_time) * 1000, 3)

    # Pipeline status: FAILED if no stage completed; PARTIAL if any stage failed/skipped; COMPLETED if all OK
    all_statuses = [s.status for s in stages]
    if all(st == "COMPLETED" for st in all_statuses):
        pipeline_status: PipelineStatus = "COMPLETED"
    elif any(st == "COMPLETED" for st in all_statuses):
        pipeline_status = "PARTIAL"
    else:
        pipeline_status = "FAILED"

    # Cryptographic content hash (R11): SHA-256 over ordered stage output hashes
    stage_hash_vector = [f"{s.stage}:{s.evidence_id or ''}:{s.status}:{s.output_hash}" for s in stages]
    content_hash = sha256_hex(
        json.dumps(stage_hash_vector, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    # Summary: honest accounting of all stages, failures, and keys (fingerprint only, R5)
    non_completed_stages = [
        {
            "stage": s.stage,
            "evidence_id": s.evidence_id,
            "status": s.status,
            "error_code": s.error_code,
            "skip_reason": s.skip_reason,
            "errors": list(s.errors),
        }
        for s in stages
        if s.status != "COMPLETED"
    ]

    keys_summary = [
        {"key_type": k.key_type, "key_fingerprint": k.fingerprint()}
        for k in keys
    ]

    summary = {
        "pipeline_status": pipeline_status,
        "content_hash": content_hash,
        "total_inputs": len(sorted_inputs),
        "failed_inputs": len(failed_evidence_ids),
        "non_completed_stages": non_completed_stages,
        "keys_used": keys_summary,
        "counts": {
            "whatsapp_messages": sum(len(res.messages) for res in parsed_wa.values()),
            "telegram_messages": sum(len(res.messages) for res in parsed_tg.values()),
            "recovered_findings": sum(len(res.findings) for res in recovered_data.values()),
            "timeline_events": len(timeline_result.events),
            "correlation_findings": len(reported_findings),
        },
    }

    # Data container for callers/service layer (persistence or CLI)
    collected_data = {
        "parsed_wa": parsed_wa,
        "parsed_tg": parsed_tg,
        "recovered": recovered_data,
        "timeline": timeline_result,
        "correlations": reported_findings,
        "decrypted_databases": decrypted_databases,
    }

    return PipelineResult(
        run_id=actual_run_id,
        status=pipeline_status,
        content_hash=content_hash,
        stages=tuple(stages),
        summary=summary,
        started_at=started_at_iso,
        completed_at=completed_at_iso,
        duration_ms=total_duration_ms,
        data=collected_data,
    )
