"""Evidence management API endpoints."""

import io
import logging
import mimetypes
import re
import traceback
import uuid
import zipfile
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile, File, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, load_only

from backend.app.config import settings, UPLOADS_DIR
from backend.app.database import get_db
from backend.models.models import ActivityLog, Case, Evidence, EvidenceFile
from backend.utils.file_storage import (
    save_upload,
    delete_file,
    resolve_evidence_path,
    resolve_evidence_file_path,
    create_extract_dir,
    save_extracted_members,
)
from backend.utils.hashing import (
    IncrementalHasher,
    compute_sha256_bytes,
    compute_multi_hashes_bytes,
)
from backend.utils.zip_safety import (
    ZipLimitExceeded,
    extract_zip_safe_in_memory,
    SafeZipMember,
)
from backend.schemas.evidence import EvidenceRead
from backend.services.audit_service import AuditService
from backend.services.integrity_service import (
    ensure_integrity,
    EvidenceIntegrityError,
    LegacyUnverifiableError,
)
from backend.services.log_service import get_log_service
from forensic.detectors.format_detector import detect_format
from forensic.media.metadata import extract_image_metadata
from forensic.common.sqlite import open_sqlite

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_UPLOAD_EXTENSIONS = {
    ".zip",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".3gp",
    ".3g2",
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".m4a",
    ".wma",
    ".aiff",
    ".alac",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
    ".rtf",
    ".vid",
}


def _is_zip_file(filename: str, content_type: Optional[str]) -> bool:
    """Heuristic to check if file is a ZIP."""
    if content_type and "zip" in content_type.lower():
        return True
    if filename and filename.lower().endswith(".zip"):
        return True
    return False


def _safe_filename(filename: Optional[str]) -> str:
    """Return a filesystem-safe basename for a client-provided filename."""
    raw_name = Path(filename or "unnamed").name.strip()
    if not raw_name or raw_name in {".", ".."}:
        return "unnamed"

    safe_chars = []
    for char in raw_name:
        if char.isalnum() or char in {".", "-", "_"}:
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    return "".join(safe_chars)[:255] or "unnamed"


def _validate_supported_upload(filename: Optional[str], content_type: Optional[str]) -> None:
    """Reject files this endpoint does not know how to inventory/analyze."""
    safe_name = _safe_filename(filename)
    extension = Path(safe_name).suffix.lower()

    if extension in SUPPORTED_UPLOAD_EXTENSIONS:
        return
    if content_type and (
        content_type.startswith("image/")
        or content_type.startswith("video/")
        or content_type.startswith("audio/")
        or content_type in {"application/zip", "application/x-sqlite3", "application/octet-stream"}
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported evidence file type: {extension or content_type or 'unknown'}",
    )


def _media_type_from_mime(mime_type: Optional[str]) -> Optional[str]:
    if not mime_type:
        return None
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    return None


def _safe_zip_member_path(filename: str) -> Path:
    """Validate and normalize a ZIP member path before extraction."""
    member_path = Path(filename)
    if member_path.is_absolute() or any(part in {"", ".", ".."} for part in member_path.parts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsafe ZIP member path: {filename}",
        )
    return member_path


def _extract_zip_in_memory(zip_data: bytes) -> List[dict]:
    """Extract ZIP archive in memory, returning list of member file info.
    Guarantees zero files written to host filesystem.
    Each dict contains: relative_path, size, sha256, md5, sha1, mime_type, content_bytes.
    """
    extracted_info = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            bad_member = zf.testzip()
            if bad_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupt ZIP member: {bad_member}",
                )

            for info in zf.infolist():
                if info.is_dir():
                    continue

                relative_path = _safe_zip_member_path(info.filename)
                rel_str = str(relative_path).replace("\\", "/")
                if rel_str.startswith("../") or "/../" in rel_str or rel_str.startswith("/"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsafe ZIP member path: {info.filename}",
                    )

                with zf.open(info) as source:
                    member_bytes = source.read()

                file_hashes = compute_multi_hashes_bytes(member_bytes)
                mime_type, _ = mimetypes.guess_type(rel_str)
                extracted_info.append(
                    {
                        "relative_path": rel_str,
                        "size": len(member_bytes),
                        "sha256": file_hashes["sha256"],
                        "md5": file_hashes["md5"],
                        "sha1": file_hashes["sha1"],
                        "mime_type": mime_type,
                        "content_bytes": member_bytes,
                    }
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive",
        ) from exc
    return extracted_info


def _evidence_to_response(evidence: Evidence) -> dict:
    """Serialize Evidence explicitly so response validation cannot hit SQLAlchemy metadata."""
    meta = evidence.metadata_ or {}
    return {
        "id": evidence.id,
        "case_id": evidence.case_id,
        "original_filename": evidence.original_filename,
        "storage_path": evidence.storage_path,
        "sha256": evidence.sha256,
        "sha512": getattr(evidence, "sha512", None) or meta.get("sha512"),
        "md5": getattr(evidence, "md5", None) or meta.get("md5"),
        "sha1": getattr(evidence, "sha1", None) or meta.get("sha1"),
        "content_type": evidence.content_type,
        "declared_mime": getattr(evidence, "declared_mime", None),
        "detected_format": getattr(evidence, "detected_format", None),
        "uploader": getattr(evidence, "uploader", None),
        "evidence_type": evidence.evidence_type,
        "metadata": meta,
        "extracted_path": evidence.extracted_path,
        "integrity_state": getattr(evidence, "integrity_state", "OK") or "OK",
        "acquisition_method": getattr(evidence, "acquisition_method", None),
        "device_make_model": getattr(evidence, "device_make_model", None),
        "device_os_version": getattr(evidence, "device_os_version", None),
        "app_version": getattr(evidence, "app_version", None),
        "acquisition_time_utc": getattr(evidence, "acquisition_time_utc", None),
        "acquired_by": getattr(evidence, "acquired_by", None),
        "acquisition_hash_claimed": getattr(evidence, "acquisition_hash_claimed", None),
        "acquisition_hash_algorithm": getattr(evidence, "acquisition_hash_algorithm", None),
        "claimed_vs_computed": getattr(evidence, "claimed_vs_computed", "NOT_PROVIDED") or "NOT_PROVIDED",
        "uploaded_at": evidence.uploaded_at,
        "analyzed_at": evidence.analyzed_at,
    }


