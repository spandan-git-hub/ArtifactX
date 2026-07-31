"""Evidence management API endpoints."""

import io
import logging
import mimetypes
import shutil
import traceback
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import ActivityLog, Case, Evidence, EvidenceFile
from backend.utils.hashing import compute_sha256_bytes, compute_sha256
from backend.utils.file_storage import delete_file
from backend.app.config import UPLOADS_DIR
from backend.schemas.evidence import EvidenceRead
from backend.services.log_service import get_log_service

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


def _extract_zip(zip_data: bytes, extract_dir: Path) -> List[dict]:
    """Extract ZIP archive to directory, return list of file info.
    Each dict contains: relative_path, size, sha256.
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
                target_path = extract_dir / relative_path
                try:
                    target_path.resolve().relative_to(extract_dir.resolve())
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unsafe ZIP member path: {info.filename}",
                    )

                logger.info(
                    "Extracting ZIP member filename=%s size=%s target=%s",
                    info.filename,
                    info.file_size,
                    target_path,
                )
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(target_path, "wb") as target:
                    while chunk := source.read(8192):
                        target.write(chunk)

                file_sha256 = compute_sha256(target_path)
                mime_type, _ = mimetypes.guess_type(str(target_path))
                extracted_info.append(
                    {
                        "relative_path": str(relative_path),
                        "size": info.file_size,
                        "sha256": file_sha256,
                        "mime_type": mime_type,
                    }
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive",
        ) from exc
    return extracted_info


def _cleanup_upload_artifacts(*paths: Optional[Path]) -> None:
    """Best-effort cleanup for files/directories created before an error."""
    for path in paths:
        if not path:
            continue
        try:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                logger.info("Cleaned up upload artifact path=%s", path)
        except Exception:
            logger.error("Failed to clean up upload artifact path=%s\n%s", path, traceback.format_exc())


def _evidence_to_response(evidence: Evidence) -> dict:
    """Serialize Evidence explicitly so response validation cannot hit SQLAlchemy metadata."""
    return {
        "id": evidence.id,
        "case_id": evidence.case_id,
        "original_filename": evidence.original_filename,
        "storage_path": evidence.storage_path,
        "sha256": evidence.sha256,
        "content_type": evidence.content_type,
        "evidence_type": evidence.evidence_type,
        "metadata": evidence.metadata_ or {},
        "extracted_path": evidence.extracted_path,
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

        logger.info("Validating upload directory path=%s", UPLOADS_DIR)
        try:
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Upload directory is not writable path=%s\n%s", UPLOADS_DIR, traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload storage is not available",
            ) from exc
        if not UPLOADS_DIR.is_dir():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload storage path is not a directory",
            )

        logger.info("Validating supported upload filename=%s content_type=%s", safe_name, file.content_type)
        _validate_supported_upload(safe_name, file.content_type)

        logger.info("Reading uploaded file filename=%s", safe_name)
        file_data = file.file.read()
        file_size = len(file_data)
        logger.info("Uploaded file read complete filename=%s size=%s", safe_name, file_size)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        logger.info("Computing uploaded file SHA-256 filename=%s size=%s", safe_name, file_size)
        sha256 = compute_sha256_bytes(file_data)
        logger.info("Computed uploaded file SHA-256 filename=%s sha256=%s", safe_name, sha256)

        is_zip = _is_zip_file(safe_name, file.content_type)
        evidence_type = "zip" if is_zip else "file"
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        storage_path = UPLOADS_DIR / stored_name

        if is_zip:
            extract_dir_name = f"extract_{uuid.uuid4().hex}"
            extract_dir = UPLOADS_DIR / extract_dir_name
            logger.info("Creating ZIP extraction directory path=%s", extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Extracting ZIP filename=%s extract_dir=%s", safe_name, extract_dir)
            extracted_files = _extract_zip(file_data, extract_dir)
            logger.info(
                "ZIP extraction complete filename=%s extract_dir=%s extracted_count=%s",
                safe_name,
                extract_dir,
                len(extracted_files),
            )

        logger.info("Saving uploaded file storage_path=%s", storage_path)
        with open(storage_path, "xb") as target:
            target.write(file_data)
        logger.info("Uploaded file saved storage_path=%s", storage_path)

        evidence_metadata = {
            "original_content_type": file.content_type,
            "upload_size": file_size,
            "is_zip": is_zip,
            "original_filename": file.filename or "unnamed",
            "stored_filename": stored_name,
        }

        logger.info("Creating Evidence row case_id=%s filename=%s sha256=%s", case_id, safe_name, sha256)
        evidence = Evidence(
            case_id=case_id,
            original_filename=safe_name,
            storage_path=str(storage_path),
            sha256=sha256,
            content_type=file.content_type,
            evidence_type=evidence_type,
            metadata_=evidence_metadata,
            extracted_path=str(extract_dir) if extract_dir else None,
        )
        db.add(evidence)
        db.flush()
        logger.info("Evidence row flushed evidence_id=%s", evidence.id)

        if is_zip and extract_dir:
            for file_info in extracted_files:
                abs_path = extract_dir / file_info["relative_path"]
                mime_type = file_info.get("mime_type")
                file_metadata = {
                    "size": file_info["size"],
                    "mime_type": mime_type,
                    "extracted_path": str(abs_path),
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
                    is_media=media_type is not None,
                    media_type=media_type,
                )
                db.add(evidence_file)

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

        return {
            "id": evidence.id,
            "filename": evidence.original_filename,
            "sha256": evidence.sha256,
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
        _cleanup_upload_artifacts(storage_path, extract_dir)
        raise
    except IntegrityError as exc:
        logger.error(
            "Evidence upload integrity error case_id=%s filename=%s\n%s",
            case_id,
            file.filename,
            traceback.format_exc(),
        )
        db.rollback()
        _cleanup_upload_artifacts(storage_path, extract_dir)
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
        _cleanup_upload_artifacts(storage_path, extract_dir)
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
        _cleanup_upload_artifacts(storage_path, extract_dir)
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
        _cleanup_upload_artifacts(storage_path, extract_dir)
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
        # Build absolute path to the stored file
        if evidence.evidence_type == "zip" and evidence.extracted_path:
            base_path = Path(evidence.extracted_path)
        else:
            # For non-ZIP, the file is the evidence itself? We'll treat the evidence file as the only file.
            # But EvidenceFile may not exist for non-ZIP; we'll handle by serving the evidence storage.
            # For simplicity, if evidence_type is file, we return the evidence storage.
            if evidence_file:
                # This case shouldn't happen, but if it does, use evidence storage
                base_path = Path(evidence.storage_path)
                relative_path = Path(evidence_file.relative_path)
            else:
                # No EvidenceFile record, treat the whole evidence as the file
                base_path = Path(evidence.storage_path)
                relative_path = Path(evidence.original_filename)
        file_path = base_path / relative_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Stored file not found")
        # Return file as streaming response
        from fastapi.responses import FileResponse

        return FileResponse(
            path=file_path,
            filename=evidence_file.original_filename if hasattr(evidence_file, "original_filename") else evidence.original_filename,
            media_type=evidence_file.mime_type or "application/octet-stream",
        )
    except Exception as e:
        # Log error
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


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Delete evidence and its associated files."""
    # Fetch tuple without loading ORM object into identity map
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

    # Delete storage files on disk
    if storage_path:
        try:
            p = Path(storage_path)
            if not p.is_absolute():
                p = UPLOADS_DIR / storage_path
            delete_file(p)
        except Exception as e:
            logger.warning(f"Could not delete storage file {storage_path}: {e}")

    if extracted_path:
        try:
            p = Path(extracted_path)
            if not p.is_absolute():
                p = UPLOADS_DIR / extracted_path
            delete_file(p)
        except Exception as e:
            logger.warning(f"Could not delete extracted path {extracted_path}: {e}")

    # Import models for bulk delete
    from backend.models.models import (
        WhatsAppMessage, WhatsAppContact, WhatsAppGroup,
        TelegramMessage, TelegramContact, TelegramGroup,
        TimelineEvent, DeletedMessage, MediaItem,
        AnalysisResult, EvidenceFile, AnalysisLog
    )

    try:
        # Fast bulk SQL deletes without ORM unit-of-work identity map conflicts
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

        # Log activity after successful deletion
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
