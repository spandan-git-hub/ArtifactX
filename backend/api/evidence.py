"""Evidence management API endpoints."""

import io
import logging
import mimetypes
import traceback
import uuid
import zipfile
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import ActivityLog, Case, Evidence, EvidenceFile
from backend.utils.hashing import (
    compute_sha256_bytes,
    compute_multi_hashes_bytes,
)
from backend.schemas.evidence import EvidenceRead
from backend.services.log_service import get_log_service
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
        "md5": meta.get("md5"),
        "sha1": meta.get("sha1"),
        "content_type": evidence.content_type,
        "evidence_type": evidence.evidence_type,
        "metadata": meta,
        "extracted_path": evidence.extracted_path,
        "integrity_state": getattr(evidence, "integrity_state", "OK") or "OK",
        "uploaded_at": evidence.uploaded_at,
        "analyzed_at": evidence.analyzed_at,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload evidence file (ZIP or regular) for a case."""
    storage_path: Optional[Path] = None
    extract_dir: Optional[Path] = None
    extracted_files: list[dict] = []
    safe_name = _safe_filename(file.filename)

    try:
        logger.info(
            "Evidence upload requested case_id=%s filename=%s content_type=%s",
            case_id,
            file.filename,
            file.content_type,
        )

        logger.info("Validating case exists case_id=%s", case_id)
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )


        logger.info("Validating supported upload filename=%s content_type=%s", safe_name, file.content_type)
        _validate_supported_upload(safe_name, file.content_type)

        logger.info("Reading uploaded file stream into memory filename=%s", safe_name)
        file_data = file.file.read()
        file_size = len(file_data)
        logger.info("Uploaded file read complete filename=%s size=%s", safe_name, file_size)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        logger.info("Computing uploaded file multi-hashes (SHA-256, MD5, SHA-1) filename=%s size=%s", safe_name, file_size)
        upload_hashes = compute_multi_hashes_bytes(file_data)
        sha256 = upload_hashes["sha256"]
        md5 = upload_hashes["md5"]
        sha1 = upload_hashes["sha1"]
        logger.info("Computed uploaded file hashes sha256=%s md5=%s sha1=%s", sha256, md5, sha1)

        is_zip = _is_zip_file(safe_name, file.content_type)
        evidence_type = "zip" if is_zip else "file"
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        storage_path = f"db://evidence/{stored_name}"

        extracted_files = []
        if is_zip:
            logger.info("Extracting ZIP in memory filename=%s", safe_name)
            extracted_files = _extract_zip_in_memory(file_data)
            logger.info(
                "In-memory ZIP extraction complete filename=%s extracted_count=%s",
                safe_name,
                len(extracted_files),
            )

        evidence_metadata = {
            "original_content_type": file.content_type,
            "upload_size": file_size,
            "is_zip": is_zip,
            "original_filename": file.filename or "unnamed",
            "stored_filename": stored_name,
            "md5": md5,
            "sha1": sha1,
            "storage_mode": "postgres_bytea",
        }

        logger.info("Creating Evidence row case_id=%s filename=%s sha256=%s", case_id, safe_name, sha256)
        evidence = Evidence(
            case_id=case_id,
            original_filename=safe_name,
            storage_path=storage_path,
            sha256=sha256,
            content_type=file.content_type,
            evidence_type=evidence_type,
            metadata_=evidence_metadata,
            content_bytes=file_data,
            extracted_path=f"db://evidence/{stored_name}/extracted" if is_zip else None,
        )
        db.add(evidence)
        db.flush()
        logger.info("Evidence row flushed evidence_id=%s", evidence.id)

        if is_zip:
            for file_info in extracted_files:
                mime_type = file_info.get("mime_type")
                file_metadata = {
                    "size": file_info["size"],
                    "mime_type": mime_type,
                    "md5": file_info.get("md5"),
                    "sha1": file_info.get("sha1"),
                    "parent_sha256": sha256,
                    "storage_mode": "postgres_bytea",
                }
                media_type = _media_type_from_mime(mime_type)
                logger.info(
                    "Creating EvidenceFile row evidence_id=%s relative_path=%s size=%s mime_type=%s",
                    evidence.id,
                    file_info["relative_path"],
                    file_info["size"],
                    mime_type,
                )
                evidence_file = EvidenceFile(
                    evidence_id=evidence.id,
                    relative_path=file_info["relative_path"],
                    sha256=file_info["sha256"],
                    file_size=file_info["size"],
                    mime_type=mime_type,
                    metadata_=file_metadata,
                    content_bytes=file_info["content_bytes"],
                    is_media=media_type is not None,
                    media_type=media_type,
                )
                db.add(evidence_file)
            db.flush()
        logger.info("Creating ActivityLog row case_id=%s evidence_id=%s", case_id, evidence.id)
        db.add(ActivityLog(
            case_id=case_id,
            action="upload_evidence",
            description=f"Evidence uploaded: {evidence.original_filename} (SHA-256: {evidence.sha256[:8]}...)",
        ))

        logger.info("Committing evidence upload transaction evidence_id=%s", evidence.id)
        db.commit()
        db.refresh(evidence)
        logger.info("Evidence upload committed evidence_id=%s", evidence.id)

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
            "md5": md5,
            "sha1": sha1,
            "size": file_size,
            "evidence_type": evidence.evidence_type,
            "is_zip": is_zip,
            "extracted_files_count": len(extracted_files) if is_zip else 0,
        }
    except HTTPException:
        logger.warning(
            "Evidence upload rejected case_id=%s filename=%s\n%s",
            case_id,
            file.filename,
            traceback.format_exc(),
        )
        db.rollback()
        raise
    except IntegrityError as exc:
        logger.error(
            "Evidence upload integrity error case_id=%s filename=%s\n%s",
            case_id,
            file.filename,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence upload conflicts with existing database state",
        ) from exc
    except SQLAlchemyError as exc:
        logger.error(
            "Evidence upload database error case_id=%s filename=%s\n%s",
            case_id,
            file.filename,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while uploading evidence",
        ) from exc
    except OSError as exc:
        logger.error(
            "Evidence upload file handling error case_id=%s filename=%s storage_path=%s extract_dir=%s\n%s",
            case_id,
            file.filename,
            storage_path,
            extract_dir,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File storage error while uploading evidence",
        ) from exc
    except Exception as e:
        logger.error(
            "Unexpected evidence upload error case_id=%s filename=%s\n%s",
            case_id,
            file.filename,
            traceback.format_exc(),
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while uploading evidence",
        ) from e


@router.get("", response_model=List[EvidenceRead])
@router.get("/", response_model=List[EvidenceRead])
def list_evidences(case_id: int, db: Session = Depends(get_db)):
    """List evidences for a specific case."""
    try:
        logger.info("Listing evidence requested case_id=%s", case_id)

        logger.info("Validating case exists before listing evidence case_id=%s", case_id)
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        logger.info("Querying evidence rows case_id=%s", case_id)
        evidences = (
            db.query(Evidence)
            .filter(Evidence.case_id == case_id)
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
        logger.info("Evidence rows loaded case_id=%s count=%s", case_id, len(evidences))

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
        if not evidence_file:
            raise HTTPException(status_code=404, detail="File not found in evidence")
        if not evidence_file.content_bytes:
            raise HTTPException(status_code=404, detail="File content not available in storage (legacy unverifiable row)")

        from fastapi.responses import Response
        filename = Path(evidence_file.relative_path).name or evidence.original_filename
        return Response(
            content=evidence_file.content_bytes,
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
    ).filter(Evidence.id == evidence_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case_id, original_filename, sha256 = row
    sha_prefix = sha256[:8] if sha256 else "unknown"

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
