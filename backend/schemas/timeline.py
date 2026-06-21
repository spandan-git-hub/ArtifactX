"""Pydantic schemas for Timeline Event."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TimelineEventBase(BaseModel):
    case_id: int
    evidence_id: int
    event_type: str
    source_app: str
    timestamp: int
    normalized_timestamp: datetime
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    description: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TimelineEventCreate(TimelineEventBase):
    pass


class TimelineEventRead(TimelineEventBase):
    id: int

    class Config:
        from_attributes = True


class TimelineEventFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None
    source_app: Optional[str] = None
    entity_type: Optional[str] = None
    search: Optional[str] = None  # full-text search in description