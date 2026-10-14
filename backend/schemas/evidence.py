"""Pydantic schemas for Evidence (B5.1, B5.2)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EvidenceBase(BaseModel):
    case_id: int


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceRead(EvidenceBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    original_filename: str
    storage_path: str
    sha256: str
    sha512: Optional[str] = None
    md5: Optional[str] = None
    sha1: Optional[str] = None
    content_type: Optional[str] = None
    declared_mime: Optional[str] = None
    detected_format: Optional[str] = None
    uploader: Optional[str] = None
    evidence_type: Optional[str] = None
    metadata: dict = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    extracted_path: Optional[str] = None
    integrity_state: str = "OK"

    # Acquisition metadata (B5.2)
    acquisition_method: Optional[str] = None
    device_make_model: Optional[str] = None
    device_os_version: Optional[str] = None
    app_version: Optional[str] = None
    acquisition_time_utc: Optional[datetime] = None
    acquired_by: Optional[str] = None
    acquisition_hash_claimed: Optional[str] = None
    acquisition_hash_algorithm: Optional[str] = None
    claimed_vs_computed: str = "NOT_PROVIDED"

    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None
