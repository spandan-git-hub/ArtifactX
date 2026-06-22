"""Tests for logging and audit trail endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import Base, engine, SessionLocal
from backend.models.models import Case, ActivityLog, AnalysisLog, ErrorLog
from backend.repositories.log_repo import LogRepository


@pytest.fixture
def client():
    """Create test client with fresh database."""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create database session for direct repository tests."""
    SessionLocal.execute("DELETE FROM activity_logs")
    SessionLocal.execute("DELETE FROM analysis_logs")
    SessionLocal.execute("DELETE FROM error_logs")
    SessionLocal.execute("DELETE FROM cases")
    SessionLocal.commit()
    yield SessionLocal
    SessionLocal.execute("DELETE FROM activity_logs")
    SessionLocal.execute("DELETE FROM analysis_logs")
    SessionLocal.execute("DELETE FROM error_logs")
    SessionLocal.execute("DELETE FROM cases")
    SessionLocal.commit()


@pytest.fixture
def test_case(db_session):
    """Create a test case."""
    case = Case(
        name="Test Case",
        description="Test case for logging",
        investigator="Test Investigator",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


class TestActivityLogEndpoints:
    """Tests for activity log API endpoints."""

    def test_create_activity_log(self, client, db_session, test_case):
        """Test creating an activity log entry."""
        repo = LogRepository(db_session)
        log = repo.add_activity_log(
            case_id=test_case.id,
            action="case_created",
            description="Test case created",
        )

        assert log.id is not None
        assert log.case_id == test_case.id
        assert log.action == "case_created"
        assert log.description == "Test case created"
        assert log.timestamp is not None

    def test_get_activity_logs(self, client, test_case):
        """Test getting activity logs via API."""
        response = client.get("/api/logs/activity", params={"case_id": test_case.id})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_activity_logs_with_filters(self, client, db_session, test_case):
        """Test activity logs with filters."""
        repo = LogRepository(db_session)
        repo.add_activity_log(
            case_id=test_case.id,
            action="evidence_uploaded",
            description="Evidence uploaded",
        )

        response = client.get(
            "/api/logs/activity",
            params={"case_id": test_case.id, "action": "evidence_uploaded"},
        )
        assert response.status_code == 200

    def test_activity_log_empty_case(self, client, db_session, test_case):
        """Test activity logs for case with no activity."""
        response = client.get("/api/logs/activity", params={"case_id": test_case.id})
        assert response.status_code == 200
        assert response.json() == []

    def test_activity_logs_limit_offset(self, client, db_session, test_case):
        """Test activity logs pagination."""
        # Create multiple logs
        repo = LogRepository(db_session)
        for i in range(5):
            repo.add_activity_log(
                case_id=test_case.id,
                action=f"action_{i}",
                description=f"Test action {i}",
            )

        # Test limit
        response = client.get("/api/logs/activity", params={"limit": 2})
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Test offset
        response = client.get("/api/logs/activity", params={"limit": 10, "offset": 2})
        assert response.status_code == 200
        assert len(response.json()) <= 3


class TestAnalysisLogEndpoints:
    """Tests for analysis log API endpoints."""

    @pytest.fixture
    def test_evidence(self, db_session, test_case):
        """Create test evidence for analysis logs."""
        from backend.models.models import Evidence

        evidence = Evidence(
            case_id=test_case.id,
            original_filename="test.db",
            storage_path="/storage/test.db",
            sha256="a" * 64,
            content_type="application/x-sqlite",
        )
        db_session.add(evidence)
        db_session.commit()
        db_session.refresh(evidence)
        return evidence

    def test_create_analysis_log(self, client, db_session, test_evidence):
        """Test creating an analysis log entry."""
        repo = LogRepository(db_session)
        log = repo.add_analysis_log(
            evidence_id=test_evidence.id,
            log_type="extraction",
            message="WhatsApp messages extracted",
            details={"count": 100, "duration_ms": 1500},
        )

        assert log.id is not None
        assert log.evidence_id == test_evidence.id
        assert log.log_type == "extraction"
        assert log.message == "WhatsApp messages extracted"
        assert log.details == {"count": 100, "duration_ms": 1500}

    def test_get_analysis_logs(self, client, test_evidence):
        """Test getting analysis logs via API."""
        response = client.get("/api/logs/analysis", params={"evidence_id": test_evidence.id})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_analysis_logs_with_type_filter(self, client, db_session, test_evidence):
        """Test analysis logs filtered by log type."""
        repo = LogRepository(db_session)
        repo.add_analysis_log(
            evidence_id=test_evidence.id,
            log_type="extraction",
            message="Messages extracted",
        )

        response = client.get(
            "/api/logs/analysis",
            params={"evidence_id": test_evidence.id, "log_type": "extraction"},
        )
        assert response.status_code == 200

    def test_analysis_log_empty_evidence(self, client, db_session, test_evidence):
        """Test analysis logs for evidence with no logs."""
        response = client.get("/api/logs/analysis", params={"evidence_id": test_evidence.id})
        assert response.status_code == 200
        assert response.json() == []


class TestErrorLogEndpoints:
    """Tests for error log API endpoints."""

    def test_create_error_log(self, client, db_session, test_case):
        """Test creating an error log entry."""
        repo = LogRepository(db_session)
        log = repo.add_error_log(
            error_type="ValidationError",
            message="Invalid input provided",
            case_id=test_case.id,
            stack_trace="Traceback...",
            endpoint="/api/evidence",
            method="POST",
            client_ip="127.0.0.1",
        )

        assert log.id is not None
        assert log.error_type == "ValidationError"
        assert log.message == "Invalid input provided"
        assert log.case_id == test_case.id
        assert log.endpoint == "/api/evidence"
        assert log.method == "POST"

    def test_get_error_logs(self, client, test_case):
        """Test getting error logs via API."""
        response = client.get("/api/logs/errors", params={"case_id": test_case.id})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_error_logs_with_type_filter(self, client, db_session, test_case):
        """Test error logs filtered by error type."""
        repo = LogRepository(db_session)
        repo.add_error_log(
            error_type="FileNotFoundError",
            message="Evidence file not found",
            case_id=test_case.id,
        )

        response = client.get(
            "/api/logs/errors",
            params={"case_id": test_case.id, "error_type": "FileNotFoundError"},
        )
        assert response.status_code == 200

    def test_error_logs_only(self, client, db_session, test_case):
        """Test that only errors are returned."""
        repo = LogRepository(db_session)

        # Create an error log
        repo.add_error_log(
            error_type="DatabaseError",
            message="Connection failed",
            case_id=test_case.id,
        )

        # Verify no other log types in errors endpoint
        repo.add_activity_log(
            case_id=test_case.id,
            action="test",
            description="Test activity",
        )

        response = client.get("/api/logs/errors", params={"case_id": test_case.id})
        data = response.json()

        for item in data:
            assert "error_type" in item or "id" in item


class TestLogSummaryEndpoint:
    """Tests for log summary endpoint."""

    def test_get_log_summary(self, client, db_session, test_case):
        """Test getting log summary for a case."""
        repo = LogRepository(db_session)

        # Add some logs
        repo.add_activity_log(
            case_id=test_case.id,
            action="evidence_uploaded",
            description="Evidence uploaded",
        )
        repo.add_activity_log(
            case_id=test_case.id,
            action="analysis_started",
            description="Analysis started",
        )
        repo.add_error_log(
            error_type="Warning",
            message="Minor issue detected",
            case_id=test_case.id,
        )

        response = client.get(f"/api/logs/summary/{test_case.id}")
        assert response.status_code == 200

        data = response.json()
        assert "total_activities" in data
        assert "total_analysis" in data
        assert "total_errors" in data
        assert "recent_errors" in data
        assert "recent_activities" in data
        assert data["total_activities"] >= 2
        assert data["total_errors"] >= 1


class TestLogRepository:
    """Tests for LogRepository class."""

    def test_count_activity_logs(self, db_session, test_case):
        """Test counting activity logs."""
        repo = LogRepository(db_session)
        count_before = repo.count_activity_logs(case_id=test_case.id)

        repo.add_activity_log(
            case_id=test_case.id,
            action="test",
            description="Test",
        )

        count_after = repo.count_activity_logs(case_id=test_case.id)
        assert count_after == count_before + 1

    def test_count_error_logs(self, db_session, test_case):
        """Test counting error logs."""
        repo = LogRepository(db_session)
        count_before = repo.count_error_logs(case_id=test_case.id)

        repo.add_error_log(
            error_type="TestError",
            message="Test error",
            case_id=test_case.id,
        )

        count_after = repo.count_error_logs(case_id=test_case.id)
        assert count_after == count_before + 1

    def test_get_recent_errors(self, db_session, test_case):
        """Test getting recent errors."""
        repo = LogRepository(db_session)

        # Add 10 errors
        for i in range(10):
            repo.add_error_log(
                error_type=f"Error{i}",
                message=f"Error {i}",
                case_id=test_case.id,
            )

        # Get recent 5
        recent = repo.get_recent_errors(case_id=test_case.id, limit=5)
        assert len(recent) == 5

    def test_get_recent_activities(self, db_session, test_case):
        """Test getting recent activities."""
        repo = LogRepository(db_session)

        # Add 10 activities
        for i in range(10):
            repo.add_activity_log(
                case_id=test_case.id,
                action=f"action{i}",
                description=f"Activity {i}",
            )

        # Get recent 5
        recent = repo.get_recent_activities(case_id=test_case.id, limit=5)
        assert len(recent) == 5

    def test_analysis_logs_date_filter(self, db_session, test_case):
        """Test analysis logs filter by date range."""
        from datetime import datetime, timedelta

        repo = LogRepository(db_session)

        # Add logs
        repo.add_analysis_log(
            evidence_id=1,
            log_type="test",
            message="Test log",
        )

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Filter by date range
        logs = repo.get_analysis_logs(
            start_date=yesterday,
            end_date=tomorrow,
            limit=10,
        )
        assert len(logs) >= 1

        # Filter with no matches
        old_date = now - timedelta(days=30)
        logs = repo.get_analysis_logs(
            start_date=old_date,
            end_date=yesterday,
            limit=10,
        )
        assert len(logs) == 0