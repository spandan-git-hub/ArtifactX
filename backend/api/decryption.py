"""
Cryptographic Decryption API.
Provides endpoints for detecting encryption formats, executing in-memory decryption,
recording judicial operation provenance, and streaming derived artifacts from PostgreSQL BYTEA.
"""

from datetime import datetime
import io
from typing import Any, List, Optional

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
    DecryptionOperationResponse,
    DecryptionRunRequest,
    DerivedArtifactResponse,
    FormatDetectionResponse,
)
from forensic.decryption.orchestrator import DecryptionOrchestrator


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


def _get_target_bytes_and_name(
    db: Session,
    evidence_id: int,
    file_id: Optional[int] = None,
) -> tuple[bytes, str, Optional[int]]:
    """Retrieve target binary buffer from PostgreSQL BYTEA and determine filename."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found.")

    if file_id:
        ev_file = db.query(EvidenceFile).filter(
            EvidenceFile.id == file_id,
            EvidenceFile.evidence_id == evidence_id,
        ).first()
        if not ev_file:
            raise HTTPException(status_code=404, detail="Target evidence member file not found.")
        target_bytes = ev_file.content_bytes
        filename = ev_file.relative_path.split("/")[-1]
        resolved_file_id = ev_file.id
    else:
        target_bytes = evidence.content_bytes
        filename = evidence.original_filename
        resolved_file_id = None

    # Fallback if content_bytes was not populated (e.g. legacy row)
    if not target_bytes and evidence.storage_path:
        import os
        if os.path.exists(evidence.storage_path):
            with open(evidence.storage_path, "rb") as f:
                target_bytes = f.read()

    if not target_bytes:
        raise HTTPException(
            status_code=400,
            detail="Evidence binary buffer is not available in PostgreSQL BYTEA storage.",
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
    Plaintext output is stored directly in PostgreSQL BYTEA as a DerivedArtifact.
    Secrets and passcodes are never stored or exposed.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence item not found.")

    target_bytes, filename, resolved_file_id = _get_target_bytes_and_name(
        db, evidence_id, req.candidate_file_id
    )

    import hashlib
    input_sha256 = hashlib.sha256(target_bytes).hexdigest()

    # Determine secret input (key_material or passcode)
    secret_input = req.key_material or req.passcode
    if not secret_input:
        raise HTTPException(
            status_code=400,
            detail="Either key_material (WhatsApp key/passkey) or passcode (Telegram PIN) must be provided.",
        )

    # Create audit operation record
    fmt_hint = req.format_override or ""
    op = DecryptionOperation(
        case_id=evidence.case_id,
        evidence_id=evidence.id,
        file_id=resolved_file_id,
        format=fmt_hint or "auto_detect",
        status="RUNNING",
        input_sha256=input_sha256,
        parameters=_clean_pg_text(req.parameters or {}),
        created_at=datetime.utcnow(),
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
        for ext in (".crypt12", ".crypt14", ".crypt15", ".enc"):
            if base_name.endswith(ext):
                base_name = base_name[: -len(ext)]
        if not base_name.endswith(".db") and artifact_type == "decrypted_sqlite":
            derived_filename = f"{base_name}_decrypted.db"
        elif artifact_type == "decrypted_media":
            mime = meta.get("operation_details", {}).get("mime_type", "")
            ext = ".jpg" if "jpeg" in mime else (".png" if "png" in mime else (".mp4" if "mp4" in mime else ".bin"))
            derived_filename = f"{base_name}_decrypted{ext}"
        else:
            derived_filename = f"{base_name}_decrypted"

        # Persist derived artifact to PostgreSQL BYTEA (Zero disk writes)
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
            provenance=_clean_pg_text({
                "operation_id": op.id,
                "parent_sha256": input_sha256,
                "format": meta.get("format"),
                "method": f"{meta.get('format').upper()}_DECRYPT",
                "validation": meta.get("operation_details", {}).get("validation", {}),
                "decrypted_at": datetime.utcnow().isoformat(),
            }),
            created_at=datetime.utcnow(),
        )
        db.add(derived)
        db.commit()
        db.refresh(derived)

        # Update operation audit record
        op.status = "SUCCEEDED"
        op.format = meta.get("format", op.format)
        op.output_sha256 = output_sha256
        op.derived_artifact_id = derived.id
        op.validation = _clean_pg_text(meta.get("operation_details", {}).get("validation", {}))
        op.completed_at = datetime.utcnow()

        # Log to ActivityLog
        act_log = ActivityLog(
            case_id=evidence.case_id,
            action="DECRYPTION_SUCCESS",
            description=f"Decryption succeeded: {op.format.upper()} on evidence #{evidence.id} -> derived artifact #{derived.id} (SHA-256: {output_sha256[:16]}...)",
            timestamp=datetime.utcnow(),
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

    except Exception as e:
        db.rollback()
        op_fail = db.query(DecryptionOperation).filter(DecryptionOperation.id == op.id).first()
        if op_fail:
            op_fail.status = "FAILED"
            op_fail.error_message = _clean_pg_text(str(e))
            op_fail.completed_at = datetime.utcnow()
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
    return [DerivedArtifactResponse.from_orm(a) for a in artifacts]


@router.get(
    "/cases/{case_id}/derived-artifacts",
    response_model=List[DerivedArtifactResponse],
)
def list_case_derived_artifacts(
    case_id: int,
    db: Session = Depends(get_db),
):
    """List all derived forensic exhibits belonging to a case."""
    artifacts = (
        db.query(DerivedArtifact)
        .filter(DerivedArtifact.case_id == case_id)
        .order_by(DerivedArtifact.created_at.desc())
        .all()
    )
    return [DerivedArtifactResponse.from_orm(a) for a in artifacts]


@router.get("/cases/{case_id}/derived-artifacts/{artifact_id}/stream")
def stream_derived_artifact(
    case_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
):
    """
    Stream derived artifact binary content directly from PostgreSQL BYTEA.
    Zero disk storage: streams directly to the requesting client.
    """
    artifact = (
        db.query(DerivedArtifact)
        .filter(
            DerivedArtifact.id == artifact_id,
            DerivedArtifact.case_id == case_id,
        )
        .first()
    )
    if not artifact or not artifact.content_bytes:
        raise HTTPException(status_code=404, detail="Derived artifact or binary bytes not found.")

    stream = io.BytesIO(artifact.content_bytes)
    media_type = artifact.mime_type or "application/octet-stream"

    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{artifact.original_filename}"',
            "X-Artifact-SHA256": artifact.sha256,
            "Content-Length": str(artifact.size_bytes),
        },
    )
