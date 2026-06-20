"""Pydantic schemas for Evidence."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceBase(BaseModel):
    case_id: int


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceRead(EvidenceBase):
    id: int
    original_filename: str
    storage_path: str
    sha256: str
    content_type: Optional[str] = None
    evidence_type: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    extracted_path: Optional[str] = None
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
