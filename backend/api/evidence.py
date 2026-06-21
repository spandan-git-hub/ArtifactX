"""Evidence management API endpoints."""

import zipfile
import io
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Evidence, EvidenceFile
from backend.utils.hashing import compute_sha256_bytes, compute_sha256
from backend.utils.file_storage import save_upload, delete_file
from backend.app.config import UPLOADS_DIR
from backend.schemas.evidence import EvidenceRead

router = APIRouter()


def _is_zip_file(filename: str, content_type: Optional[str]) -> bool:
    """Heuristic to check if file is a ZIP."""
    if content_type and "zip" in content_type.lower():
        return True
    if filename and filename.lower().endswith(".zip"):
        return True
    return False


def _extract_zip(zip_data: bytes, extract_dir: Path) -> List[dict]:
    """Extract ZIP archive to directory, return list of file info.
    Each dict contains: relative_path, size, sha256.
    """
    extracted_info = []
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Ensure no path traversal
        for info in zf.infolist():
            # Skip directories
            if info.is_dir():
                continue
            # Normalize path to prevent directory traversal
            target_path = Path(info.filename)
            # Ensure the path is relative and does not start with slash or contain ..
            # We'll join with extract_dir and then check if it's inside.
            # Simpler: we only accept filenames without path separators? Keep as is but ensure safety.
            # For simplicity, we'll basename only? But we want to preserve directory structure inside ZIP.
            # We'll allow subdirectories but ensure they stay under extract_dir.
            # Resolve the target path relative to extract_dir.
            target_path = extract_dir / info.filename
            # Resolve to absolute path and ensure it's still under extract_dir.
            try:
                target_path.resolve().relative_to(extract_dir.resolve())
            except ValueError:
                # Attempted path traversal
                continue
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Extract file
            with zf.open(info) as source, open(target_path, "wb") as target:
                # Copy in chunks to handle large files
                while True:
                    chunk = source.read(8192)
                    if not chunk:
                        break
                    target.write(chunk)
            # Compute SHA-256
            file_sha256 = compute_sha256(target_path)
            extracted_info.append(
                {
                    "relative_path": str(target_path.relative_to(extract_dir)),
                    "size": info.file_size,
                    "sha256": file_sha256,
                }
            )
    return extracted_info


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload evidence file (ZIP or regular) for a case."""
    # Read file data
    file_data = file.file.read()

    # Compute SHA-256 of the uploaded file
    sha256 = compute_sha256_bytes(file_data)

    # Determine if it's a ZIP
    is_zip = _is_zip_file(file.filename, file.content_type)

    storage_path = None
    extracted_path = None
    evidence_type = "zip" if is_zip else "file"

    if is_zip:
        # Create a subdirectory for extracted files under UPLOADS_DIR
        # Use a unique directory name based on hash or timestamp
        import uuid
        extract_dir_name = f"extract_{uuid.uuid4().hex}"
        extract_dir = UPLOADS_DIR / extract_dir_name
        extract_dir.mkdir(parents=True, exist_ok=True)

        # Extract ZIP
        extracted_files = _extract_zip(file_data, extract_dir)
        extracted_path = str(extract_dir)

        # Save the ZIP file itself as evidence
        zip_filename = file.filename or "unnamed.zip"
        zip_storage_path = save_upload(zip_filename, file_data)
        storage_path = str(zip_storage_path)
    else:
        # Regular file: save directly
        filename = file.filename or "unnamed"
        storage_path = save_upload(filename, file_data)
        extracted_path = None

    # Prepare metadata for evidence (uploaded file)
    evidence_metadata = {
        "original_content_type": file.content_type,
        "upload_size": len(file_data),
        "is_zip": is_zip,
    }

    # Create evidence record
    evidence = Evidence(
        case_id=case_id,
        original_filename=file.filename or "unnamed",
        storage_path=storage_path,
        sha256=sha256,
        content_type=file.content_type,
        evidence_type=evidence_type,
        metadata_=evidence_metadata,
        extracted_path=extracted_path,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # If ZIP, create EvidenceFile records for each extracted file
    if is_zip and extracted_path:
        extract_dir = Path(extracted_path)
        for file_info in extracted_files:
            # Build absolute path to the extracted file
            abs_path = extract_dir / file_info["relative_path"]
            # Determine mime type (simple extension mapping)
            mime_type = None
            if abs_path.suffix:
                # Very basic mapping; could be improved
                ext = abs_path.suffix.lower()
                if ext in [".jpg", ".jpeg"]:
                    mime_type = "image/jpeg"
                elif ext == ".png":
                    mime_type = "image/png"
                elif ext == ".gif":
                    mime_type = "image/gif"
                elif ext == ".pdf":
                    mime_type = "application/pdf"
                elif ext == ".txt":
                    mime_type = "text/plain"
                # else leave as None
            file_metadata = {
                "size": file_info["size"],
                "mime_type": mime_type,
                "extracted_path": str(abs_path),
            }
            evidence_file = EvidenceFile(
                evidence_id=evidence.id,
                relative_path=file_info["relative_path"],
                sha256=file_info["sha256"],
                file_size=file_info["size"],
                mime_type=mime_type,
                metadata_=file_metadata,
                is_media=mime_type and mime_type.startswith("image/") or mime_type and mime_type.startswith("video/"),
                media_type=(
                    "image"
                    if mime_type and mime_type.startswith("image/")
                    else "video"
                    if mime_type and mime_type.startswith("video/")
                    else "audio"
                    if mime_type and mime_type.startswith("audio/")
                    else None
                ),
            )
            db.add(evidence_file)
        db.commit()

    # Return response
    return {
        "id": evidence.id,
        "filename": evidence.original_filename,
        "sha256": evidence.sha256,
        "size": len(file_data),
        "evidence_type": evidence.evidence_type,
        "is_zip": is_zip,
        "extracted_files_count": len(extracted_files) if is_zip else 0,
    }


@router.get("/", response_model=List[EvidenceRead])
def list_evidences(case_id: int, db: Session = Depends(get_db)):
    """List evidences for a specific case."""
    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return evidences


@router.get("/{evidence_id}")
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@router.get("/{evidence_id}/files")
def list_evidence_files(evidence_id: int, db: Session = Depends(get_db)):
    """List files contained within the evidence (if ZIP)."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    files = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).all()
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


@router.get("/{evidence_id}/files/{file_id}")
def get_evidence_file(evidence_id: int, file_id: int, db: Session = Depends(get_db)):
    """Download a specific file from the evidence inventory."""
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


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Delete evidence and its associated files."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    # Delete storage files
    if evidence.storage_path:
        try:
            delete_file(Path(evidence.storage_path))
        except Exception:
            pass  # Best effort
    if evidence.evidence_type == "zip" and evidence.extracted_path:
        try:
            delete_file(Path(evidence.extracted_path))
        except Exception:
            pass
    # Delete database records (cascade will delete EvidenceFile and AnalysisResult)
    db.delete(evidence)
    db.commit()
    return None