"""Pydantic schemas for Case."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    investigator: Optional[str] = None
    case_number: Optional[str] = None
    examiner_name: Optional[str] = None
    examiner_designation: Optional[str] = None
    agency: Optional[str] = None
    legal_authority: Optional[str] = None
    jurisdiction: Optional[str] = None
    section63_ref: Optional[str] = None
    section63_attested: Optional[bool] = False
    section63_attested_at: Optional[datetime] = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    investigator: Optional[str] = None
    case_number: Optional[str] = None
    examiner_name: Optional[str] = None
    examiner_designation: Optional[str] = None
    agency: Optional[str] = None
    legal_authority: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: Optional[str] = None
    section63_ref: Optional[str] = None
    section63_attested: Optional[bool] = None
    section63_attested_at: Optional[datetime] = None


class Section63AttestRequest(BaseModel):
    examiner_name: Optional[str] = None
    examiner_designation: Optional[str] = None
    agency: Optional[str] = None
    section63_ref: Optional[str] = None
    section63_attested: bool = True


class CaseRead(CaseBase):
    id: int
    status: str
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime
    integrity_state: Optional[str] = "NO_EVIDENCE"
    total_exhibits: int = 0
    verified_exhibits: int = 0
    mismatched_exhibits: int = 0
    unverified_exhibits: int = 0
    hash_integrity_percentage: Optional[float] = None

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
    integrity_state: str = "OK"
    uploaded_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None


class WorkspaceCounts(BaseModel):
    evidence_count: int = 0
    legacy_unverifiable_count: int = 0
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

