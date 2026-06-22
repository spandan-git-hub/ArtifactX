"""Service for logging operations."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.repositories.log_repo import LogRepository
from backend.schemas.log import (
    ActivityLogEntry,
    AnalysisLogEntry,
    ErrorLogEntry,
    LogSummary,
)


class LogService:
    """Service for managing analysis, error, and activity logs."""

    def __init__(self, db: Session):
        self._repo = LogRepository(db)

    def get_analysis_logs(
        self,
        evidence_id: Optional[int] = None,
        log_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisLogEntry]:
        """Get analysis logs with optional filters."""
        logs = self._repo.get_analysis_logs(
            evidence_id=evidence_id,
            log_type=log_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return [AnalysisLogEntry.model_validate(log) for log in logs]

    def get_error_logs(
        self,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ErrorLogEntry]:
        """Get error logs with optional filters."""
        logs = self._repo.get_error_logs(
            case_id=case_id,
            evidence_id=evidence_id,
            start_date=start_date,
            end_date=end_date,
            error_type=error_type,
            limit=limit,
            offset=offset,
        )
        return [ErrorLogEntry.model_validate(log) for log in logs]

    def get_activity_logs(
        self,
        case_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityLogEntry]:
        """Get activity logs with optional filters."""
        logs = self._repo.get_activity_logs(
            case_id=case_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return [ActivityLogEntry.model_validate(log) for log in logs]

    def log_analysis(
        self,
        evidence_id: int,
        log_type: str,
        message: str,
        details: dict | None = None,
    ) -> AnalysisLogEntry:
        """Log an analysis event."""
        log = self._repo.add_analysis_log(
            evidence_id=evidence_id,
            log_type=log_type,
            message=message,
            details=details,
        )
        return AnalysisLogEntry.model_validate(log)

    def log_error(
        self,
        error_type: str,
        message: str,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: dict | None = None,
    ) -> ErrorLogEntry:
        """Log an error event."""
        log = self._repo.add_error_log(
            error_type=error_type,
            message=message,
            case_id=case_id,
            evidence_id=evidence_id,
            stack_trace=stack_trace,
            endpoint=endpoint,
            method=method,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata=metadata,
        )
        return ErrorLogEntry.model_validate(log)

    def log_activity(
        self,
        case_id: int,
        action: str,
        description: str,
    ) -> ActivityLogEntry:
        """Log an activity event."""
        log = self._repo.add_activity_log(
            case_id=case_id,
            action=action,
            description=description,
        )
        return ActivityLogEntry.model_validate(log)

    def get_log_summary(self, case_id: int) -> LogSummary:
        """Get a summary of all logs for a case."""
        summary = self._repo.get_case_log_summary(case_id)
        return LogSummary(
            total_activities=summary["total_activities"],
            total_analysis=summary["total_analysis"],
            total_errors=summary["total_errors"],
            recent_errors=[ErrorLogEntry.model_validate(e) for e in summary["recent_errors"]],
            recent_activities=[
                ActivityLogEntry.model_validate(a) for a in summary["recent_activities"]
            ],
        )


def get_log_service(db: Session) -> LogService:
    """Dependency for getting LogService instance."""
    return LogService(db)