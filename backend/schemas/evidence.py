"""Pydantic schemas for Evidence."""

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
    content_type: Optional[str] = None
    evidence_type: Optional[str] = None
    metadata: dict = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    extracted_path: Optional[str] = None
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None
