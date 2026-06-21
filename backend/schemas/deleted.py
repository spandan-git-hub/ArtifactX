"""Pydantic schemas for Deleted Message."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeletedMessageBase(BaseModel):
    case_id: int
    evidence_id: int
    source_app: str
    chat_jid: str
    gap_start: int
    gap_end: int
    missing_count: int
    confidence_score: float
    detection_method: str


class DeletedMessageCreate(DeletedMessageBase):
    pass


class DeletedMessageRead(DeletedMessageBase):
    id: int
    detected_at: datetime

    class Config:
        from_attributes = True