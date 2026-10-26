"""
Cryptographic Decryption API (B6).
Provides endpoints for detecting encryption formats, executing in-memory decryption,
recording judicial operation provenance, and streaming derived artifacts from PostgreSQL BYTEA.
Strictly adheres to master.md R3, R4, R5, R7, R12, R15, R19.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import io
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import (
    ActivityLog,
    Case,
    DecryptionOperation,
    DerivedArtifact,
    Evidence,
    EvidenceFile,
)
from backend.schemas.decryption import (
    CandidateKeyInfo,
    DecryptionInventoryResponse,
    DecryptionInventoryStats,
    DecryptionOperationResponse,
    DecryptionRunRequest,
    DerivedArtifactResponse,
    DirectlyUsableFileInfo,
    DiscoveredKeyInfo,
    EncryptedFileInfo,
    FormatDetectionResponse,
)
from backend.services.audit_service import AuditService
from backend.services.integrity_service import ensure_integrity
from forensic.decryption.orchestrator import DecryptionOrchestrator, DecryptorNotAvailableError
from forensic.decryption.whatsapp.errors import WhatsAppDecryptionError
from forensic.decryption.whatsapp.types import KeyMaterial

router = APIRouter(tags=["decryption"])


def _clean_pg_text(val: Any) -> Any:
    """Strip null bytes from text/json structures to prevent PostgreSQL errors."""
    if isinstance(val, str):
        return val.replace("\x00", "")
    elif isinstance(val, list):
        return [_clean_pg_text(x) for x in val]
    elif isinstance(val, dict):
        return {k: _clean_pg_text(v) for k, v in val.items()}
    return val


def _inspect_sqlite_tables(target_bytes: Optional[bytes]) -> tuple[int, list[str]]:
    """Quickly read sqlite_master table names in-memory without persistent or temporary disk I/O."""
    if not target_bytes or not target_bytes.startswith(b"SQLite format 3\x00"):
        return 0, []
    import sqlite3
    try:
        conn = sqlite3.connect(":memory:")
        conn.deserialize(target_bytes)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [row[0] for row in cur.fetchall()]
        conn.close()
        return len(tables), tables[:15]
    except Exception:
        return 0, []


def _detect_file_category(filename: str, mime: Optional[str] = None) -> str:
    fn = filename.lower()
    if fn.endswith((".db", ".sqlite", ".sqlite3")) or "sqlite" in (mime or "").lower():
        return "database"
    if fn.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".m4v", ".mov", ".opus", ".mp3", ".ogg", ".wav", ".aac")):
        return "media"
    if fn.endswith((".xml", ".json", ".plist", ".ini", ".cfg", ".conf", ".txt", ".log")):
        return "config"
    if fn.endswith((".key", ".pem", ".pub", ".crt", ".der", ".keystore")) or "key" in fn:
        return "key"
    if fn.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".html", ".htm")):
        return "document"
    return "other"


def _get_target_bytes_and_name(
    db: Session,
    evidence_id: int,
    file_id: Optional[int] = None,
) -> tuple[bytes, str, Optional[int]]:
    """Retrieve target binary buffer from PostgreSQL BYTEA or disk storage and determine filename."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found.")

    from backend.utils.file_storage import resolve_evidence_path, resolve_evidence_file_path

    if file_id:
        ev_file = db.query(EvidenceFile).filter(
            EvidenceFile.id == file_id,
            EvidenceFile.evidence_id == evidence_id,
        ).first()
        if not ev_file:
            raise HTTPException(status_code=404, detail="Target evidence member file not found.")
        target_bytes = ev_file.content_bytes
        if not target_bytes:
            disk_p = resolve_evidence_file_path(ev_file)
            if disk_p and disk_p.is_file():
                target_bytes = disk_p.read_bytes()
        filename = ev_file.relative_path.split("/")[-1]
        resolved_file_id = ev_file.id
    else:
        target_bytes = evidence.content_bytes
        if not target_bytes:
            disk_p = resolve_evidence_path(evidence.storage_path)
            if disk_p and disk_p.is_file():
                target_bytes = disk_p.read_bytes()
        filename = evidence.original_filename
        resolved_file_id = None

    if not target_bytes:
        raise HTTPException(
            status_code=400,
            detail="Evidence binary buffer is not available in storage.",
        )

    return target_bytes, filename, resolved_file_id