def _process_and_store_evidence(
    db: Session,
    case_id: int,
    filename: str,
    file_bytes: bytes,
    declared_content_type: Optional[str] = None,
    uploader: Optional[str] = "system",
    acquisition_metadata: Optional[dict] = None,
) -> dict:
    """Shared core pipeline for in-memory evidence hashing, format detection, ZIP safety, and audit ingestion."""
    safe_name = _safe_filename(filename)
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)",
        )

    # 1. Compute multi-hashes in one incremental pass (B5.1)
    upload_hashes = compute_multi_hashes_bytes(file_bytes)
    sha256 = upload_hashes["sha256"]
    sha512 = upload_hashes["sha512"]
    md5 = upload_hashes["md5"]
    sha1 = upload_hashes["sha1"]

    # 2. Signature-based format detection (B5.4)
    detection = detect_format(file_bytes, safe_name)
    detected_format = detection.format

    case = db.query(Case).filter(Case.id == case_id).first()
    case_number_str = (case.case_number if case and case.case_number else f"case_{case_id}")
    case_folder = re.sub(r'[^\w\-.]', '_', str(case_number_str))

    # 3. ZIP archive safety checks (B5.1, R12)
    is_zip = (detected_format == "ZIP") or _is_zip_file(safe_name, declared_content_type)
    evidence_type = "zip" if is_zip else "file"
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"

    # Save uploaded file to disk in uploads/<case_folder>/ directory (never committed to PostgreSQL BYTEA)
    file_disk_path = save_upload(stored_name, file_bytes, subfolder=case_folder)
    storage_path = str(file_disk_path.resolve())

    extracted_files: List[SafeZipMember] = []
    evidence_integrity_state = "OK"
    extracted_path: Optional[str] = None

    if is_zip:
        try:
            extracted_files = extract_zip_safe_in_memory(file_bytes)
            # Save extracted ZIP member files to disk in uploads/<case_folder>/extract_<uuid>/
            extract_dir = create_extract_dir(subfolder=case_folder)
            extracted_path = str(extract_dir.resolve())
            save_extracted_members(extract_dir, extracted_files)

        except ZipLimitExceeded as zle:
            evidence_integrity_state = "ARCHIVE_REJECTED"
            AuditService.append(
                db=db,
                action="ARCHIVE_SAFETY_VIOLATION",
                actor=uploader or "system",
                case_id=case_id,
                details={
                    "filename": safe_name,
                    "reason": zle.reason,
                    "error": str(zle),
                },
            )

    # 4. Acquisition metadata verification (B5.2)
    acq_meta = acquisition_metadata or {}
    claimed_hash = acq_meta.get("acquisition_hash_claimed")
    claimed_algo = (acq_meta.get("acquisition_hash_algorithm") or "sha256").lower()

    if claimed_hash:
        computed_for_claimed = upload_hashes.get(claimed_algo, sha256)
        if computed_for_claimed.lower() == claimed_hash.lower():
            claimed_vs_computed = "MATCH"
        else:
            claimed_vs_computed = "MISMATCH"
            AuditService.append(
                db=db,
                action="ACQUISITION_HASH_MISMATCH",
                actor=uploader or "system",
                case_id=case_id,
                details={
                    "filename": safe_name,
                    "algorithm": claimed_algo,
                    "claimed": claimed_hash,
                    "computed": computed_for_claimed,
                },
            )
    else:
        claimed_vs_computed = "NOT_PROVIDED"

    evidence_metadata = {
        "original_content_type": declared_content_type,
        "upload_size": file_size,
        "is_zip": is_zip,
        "original_filename": filename or "unnamed",
        "stored_filename": stored_name,
        "case_number": case_number_str,
        "case_folder": case_folder,
        "sha512": sha512,
        "md5": md5,
        "sha1": sha1,
        "storage_mode": "disk_file",
        "storage_path": storage_path,
        "detection": detection.to_dict(),
    }

    evidence = Evidence(
        case_id=case_id,
        original_filename=safe_name,
        storage_path=storage_path,
        sha256=sha256,
        sha512=sha512,
        md5=md5,
        sha1=sha1,
        content_type=declared_content_type,
        declared_mime=declared_content_type,
        detected_format=detected_format,
        uploader=uploader,
        evidence_type=evidence_type,
        metadata_=evidence_metadata,
        content_bytes=None,  # Stored on disk in uploads/<case_folder>/ to prevent PostgreSQL BYTEA latency and bloat
        _content_bytes=None,
        integrity_state=evidence_integrity_state,
        extracted_path=extracted_path,
        acquisition_method=acq_meta.get("acquisition_method"),
        device_make_model=acq_meta.get("device_make_model"),
        device_os_version=acq_meta.get("device_os_version"),
        app_version=acq_meta.get("app_version"),
        acquisition_time_utc=acq_meta.get("acquisition_time_utc"),
        acquired_by=acq_meta.get("acquired_by"),
        acquisition_hash_claimed=claimed_hash,
        acquisition_hash_algorithm=claimed_algo if claimed_hash else None,
        claimed_vs_computed=claimed_vs_computed,
    )
    db.add(evidence)
    db.flush()

    if is_zip and evidence_integrity_state != "ARCHIVE_REJECTED":
        for member in extracted_files:
            file_meta = {
                "size": member.size,
                "mime_type": member.mime_type,
                "sha512": member.sha512,
                "md5": member.md5,
                "sha1": member.sha1,
                "parent_sha256": sha256,
                "storage_mode": "disk_file",
                "original_filename": member.original_filename,
            }
            media_type = _media_type_from_mime(member.mime_type)
            evidence_file = EvidenceFile(
                evidence_id=evidence.id,
                relative_path=member.normalized_path,
                sha256=member.sha256,
                sha512=member.sha512,
                md5=member.md5,
                sha1=member.sha1,
                file_size=member.size,
                mime_type=member.mime_type,
                metadata_=file_meta,
                content_bytes=None,  # Saved on disk in extract_dir in uploads/<case_folder>/
                _content_bytes=None,
                is_media=media_type is not None,
                media_type=media_type,
            )
            db.add(evidence_file)
        db.flush()

    # 5. Append-only cryptographic audit chain entry (B5.5, R3)
    AuditService.append(
        db=db,
        action="INGEST",
        actor=uploader or "system",
        case_id=case_id,
        evidence_id=evidence.id,
        details={
            "filename": safe_name,
            "sha256": sha256,
            "size": file_size,
            "detected_format": detected_format,
            "claimed_vs_computed": claimed_vs_computed,
            "integrity_state": evidence_integrity_state,
        },
    )

    db.add(ActivityLog(
        case_id=case_id,
        action="upload_evidence",
        description=f"Evidence uploaded: {evidence.original_filename} (SHA-256: {evidence.sha256[:8]}...)",
    ))
    db.commit()
    db.refresh(evidence)

    # Auto-trigger forensic parsers on uploaded evidence
    try:
        from backend.services.whatsapp_service import WhatsAppService
        from backend.services.telegram_service import TelegramService
        WhatsAppService().analyze_evidence_sync(evidence.id, db)
        TelegramService().analyze_evidence_sync(evidence.id, db)
    except Exception as exc:
        logger.warning("Auto-analysis on upload encountered non-fatal error: %s", exc)

    return {
        "id": evidence.id,
        "filename": evidence.original_filename,
        "sha256": evidence.sha256,
        "sha512": sha512,
        "md5": md5,
        "sha1": sha1,
        "size": file_size,
        "evidence_type": evidence.evidence_type,
        "detected_format": detected_format,
        "claimed_vs_computed": claimed_vs_computed,
        "integrity_state": evidence.integrity_state,
        "is_zip": is_zip,
        "extracted_files_count": len(extracted_files) if is_zip else 0,
    }


