"""Pydantic schemas for Reporting."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports."""
    FULL = "full"
    EVIDENCE = "evidence"
    TIMELINE = "timeline"
    DELETED = "deleted"
    SUMMARY = "summary"


class ReportFormat(str, Enum):
    """Report output formats."""
    PDF = "pdf"
    JSON = "json"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# Evidence Summary
class EvidenceSummary(BaseModel):
    """Summary of evidence for a case."""
    case_id: int
    case_name: str
    total_evidence_files: int
    total_extracted_files: int
    evidence_breakdown: Dict[str, int] = Field(default_factory=dict)
    media_summary: Dict[str, int] = Field(default_factory=dict)
    apps_found: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, datetime]] = None


class EvidenceReportData(BaseModel):
    """Detailed evidence data for PDF generation."""
    summary: EvidenceSummary
    evidence_list: List[Dict[str, Any]] = Field(default_factory=list)
    file_inventory: List[Dict[str, Any]] = Field(default_factory=list)


# Timeline Summary
class TimelineSummary(BaseModel):
    """Summary of timeline events."""
    case_id: int
    total_events: int
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_app: Dict[str, int] = Field(default_factory=dict)
    date_range: Optional[Dict[str, datetime]] = None
    app_breakdown: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class TimelineReportData(BaseModel):
    """Detailed timeline data for PDF generation."""
    summary: TimelineSummary
    events: List[Dict[str, Any]] = Field(default_factory=list)


# Deleted Message Summary
class DeletedMessageSummary(BaseModel):
    """Summary of deleted messages."""
    case_id: int
    total_deletions: int
    whatsapp_deletions: int
    telegram_deletions: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    date_range: Optional[Dict[str, datetime]] = None


class DeletedMessageReportData(BaseModel):
    """Detailed deleted message data for PDF generation."""
    summary: DeletedMessageSummary
    deletions: List[Dict[str, Any]] = Field(default_factory=list)


# Full Report
class FullReportData(BaseModel):
    """Complete report data for PDF generation."""
    case_id: int
    case_name: str
    case_description: str
    case_status: str
    generated_at: datetime
    evidence_summary: EvidenceSummary
    timeline_summary: TimelineSummary
    deleted_summary: DeletedMessageSummary
    statistics: Dict[str, Any] = Field(default_factory=dict)
    correlation_stats: Dict[str, Any] = Field(default_factory=dict)


# Report Generation Request/Response
class ReportGenerateRequest(BaseModel):
    """Request to generate a report."""
    case_id: int
    report_type: ReportType = ReportType.FULL
    format: ReportFormat = ReportFormat.PDF
    include_evidence: bool = True
    include_timeline: bool = True
    include_deleted: bool = True
    include_correlations: bool = True


class ReportGenerateResponse(BaseModel):
    """Response from report generation request."""
    report_id: str
    case_id: int
    report_type: ReportType
    status: ReportStatus
    message: str
    created_at: datetime


class ReportInfo(BaseModel):
    """Information about a generated report."""
    report_id: str
    case_id: int
    report_type: ReportType
    status: ReportStatus
    file_path: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# Download Response
class ReportDownloadResponse(BaseModel):
    """Response for report download."""
    report_id: str
    filename: str
    content_type: str
    size: int