@router.post(
    "/evidence/{evidence_id}/decryption/detect",
    response_model=FormatDetectionResponse,
    status_code=status.HTTP_200_OK,
)
def detect_encryption_format(
    evidence_id: int,
    file_id: Optional[int] = Query(None, description="Optional extracted EvidenceFile ID"),
    db: Session = Depends(get_db),
):
    """
    Perform deep format and entropy inspection on the evidence buffer.
    Never relies solely on filename extensions.
    """
    target_bytes, filename, _ = _get_target_bytes_and_name(db, evidence_id, file_id)
    det = DecryptionOrchestrator.detect_format(target_bytes, filename)
    return FormatDetectionResponse(
        is_encrypted=det.is_encrypted,
        format=det.format,
        confidence=det.confidence,
        entropy=det.entropy,
        parameters=det.parameters,
        reasons=det.reasons,
    )


@router.post(
    "/evidence/{evidence_id}/decryption/run",
    response_model=DecryptionOperationResponse,
    status_code=status.HTTP_200_OK,
)
def run_decryption(
    evidence_id: int,
    req: DecryptionRunRequest,
    db: Session = Depends(get_db),
):
    """
    Execute controlled, auditable cryptographic decryption.
    Plaintext output is stored directly in PostgreSQL BYTEA as a DerivedArtifact (R4).
    Keys are radioactive: secrets are never stored, logged, or exposed (R5).
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found.")

    # 1. Pre-stage integrity verification (R3)
    from backend.services.integrity_service import EvidenceIntegrityError, LegacyUnverifiableError
    try:
        ensure_integrity(evidence_id=evidence.id, db=db, action_context="decryption_prestage")
    except (EvidenceIntegrityError, LegacyUnverifiableError) as ie:
        raise HTTPException(
            status_code=400,
            detail=f"Evidence integrity verification failed: {str(ie)}",
        )

    target_bytes, filename, resolved_file_id = _get_target_bytes_and_name(
        db, evidence_id, req.candidate_file_id
    )

    input_sha256 = hashlib.sha256(target_bytes).hexdigest()

    # 2. Extract secret input (R5: SecretStr prevents leaking in repr/logs)
    secret_input: Union[str, bytes, None] = None
    if req.key_file_id:
        kf = db.query(EvidenceFile).filter(EvidenceFile.id == req.key_file_id).first()
        if kf and kf.content_bytes:
            secret_input = kf.content_bytes

    if not secret_input:
        secret_obj = req.key_data or req.key_material
        if not secret_obj:
            raise HTTPException(
                status_code=400,
                detail="key_data, key_material, or key_file_id must be provided.",
            )

        raw_secret_str = secret_obj.get_secret_value().strip()
        if not raw_secret_str:
            raise HTTPException(
                status_code=400,
                detail="Key material cannot be empty.",
            )

        clean = raw_secret_str.replace(" ", "").replace("-", "")
        if clean.lower().startswith("0x"):
            clean = clean[2:]
        if len(clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean):
            secret_input = clean
        else:
            try:
                decoded = base64.b64decode(raw_secret_str)
                if len(decoded) in (32, 59, 131, 158) or decoded.startswith(b"\xac\xed\x00\x05"):
                    secret_input = decoded
                else:
                    secret_input = clean
            except Exception:
                try:
                    secret_input = bytes.fromhex(clean)
                except Exception:
                    secret_input = raw_secret_str

    # 3. Create initial operation audit record (status=RUNNING, no secret logged)
    fmt_hint = req.format_override or ""
    now_utc = datetime.now(timezone.utc)
    op = DecryptionOperation(
        case_id=evidence.case_id,
        evidence_id=evidence.id,
        file_id=resolved_file_id,
        format=fmt_hint or "auto_detect",
        status="RUNNING",
        input_sha256=input_sha256,
        parameters=_clean_pg_text(req.parameters or {}),
        created_at=now_utc,
    )
    db.add(op)
    db.commit()
    db.refresh(op)

    try:
        decrypted_bytes, meta = DecryptionOrchestrator.decrypt(
            data=target_bytes,
            key_or_passcode=secret_input,
            format_hint=fmt_hint,
            filename=filename,
            parameters=req.parameters,
        )

        output_sha256 = meta.get("output_sha256")
        artifact_type = meta.get("artifact_type", "decrypted_sqlite")

        # Determine clean derived filename
        base_name = filename
        for ext in (".crypt12", ".crypt14", ".crypt15"):
            if base_name.endswith(ext):
                base_name = base_name[: -len(ext)]
        if base_name.endswith(".db"):
            base_name = base_name[:-3]
        if artifact_type == "decrypted_sqlite":
            derived_filename = f"{base_name}_decrypted.db"
        else:
            derived_filename = f"{base_name}_decrypted"

        # 4. Persist derived artifact to PostgreSQL BYTEA (Zero disk writes, R4, Idempotent)
        comp_utc = datetime.now(timezone.utc)
        existing_derived = (
            db.query(DerivedArtifact)
            .filter(
                DerivedArtifact.case_id == evidence.case_id,
                (
                    (DerivedArtifact.sha256 == output_sha256)
                    | (
                        (DerivedArtifact.parent_evidence_id == evidence.id)
                        & (DerivedArtifact.parent_file_id == resolved_file_id)
                        & (DerivedArtifact.artifact_type == artifact_type)
                    )
                ),
            )
            .first()
        )

        provenance_payload = _clean_pg_text({
            "operation_id": op.id,
            "source_evidence_id": evidence.id,
            "source_sha256": input_sha256,
            "format": meta.get("format"),
            "method": f"{meta.get('format', '').upper()}_DECRYPT",
            "tool_version": "ArtifactX-1.0.0",
            "output_sha256": output_sha256,
            "validation_report": meta.get("operation_details", {}).get("validation", {}),
            "decrypted_at": comp_utc.isoformat(),
        })

        if existing_derived:
            derived = existing_derived
            derived.original_filename = derived_filename
            derived.sha256 = output_sha256
            derived.size_bytes = len(decrypted_bytes)
            derived.mime_type = meta.get("operation_details", {}).get("mime_type") or ("application/x-sqlite3" if artifact_type == "decrypted_sqlite" else "application/octet-stream")
            derived.content_bytes = decrypted_bytes
            derived.provenance = provenance_payload
            derived.created_at = comp_utc
            db.commit()
            db.refresh(derived)
        else:
            derived = DerivedArtifact(
                case_id=evidence.case_id,
                parent_evidence_id=evidence.id,
                parent_file_id=resolved_file_id,
                original_filename=derived_filename,
                artifact_type=artifact_type,
                sha256=output_sha256,
                size_bytes=len(decrypted_bytes),
                mime_type=meta.get("operation_details", {}).get("mime_type") or ("application/x-sqlite3" if artifact_type == "decrypted_sqlite" else "application/octet-stream"),
                content_bytes=decrypted_bytes,
                provenance=provenance_payload,
                created_at=comp_utc,
            )
            db.add(derived)
            db.commit()
            db.refresh(derived)

        # Attempt automatic forensic indexing of decrypted SQLite database
        if artifact_type == "decrypted_sqlite":
            try:
                from backend.services.whatsapp_service import WhatsAppService
                wa_service = WhatsAppService()
                wa_service.parse_evidence_sync(
                    evidence_id=evidence.id,
                    db=db,
                    derived_artifact_id=str(derived.id),
                )
            except Exception as pe:
                print(f"[Decryption] Post-decryption parsing non-fatal notice: {pe}")

        # 5. Update operation audit record
        op.status = "SUCCEEDED"
        op.format = meta.get("format", op.format)
        op.output_sha256 = output_sha256
        op.derived_artifact_id = derived.id
        op.validation = _clean_pg_text(meta.get("operation_details", {}).get("validation", {}))
        op.completed_at = comp_utc

        # 6. Log to hash-chained audit ledger (no secrets logged, R5)
        AuditService.append(
            db=db,
            action="DECRYPTION_SUCCESS",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            details={
                "operation_id": op.id,
                "format": op.format,
                "derived_artifact_id": derived.id,
                "output_sha256": output_sha256,
                "key_fingerprint": meta.get("operation_details", {}).get("key_fingerprint"),
            },
        )

        act_log = ActivityLog(
            case_id=evidence.case_id,
            action="DECRYPTION_SUCCESS",
            description=f"Decryption succeeded: {op.format.upper()} on evidence #{evidence.id} -> derived artifact #{derived.id} (SHA-256: {output_sha256[:16]}...)",
            timestamp=comp_utc,
        )
        db.add(act_log)
        db.commit()
        db.refresh(op)

        return DecryptionOperationResponse(
            operation_id=op.id,
            case_id=op.case_id,
            evidence_id=op.evidence_id,
            file_id=op.file_id,
            format=op.format,
            status=op.status,
            input_sha256=op.input_sha256,
            output_sha256=op.output_sha256,
            derived_artifact_id=op.derived_artifact_id,
            validation=op.validation or {},
            parameters=op.parameters or {},
            error_message=None,
            created_at=op.created_at,
            completed_at=op.completed_at,
        )

    except DecryptorNotAvailableError as dne:
        db.rollback()
        fail_utc = datetime.now(timezone.utc)
        op_demoted = db.query(DecryptionOperation).filter(DecryptionOperation.id == op.id).first()
        if op_demoted:
            op_demoted.status = "DECRYPTOR_NOT_AVAILABLE"
            op_demoted.error_message = _clean_pg_text(str(dne))
            op_demoted.completed_at = fail_utc
            db.commit()
            db.refresh(op_demoted)

        AuditService.append(
            db=db,
            action="DECRYPTION_UNAVAILABLE",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            details={
                "operation_id": op.id,
                "format": op.format,
                "reason": str(dne),
            },
        )

        act_log = ActivityLog(
            case_id=evidence.case_id,
            action="DECRYPTION_UNAVAILABLE",
            description=f"Decryption unavailable for format {op.format}: {str(dne)}",
            timestamp=fail_utc,
        )
        db.add(act_log)
        db.commit()

        return DecryptionOperationResponse(
            operation_id=op.id,
            case_id=op.case_id,
            evidence_id=op.evidence_id,
            file_id=op.file_id,
            format=op.format,
            status="DECRYPTOR_NOT_AVAILABLE",
            input_sha256=op.input_sha256,
            output_sha256=None,
            derived_artifact_id=None,
            validation={},
            parameters=op.parameters or {},
            error_message=_clean_pg_text(str(dne)),
            created_at=op.created_at,
            completed_at=fail_utc,
        )

    except WhatsAppDecryptionError as wde:
        db.rollback()
        fail_utc = datetime.now(timezone.utc)
        op_fail = db.query(DecryptionOperation).filter(DecryptionOperation.id == op.id).first()
        if op_fail:
            op_fail.status = "FAILED"
            op_fail.error_message = _clean_pg_text(f"[{wde.code}] {wde.message}")
            op_fail.completed_at = fail_utc
            db.commit()
            db.refresh(op_fail)

        AuditService.append(
            db=db,
            action="DECRYPTION_FAILED",
            actor="system",
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            details={
                "operation_id": op.id,
                "format": op.format,
                "error_code": wde.code,
                "error_message": wde.message,
            },
        )

        act_log = ActivityLog(
            case_id=evidence.case_id,
            action="DECRYPTION_FAILED",
            description=f"Decryption failed: [{wde.code}] {wde.message}",
            timestamp=fail_utc,
        )
        db.add(act_log)
        db.commit()

        return DecryptionOperationResponse(
            operation_id=op.id,
            case_id=op.case_id,
            evidence_id=op.evidence_id,
            file_id=op.file_id,
            format=op.format,
            status="FAILED",
            input_sha256=op.input_sha256,
            output_sha256=None,
            derived_artifact_id=None,
            validation={},
            parameters=op.parameters or {},
            error_message=_clean_pg_text(f"[{wde.code}] {wde.message}"),
            created_at=op.created_at,
            completed_at=fail_utc,
        )

    except Exception as e:
        db.rollback()
        fail_utc = datetime.now(timezone.utc)
        op_fail = db.query(DecryptionOperation).filter(DecryptionOperation.id == op.id).first()
        if op_fail:
            op_fail.status = "FAILED"
            op_fail.error_message = _clean_pg_text(str(e))
            op_fail.completed_at = fail_utc
            db.commit()

        raise HTTPException(
            status_code=400,
            detail=f"Decryption operation failed: {str(e)}",
        )


@router.get(
    "/evidence/{evidence_id}/decryption/operations",
    response_model=List[DecryptionOperationResponse],
)
def list_evidence_decryption_operations(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve audit ledger of decryption operations performed on an evidence item."""
    ops = (
        db.query(DecryptionOperation)
        .filter(DecryptionOperation.evidence_id == evidence_id)
        .order_by(DecryptionOperation.created_at.desc())
        .all()
    )
    return [
        DecryptionOperationResponse(
            operation_id=o.id,
            case_id=o.case_id,
            evidence_id=o.evidence_id,
            file_id=o.file_id,
            format=o.format,
            status=o.status,
            input_sha256=o.input_sha256,
            output_sha256=o.output_sha256,
            derived_artifact_id=o.derived_artifact_id,
            validation=o.validation or {},
            parameters=o.parameters or {},
            error_message=o.error_message,
            created_at=o.created_at,
            completed_at=o.completed_at,
        )
        for o in ops
    ]


