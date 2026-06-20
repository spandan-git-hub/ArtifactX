"""Evidence management API endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Evidence
from backend.utils.hashing import compute_sha256_bytes

router = APIRouter()


@router.post("/upload")
def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload evidence file for a case."""
    # Read file data
    file_data = file.file.read()

    # Compute SHA-256
    sha256 = compute_sha256_bytes(file_data)

    # Save to storage (simplified for Phase 0)
    filename = file.filename or "unnamed"
    storage_path = Path("uploads") / filename
    with open(storage_path, "wb") as f:
        f.write(file_data)

    # Create evidence record
    evidence = Evidence(
        case_id=case_id,
        original_filename=filename,
        storage_path=str(storage_path),
        sha256=sha256,
        content_type=file.content_type,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {
        "id": evidence.id,
        "filename": filename,
        "sha256": sha256,
        "size": len(file_data),
    }


@router.get("/{evidence_id}")
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence
