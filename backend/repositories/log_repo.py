"""Repository for log data access."""

from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.models.models import AnalysisLog, ActivityLog, ErrorLog


class LogRepository:
    """Repository for analysis, error, and activity logs."""

    def __init__(self, db: Session):
        self.db = db

    # Analysis Logs
    def get_analysis_logs(
        self,
        evidence_id: Optional[int] = None,
        log_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisLog]:
        """Get analysis logs with optional filters."""
        query = self.db.query(AnalysisLog)

        if evidence_id is not None:
            query = query.filter(AnalysisLog.evidence_id == evidence_id)
        if log_type:
            query = query.filter(AnalysisLog.log_type == log_type)
        if start_date:
            query = query.filter(AnalysisLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AnalysisLog.timestamp <= end_date)

        return (
            query.order_by(desc(AnalysisLog.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_analysis_logs(
        self,
        evidence_id: Optional[int] = None,
        log_type: Optional[str] = None,
    ) -> int:
        """Count analysis logs with optional filters."""
        query = self.db.query(func.count(AnalysisLog.id))

        if evidence_id is not None:
            query = query.filter(AnalysisLog.evidence_id == evidence_id)
        if log_type:
            query = query.filter(AnalysisLog.log_type == log_type)

        return query.scalar() or 0

    def add_analysis_log(
        self,
        evidence_id: int,
        log_type: str,
        message: str,
        details: dict | None = None,
    ) -> AnalysisLog:
        """Add a new analysis log entry."""
        log = AnalysisLog(
            evidence_id=evidence_id,
            log_type=log_type,
            message=message,
            details=details or {},
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    # Error Logs
    def get_error_logs(
        self,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ErrorLog]:
        """Get error logs with optional filters."""
        query = self.db.query(ErrorLog)

        if case_id is not None:
            query = query.filter(ErrorLog.case_id == case_id)
        if evidence_id is not None:
            query = query.filter(ErrorLog.evidence_id == evidence_id)
        if start_date:
            query = query.filter(ErrorLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ErrorLog.timestamp <= end_date)
        if error_type:
            query = query.filter(ErrorLog.error_type == error_type)

        return (
            query.order_by(desc(ErrorLog.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_error_logs(
        self,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
    ) -> int:
        """Count error logs with optional filters."""
        query = self.db.query(func.count(ErrorLog.id))

        if case_id is not None:
            query = query.filter(ErrorLog.case_id == case_id)
        if evidence_id is not None:
            query = query.filter(ErrorLog.evidence_id == evidence_id)

        return query.scalar() or 0

    def add_error_log(
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
    ) -> ErrorLog:
        """Add a new error log entry."""
        log = ErrorLog(
            case_id=case_id,
            evidence_id=evidence_id,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            method=method,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata_=metadata or {},
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_recent_errors(self, case_id: int, limit: int = 5) -> list[ErrorLog]:
        """Get recent errors for a case."""
        return (
            self.db.query(ErrorLog)
            .filter(ErrorLog.case_id == case_id)
            .order_by(desc(ErrorLog.timestamp))
            .limit(limit)
            .all()
        )

    # Activity Logs
    def get_activity_logs(
        self,
        case_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityLog]:
        """Get activity logs with optional filters."""
        query = self.db.query(ActivityLog)

        if case_id is not None:
            query = query.filter(ActivityLog.case_id == case_id)
        if action:
            query = query.filter(ActivityLog.action == action)
        if start_date:
            query = query.filter(ActivityLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ActivityLog.timestamp <= end_date)

        return (
            query.order_by(desc(ActivityLog.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_activity_logs(
        self,
        case_id: Optional[int] = None,
    ) -> int:
        """Count activity logs with optional filters."""
        query = self.db.query(func.count(ActivityLog.id))

        if case_id is not None:
            query = query.filter(ActivityLog.case_id == case_id)

        return query.scalar() or 0

    def add_activity_log(
        self,
        case_id: int,
        action: str,
        description: str,
    ) -> ActivityLog:
        """Add a new activity log entry."""
        log = ActivityLog(
            case_id=case_id,
            action=action,
            description=description,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_recent_activities(self, case_id: int, limit: int = 5) -> list[ActivityLog]:
        """Get recent activities for a case."""
        return (
            self.db.query(ActivityLog)
            .filter(ActivityLog.case_id == case_id)
            .order_by(desc(ActivityLog.timestamp))
            .limit(limit)
            .all()
        )

    # Summary
    def get_case_log_summary(self, case_id: int) -> dict:
        """Get a summary of all logs for a case."""
        return {
            "total_activities": self.count_activity_logs(case_id=case_id),
            "total_analysis": self.count_analysis_logs(evidence_id=None),
            "total_errors": self.count_error_logs(case_id=case_id),
            "recent_errors": [
                e for e in self.get_recent_errors(case_id=case_id)
            ],
            "recent_activities": [
                a for a in self.get_recent_activities(case_id=case_id)
            ],
        }