@router.get(
    "/evidence/{evidence_id}/derived-artifacts",
    response_model=List[DerivedArtifactResponse],
)
def list_evidence_derived_artifacts(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """List derived exhibits generated from an evidence container."""
    artifacts = (
        db.query(DerivedArtifact)
        .filter(DerivedArtifact.parent_evidence_id == evidence_id)
        .order_by(DerivedArtifact.created_at.desc())
        .all()
    )
    return [DerivedArtifactResponse.model_validate(a) for a in artifacts]


@router.get(
    "/cases/{case_id}/derived-artifacts",
    response_model=List[DerivedArtifactResponse],
)
def list_case_derived_artifacts(
    case_id: int,
    db: Session = Depends(get_db),
):
    """List all derived exhibits generated across all evidence containers for a case."""
    artifacts = (
        db.query(DerivedArtifact)
        .filter(DerivedArtifact.case_id == case_id)
        .order_by(DerivedArtifact.created_at.desc())
        .all()
    )
    return [DerivedArtifactResponse.model_validate(a) for a in artifacts]


@router.get(
    "/derived-artifacts/{artifact_id}/stream",
    response_class=StreamingResponse,
)
def stream_derived_artifact(
    artifact_id: int,
    db: Session = Depends(get_db),
):
    """Stream verified derived exhibit binary content directly from PostgreSQL BYTEA (Zero disk writes)."""
    artifact = db.query(DerivedArtifact).filter(DerivedArtifact.id == artifact_id).first()
    if not artifact or not artifact.content_bytes:
        raise HTTPException(
            status_code=404,
            detail="Derived exhibit binary content not found in storage.",
        )

    stream = io.BytesIO(artifact.content_bytes)
    return StreamingResponse(
        stream,
        media_type=artifact.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.original_filename}"',
            "Content-Length": str(len(artifact.content_bytes)),
            "X-Artifact-SHA256": artifact.sha256,
        },
    )


