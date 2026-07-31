"""Pydantic schemas for Case."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    investigator: Optional[str] = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    investigator: Optional[str] = None
    status: Optional[str] = None


class CaseRead(CaseBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisStageInfo(BaseModel):
    stage_number: int
    stage_name: str
    description: str


class EvidenceWorkspaceSummary(BaseModel):
    id: int
    original_filename: str
    sha256: str
    evidence_type: Optional[str] = None
    file_count: int = 0
    uploaded_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None


class WorkspaceCounts(BaseModel):
    evidence_count: int = 0
    whatsapp_messages: int = 0
    telegram_messages: int = 0
    total_messages: int = 0
    total_contacts: int = 0
    timeline_events: int = 0
    deleted_messages: int = 0
    correlation_edges: int = 0


class CaseWorkspaceRead(BaseModel):
    case: CaseRead
    active_evidence: list[EvidenceWorkspaceSummary]
    hash_integrity_score: float
    analysis_stage: AnalysisStageInfo
    summary_counts: WorkspaceCounts

