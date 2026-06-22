"""Pydantic schemas for Logging & Audit."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class LogEntryBase(BaseModel):
    """Base log schema."""

    message: str
    timestamp: Optional[datetime] = None


class AnalysisLogEntry(LogEntryBase):
    """Analysis log entry schema."""

    id: int
    evidence_id: Optional[int] = None
    log_type: Optional[str] = None
    details: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class ErrorLogEntry(BaseModel):
    """Error log entry schema."""

    id: int
    case_id: Optional[int] = None
    evidence_id: Optional[int] = None
    error_type: Optional[str] = None
    message: str
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ActivityLogEntry(LogEntryBase):
    """Activity log entry schema."""

    id: int
    case_id: Optional[int] = None
    action: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class LogFilter(BaseModel):
    """Filter parameters for log queries."""

    case_id: Optional[int] = None
    evidence_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    log_type: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class LogSummary(BaseModel):
    """Summary of logs for a case."""

    total_activities: int = 0
    total_analysis: int = 0
    total_errors: int = 0
    recent_errors: list[ErrorLogEntry] = []
    recent_activities: list[ActivityLogEntry] = []