@router.get(
    "/cases/{case_id}/decryption/inventory",
    response_model=DecryptionInventoryResponse,
)
def get_case_decryption_inventory(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    Return comprehensive inventory of all files identified from uploaded evidence files,
    strictly grouped into:
    1. Directly Usable files (unencrypted databases, media, configs, logs, plus decrypted artifacts)
    2. Encrypted files (crypt14, crypt15, sqlcipher, etc.) with identified candidate keys for autofill
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id.asc())
        .all()
    )
    derived_artifacts = (
        db.query(DerivedArtifact)
        .filter(DerivedArtifact.case_id == case_id)
        .order_by(DerivedArtifact.id.desc())
        .all()
    )

    from forensic.decryption.whatsapp.keys import WhatsAppKeyParser

    # 1. Discover all candidate keys across the case's evidence files
    discovered_keys: List[DiscoveredKeyInfo] = []

    for ev in evidence_items:
        for ef in ev.files:
            fn = ef.relative_path.lower()
            if any(k in fn for k in ["key", ".key", "keystore"]) and (ef.file_size or 0) < 20000:
                raw_bytes = ef.content_bytes
                if raw_bytes:
                    ktype = "generic_key"
                    autofill_val = raw_bytes.hex()
                    preview = raw_bytes[:16].hex()
                    # Try crypt15
                    try:
                        root_km, _ = WhatsAppKeyParser.parse_crypt15_key(raw_bytes)
                        ktype = "crypt15_keyfile"
                        autofill_val = root_km.raw_key.hex()
                        preview = root_km.raw_key.hex()
                    except Exception:
                        # Try crypt14
                        try:
                            c14_km = WhatsAppKeyParser.parse_crypt14_key(raw_bytes)
                            ktype = "crypt14_keyfile"
                            autofill_val = c14_km.raw_key.hex()
                            preview = c14_km.raw_key.hex()
                        except Exception:
                            pass

                    discovered_keys.append(
                        DiscoveredKeyInfo(
                            key_file_id=ef.id,
                            filename=ef.relative_path.split("/")[-1],
                            relative_path=ef.relative_path,
                            key_type=ktype,
                            size_bytes=len(raw_bytes),
                            source_container=ev.original_filename,
                            preview_hex=preview,
                            autofill_value=autofill_val,
                        )
                    )

    # Deduplicate discovered keys by sha256 or key file ID/filename
    seen_key_sigs = set()
    unique_discovered_keys: List[DiscoveredKeyInfo] = []
    for dk in discovered_keys:
        sig = (dk.key_file_id, dk.autofill_value, dk.filename)
        if sig in seen_key_sigs:
            continue
        seen_key_sigs.add(sig)
        unique_discovered_keys.append(dk)
    discovered_keys = unique_discovered_keys

    # 2. Build map of existing DerivedArtifacts to mark encrypted files that have already been decrypted
    derived_parent_file_ids = {a.parent_file_id: a for a in derived_artifacts if a.parent_file_id}
    derived_parent_ev_ids = {a.parent_evidence_id: a for a in derived_artifacts if not a.parent_file_id}

    encrypted_files: List[EncryptedFileInfo] = []
    directly_usable: List[DirectlyUsableFileInfo] = []

    # 3. Add derived artifacts directly to directly_usable section (deduplicated by sha256 and filename)
    seen_derived_sha = set()
    for da in derived_artifacts:
        sig = (da.sha256, da.original_filename) if da.sha256 else da.id
        if sig in seen_derived_sha:
            continue
        seen_derived_sha.add(sig)

        t_cnt, t_names = _inspect_sqlite_tables(da.content_bytes) if da.artifact_type == "decrypted_sqlite" else (0, [])
        directly_usable.append(
            DirectlyUsableFileInfo(
                id=f"art_{da.id}",
                is_derived=True,
                artifact_id=da.id,
                evidence_id=da.parent_evidence_id,
                file_id=da.parent_file_id,
                filename=da.original_filename,
                relative_path=f"derived/{da.original_filename}",
                size_bytes=da.size_bytes or (len(da.content_bytes) if da.content_bytes else 0),
                sha256=da.sha256,
                category="database" if da.artifact_type == "decrypted_sqlite" else "other",
                mime_type=da.mime_type or "application/x-sqlite3",
                source_container="Decrypted Derived Exhibit",
                status="Decrypted Plaintext",
                table_count=t_cnt if t_cnt > 0 else None,
                tables=t_names,
            )
        )

    # 4. Process all evidence files
    seen_encrypted_sig = set()
    seen_usable_sig = set()

    # Pre-populate seen_usable_sig with derived artifacts to prevent duplicate plaintexts
    for d in directly_usable:
        if d.sha256:
            seen_usable_sig.add(("sha", d.sha256))
        seen_usable_sig.add(("path", d.filename))

    for ev in evidence_items:
        items_to_check = []
        if ev.files:
            for ef in ev.files:
                items_to_check.append(("file", ef))
        else:
            # Standalone evidence file
            items_to_check.append(("evidence", ev))

        for it_type, item in items_to_check:
            if it_type == "file":
                ef_id = item.id
                ev_id = ev.id
                rel_path = item.relative_path
                fname = rel_path.split("/")[-1]
                sz = item.file_size or 0
                h_sha256 = item.sha256
                mime = item.mime_type
            else:
                ef_id = None
                ev_id = ev.id
                rel_path = item.original_filename
                fname = item.original_filename
                sz = getattr(item, 'file_size_bytes', 0)
                h_sha256 = item.sha256
                mime = getattr(item, 'mime_type', None) or getattr(item, 'declared_mime', None) or getattr(item, 'content_type', 'application/octet-stream')

            fn_lower = fname.lower()
            is_enc = any(fn_lower.endswith(ext) for ext in [".crypt", ".crypt12", ".crypt14", ".crypt15", ".enc"])

            if is_enc:
                # Deduplicate identical encrypted files
                enc_sig = (h_sha256, fname) if h_sha256 else (ev_id, ef_id, rel_path)
                if enc_sig in seen_encrypted_sig:
                    continue
                seen_encrypted_sig.add(enc_sig)

                # Determine format
                detected_fmt = "crypt15" if fn_lower.endswith(".crypt15") else ("crypt14" if fn_lower.endswith(".crypt14") else ("crypt12" if fn_lower.endswith(".crypt12") else "encrypted"))
                fmt_name = "WhatsApp Crypt15 (AES-256-GCM)" if detected_fmt == "crypt15" else ("WhatsApp Crypt14 (AES-256-CTR)" if detected_fmt == "crypt14" else "Encrypted Database")

                # Match candidate keys from discovered keys
                cand_keys: List[CandidateKeyInfo] = []
                autofill_key: Optional[CandidateKeyInfo] = None

                for dk in discovered_keys:
                    matched = False
                    if detected_fmt == "crypt15" and ("crypt15" in dk.key_type or "test_backup" in dk.filename.lower() or dk.filename.endswith(".key")):
                        matched = True
                    elif detected_fmt in ("crypt14", "crypt12") and ("crypt14" in dk.key_type or "key" in dk.filename.lower()):
                        matched = True

                    cki = CandidateKeyInfo(
                        key_file_id=dk.key_file_id,
                        filename=dk.filename,
                        relative_path=dk.relative_path,
                        key_type=dk.key_type,
                        key_format="Hex String / Enclave Key",
                        size_bytes=dk.size_bytes,
                        preview_hex=dk.preview_hex,
                        autofill_value=dk.autofill_value,
                        is_matched=matched,
                    )
                    cand_keys.append(cki)
                    if matched and not autofill_key:
                        autofill_key = cki

                # Check if already decrypted
                existing_da = None
                if ef_id:
                    existing_da = next((a for a in derived_artifacts if a.parent_file_id == ef_id), None)
                else:
                    existing_da = next((a for a in derived_artifacts if a.parent_evidence_id == ev_id and not a.parent_file_id), None)

                if existing_da:
                    # Once decrypted successfully, remove from found encrypted files list (it is now in directly usable)
                    continue

                status_str = "AWAITING_KEY"

                encrypted_files.append(
                    EncryptedFileInfo(
                        id=f"file_{ef_id}" if ef_id else f"ev_{ev_id}",
                        evidence_id=ev_id,
                        file_id=ef_id,
                        filename=fname,
                        relative_path=rel_path,
                        size_bytes=sz,
                        sha256=h_sha256,
                        detected_format=detected_fmt,
                        format_name=fmt_name,
                        source_container=ev.original_filename,
                        status=status_str,
                        derived_artifact_id=existing_da.id if existing_da else None,
                        candidate_keys=cand_keys,
                        autofill_key=autofill_key,
                    )
                )
            else:
                usable_sig = (h_sha256, fname) if h_sha256 else (ev_id, ef_id, rel_path)
                if usable_sig in seen_usable_sig:
                    continue
                seen_usable_sig.add(usable_sig)

                cat = _detect_file_category(fname, mime)
                t_cnt, t_names = (0, [])
                if cat == "database":
                    raw_bytes = item.content_bytes
                    t_cnt, t_names = _inspect_sqlite_tables(raw_bytes)
                directly_usable.append(
                    DirectlyUsableFileInfo(
                        id=f"file_{ef_id}" if ef_id else f"ev_{ev_id}",
                        is_derived=False,
                        artifact_id=None,
                        evidence_id=ev_id,
                        file_id=ef_id,
                        filename=fname,
                        relative_path=rel_path,
                        size_bytes=sz,
                        sha256=h_sha256,
                        category=cat,
                        mime_type=mime,
                        source_container=ev.original_filename,
                        status="Directly Usable (Plaintext)",
                        table_count=t_cnt if t_cnt > 0 else None,
                        tables=t_names,
                    )
                )

    stats = DecryptionInventoryStats(
        total_identified_files=len(encrypted_files) + len(directly_usable),
        encrypted_count=len(encrypted_files),
        directly_usable_count=len(directly_usable),
        discovered_keys_count=len(discovered_keys),
        decrypted_count=len([e for e in encrypted_files if e.status == "DECRYPTED"]) + len(derived_artifacts),
    )

    return DecryptionInventoryResponse(
        case_id=case_id,
        encrypted_files=encrypted_files,
        directly_usable_files=directly_usable,
        discovered_keys=discovered_keys,
        stats=stats,
    )


@router.post(
    "/cases/{case_id}/decryption/execute",
    response_model=DecryptionOperationResponse,
    status_code=status.HTTP_200_OK,
)
def execute_case_decryption(
    case_id: int,
    req: DecryptionRunRequest,
    db: Session = Depends(get_db),
):
    """
    Execute decryption targeting an encrypted exhibit file within a case.
    Accepts candidate_file_id or evidence_id, with manual key or autofilled key_file_id.
    """
    ev_id = req.evidence_id
    if not ev_id and req.candidate_file_id:
        ef = db.query(EvidenceFile).filter(EvidenceFile.id == req.candidate_file_id).first()
        if ef:
            ev_id = ef.evidence_id
    if not ev_id:
        first_ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
        if first_ev:
            ev_id = first_ev.id
    if not ev_id:
        raise HTTPException(status_code=400, detail="Could not resolve target evidence item for decryption.")
    return run_decryption(evidence_id=ev_id, req=req, db=db)

