"""Pydantic schemas for Timeline Event (B11 Timeline & Time Handling, Rules R8, R10, R11)."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TimelineEventBase(BaseModel):
    case_id: int
    evidence_id: Optional[int] = None
    event_type: str
    source_app: str
    timestamp: int
    normalized_timestamp: Optional[datetime] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    description: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Additive forensic fields (Rules R8, R10, R11)
    event_id: Optional[str] = None
    utc_ms: Optional[int] = None
    time_unit: Optional[str] = "unknown"
    tz_basis: Optional[str] = "utc_source"
    time_flags: Optional[List[str]] = Field(default_factory=list)
    raw_timestamp: Optional[str] = None
    actor_ref: Optional[str] = None
    chat_ref: Optional[str] = None
    summary: Optional[str] = None
    source_refs: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    confidence_score: Optional[float] = 1.0
    strength: Optional[str] = "deterministic"
    limitations: Optional[List[str]] = Field(default_factory=list)


class TimelineEventCreate(TimelineEventBase):
    pass


class TimelineEventRead(TimelineEventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TimelineEventFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None
    source_app: Optional[str] = None
    entity_type: Optional[str] = None
    search: Optional[str] = None  # full-text search in description