@router.put("/upload-stream", status_code=status.HTTP_201_CREATED)
async def upload_evidence_stream(
    request: Request,
    case_id: Optional[int] = Query(None),
    x_case_id: Optional[int] = Header(None, alias="X-Case-ID"),
    filename: Optional[str] = Query(None),
    x_original_filename: Optional[str] = Header(None, alias="X-Original-Filename"),
    x_declared_mime: Optional[str] = Header(None, alias="X-Declared-Mime"),
    x_acquisition_method: Optional[str] = Header(None, alias="X-Acquisition-Method"),
    x_device_make_model: Optional[str] = Header(None, alias="X-Device-Make-Model"),
    x_device_os_version: Optional[str] = Header(None, alias="X-Device-Os-Version"),
    x_app_version: Optional[str] = Header(None, alias="X-App-Version"),
    x_acquired_by: Optional[str] = Header(None, alias="X-Acquired-By"),
    x_acquisition_hash_claimed: Optional[str] = Header(None, alias="X-Acquisition-Hash-Claimed"),
    x_acquisition_hash_algorithm: Optional[str] = Header(None, alias="X-Acquisition-Hash-Algorithm"),
    x_uploader: Optional[str] = Header(None, alias="X-Uploader"),
    db: Session = Depends(get_db),
):
    """
    Streaming upload endpoint for zero-spool in-memory ingestion (B5.1, DEC-012).
    Enforces MAX_UPLOAD_SIZE while streaming (HTTP 413 if exceeded).
    """
    target_case_id = case_id or x_case_id
    if not target_case_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required case_id")

    case = db.query(Case).filter(Case.id == target_case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {target_case_id} not found")

    target_name = filename or x_original_filename or "evidence.bin"
    safe_name = _safe_filename(target_name)

    # Read stream incrementally and enforce ceiling
    max_size = settings.max_upload_size
    chunks = []
    total_bytes = 0

    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > max_size:
            AuditService.append(
                db=db,
                action="INGEST_REJECTED_TOO_LARGE",
                actor=x_uploader or "system",
                case_id=target_case_id,
                details={"filename": safe_name, "bytes_read": total_bytes, "limit": max_size},
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded evidence exceeded maximum allowed size of {max_size} bytes ({max_size // (1024*1024)} MiB)",
            )
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes)")

    acq_meta = {
        "acquisition_method": x_acquisition_method,
        "device_make_model": x_device_make_model,
        "device_os_version": x_device_os_version,
        "app_version": x_app_version,
        "acquired_by": x_acquired_by,
        "acquisition_hash_claimed": x_acquisition_hash_claimed,
        "acquisition_hash_algorithm": x_acquisition_hash_algorithm,
    }

    return _process_and_store_evidence(
        db=db,
        case_id=target_case_id,
        filename=safe_name,
        file_bytes=file_bytes,
        declared_content_type=x_declared_mime or request.headers.get("content-type"),
        uploader=x_uploader or "system",
        acquisition_metadata=acq_meta,
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    acquisition_method: Optional[str] = None,
    device_make_model: Optional[str] = None,
    device_os_version: Optional[str] = None,
    app_version: Optional[str] = None,
    acquired_by: Optional[str] = None,
    acquisition_hash_claimed: Optional[str] = None,
    acquisition_hash_algorithm: Optional[str] = None,
    uploader: Optional[str] = "system",
    db: Session = Depends(get_db),
):
    """Upload evidence file via multipart/form-data with streaming cap enforcement (B5.1)."""
    safe_name = _safe_filename(file.filename)

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    _validate_supported_upload(safe_name, file.content_type)

    # Read chunks while strictly enforcing upload ceiling
    max_size = settings.max_upload_size
    chunks = []
    total_bytes = 0

    while True:
        chunk = file.file.read(65536)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_size:
            AuditService.append(
                db=db,
                action="INGEST_REJECTED_TOO_LARGE",
                actor=uploader or "system",
                case_id=case_id,
                details={"filename": safe_name, "bytes_read": total_bytes, "limit": max_size},
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded evidence exceeded maximum allowed size of {max_size} bytes ({max_size // (1024*1024)} MiB)",
            )
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)",
        )

    acq_meta = {
        "acquisition_method": acquisition_method,
        "device_make_model": device_make_model,
        "device_os_version": device_os_version,
        "app_version": app_version,
        "acquired_by": acquired_by,
        "acquisition_hash_claimed": acquisition_hash_claimed,
        "acquisition_hash_algorithm": acquisition_hash_algorithm,
    }

    return _process_and_store_evidence(
        db=db,
        case_id=case_id,
        filename=safe_name,
        file_bytes=file_bytes,
        declared_content_type=file.content_type,
        uploader=uploader or "system",
        acquisition_metadata=acq_meta,
    )


@router.get("", response_model=List[EvidenceRead])
@router.get("/", response_model=List[EvidenceRead])
def list_evidences(case_id: int, db: Session = Depends(get_db)):
    """List evidences for a specific case with deferred BYTEA query optimization (R19)."""
    try:
        logger.info("Listing evidence requested case_id=%s", case_id)

        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        # Deferred BYTEA (R19, B5.1): load_only all metadata columns, excluding content_bytes
        evidences = (
            db.query(Evidence)
            .options(
                load_only(
                    Evidence.id,
                    Evidence.case_id,
                    Evidence.original_filename,
                    Evidence.storage_path,
                    Evidence.sha256,
                    Evidence.sha512,
                    Evidence.md5,
                    Evidence.sha1,
                    Evidence.content_type,
                    Evidence.declared_mime,
                    Evidence.detected_format,
                    Evidence.uploader,
                    Evidence.evidence_type,
                    Evidence.metadata_,
                    Evidence.extracted_path,
                    Evidence.integrity_state,
                    Evidence.acquisition_method,
                    Evidence.device_make_model,
                    Evidence.device_os_version,
                    Evidence.app_version,
                    Evidence.acquisition_time_utc,
                    Evidence.acquired_by,
                    Evidence.acquisition_hash_claimed,
                    Evidence.acquisition_hash_algorithm,
                    Evidence.claimed_vs_computed,
                    Evidence.uploaded_at,
                    Evidence.analyzed_at,
                )
            )
            .filter(Evidence.case_id == case_id)
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )

        return [_evidence_to_response(evidence) for evidence in evidences]
    except HTTPException:
        logger.warning(
            "Evidence list rejected case_id=%s\n%s",
            case_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Evidence list database error case_id=%s\n%s",
            case_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while listing evidence",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected evidence list error case_id=%s\n%s",
            case_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while listing evidence",
        ) from exc


@router.get("/{evidence_id}")
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    try:
        logger.info("Getting evidence requested evidence_id=%s", evidence_id)
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence {evidence_id} not found",
            )

        logger.info(
            "Evidence row loaded evidence_id=%s case_id=%s filename=%s",
            evidence.id,
            evidence.case_id,
            evidence.original_filename,
        )
        return _evidence_to_response(evidence)
    except HTTPException:
        logger.warning(
            "Evidence retrieval rejected evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Evidence retrieval database error evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving evidence",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected evidence retrieval error evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while retrieving evidence",
        ) from exc


@router.get("/{evidence_id}/files")
def list_evidence_files(evidence_id: int, db: Session = Depends(get_db)):
    """List files contained within the evidence (if ZIP)."""
    try:
        logger.info("Listing evidence files requested evidence_id=%s", evidence_id)
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence {evidence_id} not found",
            )

        logger.info("Querying evidence file rows evidence_id=%s", evidence_id)
        files = (
            db.query(EvidenceFile)
            .filter(EvidenceFile.evidence_id == evidence_id)
            .order_by(EvidenceFile.relative_path.asc())
            .all()
        )
        logger.info("Evidence file rows loaded evidence_id=%s count=%s", evidence_id, len(files))

        return [
            {
                "id": f.id,
                "relative_path": f.relative_path,
                "sha256": f.sha256,
                "size": f.file_size,
                "mime_type": f.mime_type,
                "is_media": f.is_media,
                "media_type": f.media_type,
                "metadata": f.metadata_,
            }
            for f in files
        ]
    except HTTPException:
        logger.warning(
            "Evidence files list rejected evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Evidence files list database error evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while listing evidence files",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected evidence files list error evidence_id=%s\n%s",
            evidence_id,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while listing evidence files",
        ) from exc


