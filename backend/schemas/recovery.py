"""Pydantic schemas for physical recovery findings and runs."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RecoveryProvenance(BaseModel):
    source_artifact_id: Optional[int] = None
    source_sha256: str
    method: str
    algorithm_version: str = "2.0.0-r2"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class RecoveredFindingResponse(BaseModel):
    id: int
    case_id: int
    run_id: Optional[int] = None
    evidence_id: int
    source_file_id: Optional[int] = None
    source_app: str
    method: str
    page_number: int
    byte_offset: int
    raw_payload_hash: str
    raw_payload_preview: Optional[str] = None
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    sender_id: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[int] = None
    media_reference: Optional[str] = None
    validation_status: str
    limitations: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class RecoveryRunResponse(BaseModel):
    id: int
    case_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    findings_count: int = 0
    wal_pages_analyzed: int = 0
    freelist_pages_analyzed: int = 0
    slack_spans_analyzed: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class RecoveryRunRequest(BaseModel):
    evidence_id: Optional[int] = None
    source_app_hint: Optional[str] = None  # 'whatsapp', 'telegram'