@router.get("/{evidence_id}/files/{file_id}")
def get_evidence_file(evidence_id: int, file_id: int, db: Session = Depends(get_db)):
    """Download a specific file from the evidence inventory."""
    try:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        evidence_file = (
            db.query(EvidenceFile)
            .filter(EvidenceFile.id == file_id, EvidenceFile.evidence_id == evidence_id)
            .first()
        )
        filename = Path(evidence_file.relative_path).name or evidence.original_filename

        # Stream directly from disk in uploads if available
        file_path = resolve_evidence_file_path(evidence_file)
        if file_path and file_path.is_file():
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type=evidence_file.mime_type or "application/octet-stream",
            )

        content_bytes = evidence_file.content_bytes
        if not content_bytes:
            raise HTTPException(status_code=404, detail="File content not available in storage (legacy unverifiable row)")

        return Response(
            content=content_bytes,
            media_type=evidence_file.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="evidence_file_retrieval_error",
            message=f"Error retrieving evidence file: {str(e)}",
            case_id=None,
            evidence_id=evidence_id,
            stack_trace=str(e.__traceback__),
            endpoint=f"/api/evidence/{evidence_id}/files/{file_id}",
            method="GET"
        )
        raise


@router.post("/{evidence_id}/verify-hashes")
def verify_evidence_hashes(evidence_id: int, db: Session = Depends(get_db)):
    """Verify in-memory evidence files against recorded cryptographic hashes (SHA-256, MD5, SHA-1)."""
    try:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")

        expected_sha256 = evidence.sha256 or ""
        expected_md5 = (evidence.metadata_ or {}).get("md5")
        expected_sha1 = (evidence.metadata_ or {}).get("sha1")

        is_legacy = (evidence.content_bytes is None) or (getattr(evidence, "integrity_state", "OK") == "LEGACY_UNVERIFIABLE")

        main_file_match = False
        actual_hashes = {}
        if is_legacy or not evidence.content_bytes:
            actual_hashes = {
                "sha256": "LEGACY_UNVERIFIABLE",
                "md5": "LEGACY_UNVERIFIABLE",
                "sha1": "LEGACY_UNVERIFIABLE"
            }
            main_file_match = False
        else:
            actual_hashes = compute_multi_hashes_bytes(evidence.content_bytes)
            sha256_match = actual_hashes["sha256"].lower() == expected_sha256.lower()
            md5_match = True if not expected_md5 else actual_hashes["md5"].lower() == expected_md5.lower()
            sha1_match = True if not expected_sha1 else actual_hashes["sha1"].lower() == expected_sha1.lower()
            main_file_match = sha256_match and md5_match and sha1_match

        # 2. Extracted files verification (if archive)
        extracted_results = []
        files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).all()
        matched_count = 0
        mismatched_count = 0

        for f in files:
            f_metadata = f.metadata_ or {}
            exp_sha256 = f.sha256 or ""
            exp_md5 = f_metadata.get("md5")
            exp_sha1 = f_metadata.get("sha1")

            f_match = False
            act_hashes = {}
            if f.content_bytes:
                act_hashes = compute_multi_hashes_bytes(f.content_bytes)
                s_match = act_hashes["sha256"].lower() == exp_sha256.lower()
                m_match = True if not exp_md5 else act_hashes["md5"].lower() == exp_md5.lower()
                sh_match = True if not exp_sha1 else act_hashes["sha1"].lower() == exp_sha1.lower()
                f_match = s_match and m_match and sh_match
            else:
                act_hashes = {
                    "sha256": "LEGACY_UNVERIFIABLE",
                    "md5": "LEGACY_UNVERIFIABLE",
                    "sha1": "LEGACY_UNVERIFIABLE"
                }
                f_match = False

            if f_match:
                matched_count += 1
            else:
                mismatched_count += 1

            extracted_results.append({
                "id": f.id,
                "relative_path": f.relative_path,
                "expected_sha256": exp_sha256,
                "actual_sha256": act_hashes.get("sha256"),
                "expected_md5": exp_md5,
                "actual_md5": act_hashes.get("md5"),
                "expected_sha1": exp_sha1,
                "actual_sha1": act_hashes.get("sha1"),
                "is_intact": f_match,
            })

        if is_legacy:
            overall_intact = False
            verification_status = "LEGACY_UNVERIFIABLE"
        else:
            overall_intact = main_file_match and (mismatched_count == 0)
            verification_status = "VERIFIED_INTACT" if overall_intact else "HASH_MISMATCH"

        # Log Activity for Chain-of-Custody (B20)
        log_service = get_log_service(db)
        log_service.log_activity(
            case_id=evidence.case_id,
            action="verify_hashes",
            description=f"Evidence '{evidence.original_filename}' cryptographic verification: {verification_status} (SHA-256: {expected_sha256[:8]}...)",
        )

        return {
            "evidence_id": evidence.id,
            "case_id": evidence.case_id,
            "filename": evidence.original_filename,
            "verification_status": verification_status,
            "integrity_state": getattr(evidence, "integrity_state", "OK") or "OK",
            "is_valid": overall_intact,
            "verified_at": datetime.utcnow().isoformat(),
            "main_file": {
                "storage_path": evidence.storage_path,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_hashes.get("sha256"),
                "expected_md5": expected_md5,
                "actual_md5": actual_hashes.get("md5"),
                "expected_sha1": expected_sha1,
                "actual_sha1": actual_hashes.get("sha1"),
                "is_intact": main_file_match,
            },
            "extracted_files_summary": {
                "total": len(files),
                "matched": matched_count,
                "mismatched": mismatched_count,
            },
            "files": extracted_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error verifying evidence hashes:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to verify evidence hashes: {str(e)}")


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Delete evidence and its associated records."""
    row = db.query(
        Evidence.case_id,
        Evidence.original_filename,
        Evidence.sha256,
        Evidence.storage_path,
        Evidence.extracted_path,
    ).filter(Evidence.id == evidence_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case_id, original_filename, sha256, storage_path, extracted_path = row
    sha_prefix = sha256[:8] if sha256 else "unknown"

    # Delete storage files and extracted directory on disk if present
    if storage_path:
        delete_file(storage_path)
    if extracted_path:
        delete_file(extracted_path)

    from backend.models.models import (
        WhatsAppMessage, WhatsAppContact, WhatsAppGroup,
        TelegramMessage, TelegramContact, TelegramGroup,
        TimelineEvent, DeletedMessage, MediaItem,
        AnalysisResult, EvidenceFile, AnalysisLog
    )

    try:
        db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(WhatsAppGroup).filter(WhatsAppGroup.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramMessage).filter(TelegramMessage.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramContact).filter(TelegramContact.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TelegramGroup).filter(TelegramGroup.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(TimelineEvent).filter(TimelineEvent.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(DeletedMessage).filter(DeletedMessage.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(MediaItem).filter(MediaItem.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(AnalysisResult).filter(AnalysisResult.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(AnalysisLog).filter(AnalysisLog.evidence_id == evidence_id).delete(synchronize_session=False)
        db.query(Evidence).filter(Evidence.id == evidence_id).delete(synchronize_session=False)

        db.commit()

        try:
            log_service = get_log_service(db)
            log_service.log_activity(
                case_id=case_id,
                action="delete_evidence",
                description=f"Evidence deleted: {original_filename} (SHA-256: {sha_prefix}...)"
            )
            db.commit()
        except Exception:
            pass

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_service = get_log_service(db)
        log_service.log_error(
            error_type="evidence_deletion_error",
            message=f"Error deleting evidence: {str(e)}",
            case_id=case_id,
            evidence_id=evidence_id,
            stack_trace=traceback.format_exc(),
            endpoint=f"/api/evidence/{evidence_id}",
            method="DELETE"
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete evidence: {str(e)}")


@router.get("/{evidence_id}/exif")
def get_evidence_exif(
    evidence_id: int,
    file_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """B21: Extract EXIF metadata (camera, specs, GPS, resolution) for evidence image files."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")

    results = []

    if file_id:
        file_row = db.query(EvidenceFile).filter(
            EvidenceFile.id == file_id,
            EvidenceFile.evidence_id == evidence_id
        ).first()
        if not file_row:
            raise HTTPException(status_code=404, detail="Requested file not found in evidence")

        target_source = file_row.content_bytes
        meta = extract_image_metadata(target_source) if target_source else {}
        results.append({
            "file_id": file_row.id,
            "relative_path": file_row.relative_path,
            "mime_type": file_row.mime_type,
            "file_size": file_row.file_size or (len(target_source) if target_source else 0),
            "metadata": meta,
        })
    else:
        # Scan image files in this evidence
        image_files = db.query(EvidenceFile).filter(
            EvidenceFile.evidence_id == evidence_id,
            EvidenceFile.is_media == True,
            EvidenceFile.media_type == "image"
        ).all()

        if image_files:
            for f in image_files:
                target_source = f.content_bytes
                meta = extract_image_metadata(target_source) if target_source else {}
                results.append({
                    "file_id": f.id,
                    "relative_path": f.relative_path,
                    "mime_type": f.mime_type,
                    "file_size": f.file_size or (len(target_source) if target_source else 0),
                    "metadata": meta,
                })
        else:
            # Check main evidence in-memory bytes if it's an image
            target_source = evidence.content_bytes
            if target_source is not None and (evidence.content_type or "").startswith("image/"):
                meta = extract_image_metadata(target_source)
                results.append({
                    "file_id": None,
                    "relative_path": evidence.original_filename,
                    "mime_type": evidence.content_type,
                    "file_size": len(target_source),
                    "metadata": meta,
                })

    return {
        "evidence_id": evidence_id,
        "case_id": evidence.case_id,
        "total_images": len(results),
        "exif_records": results,
    }


@router.get("/{evidence_id}/sqlite-inspect")
def inspect_sqlite_database(
    evidence_id: int,
    file_id: Optional[int] = None,
    table_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """B22: Raw SQLite table inspector endpoint allowing direct inspection of msgstore.db, cache4.db, etc."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")

    # 1. Locate available database files in evidence
    db_files = db.query(EvidenceFile).filter(
        EvidenceFile.evidence_id == evidence_id,
        (EvidenceFile.relative_path.ilike("%.db") |
         EvidenceFile.relative_path.ilike("%.sqlite") |
         EvidenceFile.relative_path.ilike("%.sqlite3"))
    ).all()

    available_databases = [
        {"id": f.id, "relative_path": f.relative_path, "size": f.file_size}
        for f in db_files
    ]

    db_source = None
    target_rel_path = evidence.original_filename
    selected_file_id = None

    if file_id:
        file_row = db.query(EvidenceFile).filter(
            EvidenceFile.id == file_id,
            EvidenceFile.evidence_id == evidence_id
        ).first()
        if not file_row:
            raise HTTPException(status_code=404, detail="Database file not found in evidence")
        selected_file_id = file_row.id
        target_rel_path = file_row.relative_path
        db_source = file_row.content_bytes
    elif db_files:
        # Default to first database file found
        first_db = db_files[0]
        selected_file_id = first_db.id
        target_rel_path = first_db.relative_path
        db_source = first_db.content_bytes
    else:
        # Check main in-memory evidence bytes
        db_source = evidence.content_bytes

    if not db_source:
        raise HTTPException(
            status_code=404,
            detail=f"SQLite database file content not available in storage: {target_rel_path}"
        )

    # 2. Inspect SQLite Database
    try:
        conn = open_sqlite(db_source)
        cursor = conn.cursor()

        # List tables & schemas
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC")
        raw_tables = cursor.fetchall()

        tables_meta = []
        for t_name, ddl in raw_tables:
            try:
                count_cur = conn.cursor()
                count_cur.execute(f'SELECT COUNT(*) FROM "{t_name}"')
                row_cnt = count_cur.fetchone()[0]
            except Exception:
                row_cnt = 0
            tables_meta.append({
                "name": t_name,
                "sql": ddl or "",
                "row_count": row_cnt
            })

        active_table = table_name
        if not active_table and tables_meta:
            active_table = tables_meta[0]["name"]

        columns_meta = []
        rows_data = []
        total_rows = 0

        if active_table:
            # PRAGMA table_info
            cursor.execute(f'PRAGMA table_info("{active_table}")')
            col_rows = cursor.fetchall()
            # col_rows tuple: (cid, name, type, notnull, dflt_value, pk)
            columns_meta = [
                {
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2] or "TEXT",
                    "notnull": bool(col[3]),
                    "dflt_value": col[4],
                    "pk": bool(col[5])
                }
                for col in col_rows
            ]

            # Total rows for active table
            for tm in tables_meta:
                if tm["name"] == active_table:
                    total_rows = tm["row_count"]
                    break

            # Fetch rows
            cursor.execute(f'SELECT * FROM "{active_table}" LIMIT ? OFFSET ?', (limit, offset))
            raw_rows = cursor.fetchall()

            col_names = [c["name"] for c in columns_meta]
            for r in raw_rows:
                row_dict = {}
                for idx, col_name in enumerate(col_names):
                    val = r[idx]
                    if isinstance(val, bytes):
                        try:
                            val = val.decode('utf-8', errors='ignore')
                        except Exception:
                            val = f"<BLOB {len(val)} bytes>"
                    row_dict[col_name] = val
                rows_data.append(row_dict)

        conn.close()

        return {
            "evidence_id": evidence_id,
            "file_id": selected_file_id,
            "database_name": target_rel_path,
            "available_databases": available_databases,
            "table_count": len(tables_meta),
            "tables": tables_meta,
            "selected_table": active_table,
            "columns": columns_meta,
            "rows": rows_data,
            "total_rows": total_rows,
            "limit": limit,
            "offset": offset,
        }
    except sqlite3.Error as err:
        logger.error(f"SQLite inspect error for {target_file_path}: {err}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to inspect SQLite database: {str(err)}"
        )
