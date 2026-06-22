"""Integration tests for Reports API endpoints."""

from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import (
    Case,
    Evidence,
    WhatsAppMessage,
    WhatsAppContact,
    TimelineEvent,
    DeletedMessage,
    CorrelationEdge,
)

client = TestClient(app)


def test_generate_report_endpoint(db_session: Session):
    """Test report generation endpoint."""
    # Create test case
    case = Case(name="Report Test Case", description="Test report generation")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Create evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="report123",
    )
    db_session.add(evidence)
    db_session.commit()

    response = client.post(
        f"/api/cases/{case.id}/reports",
        json={"report_type": "full"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "status" in data
    assert data["case_id"] == case.id


def test_generate_report_endpoint_not_found(db_session: Session):
    """Test report generation with non-existent case."""
    response = client.post(
        "/api/cases/9999/reports",
        json={"report_type": "full"}
    )

    assert response.status_code == 404


def test_generate_evidence_report(db_session: Session):
    """Test evidence-only report generation."""
    case = Case(name="Evidence Report Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="ev123",
    )
    db_session.add(evidence)
    db_session.commit()

    response = client.post(
        f"/api/cases/{case.id}/reports",
        json={
            "report_type": "evidence",
            "include_evidence": True,
            "include_timeline": False,
            "include_deleted": False,
            "include_correlations": False,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["completed", "failed"]


def test_get_evidence_summary_endpoint(db_session: Session):
    """Test evidence summary endpoint."""
    case = Case(name="Summary Test", description="Test summary")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="sum123",
    )
    db_session.add(evidence)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/reports/summary")

    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert "total_evidence_files" in data


def test_get_timeline_summary_endpoint(db_session: Session):
    """Test timeline summary endpoint."""
    case = Case(name="Timeline Summary Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add timeline event
    event = TimelineEvent(
        case_id=case.id,
        event_type="message_sent",
        source_app="whatsapp",
        normalized_timestamp=datetime(2024, 1, 15, 10, 0, 0),
    )
    db_session.add(event)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/reports/timeline")

    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert "total_events" in data


def test_get_deleted_summary_endpoint(db_session: Session):
    """Test deleted messages summary endpoint."""
    case = Case(name="Deleted Summary Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="del123",
    )
    db_session.add(evidence)
    db_session.commit()

    # Add deletion
    deleted = DeletedMessage(
        case_id=case.id,
        evidence_id=evidence.id,
        source_app="whatsapp",
        chat_jid="chat@example.com",
        gap_start=1000,
        gap_end=1005,
        missing_count=5,
        confidence_score=0.85,
        detection_method="sequence_gap",
    )
    db_session.add(deleted)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/reports/deleted")

    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert "total_deletions" in data


def test_report_service_evidence_summary(db_session: Session):
    """Test ReportService evidence summary."""
    from backend.services.report_service import ReportService

    service = ReportService(db_session)

    case = Case(name="Service Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="svc123",
    )
    db_session.add(evidence)
    db_session.commit()

    summary = service.get_evidence_summary(case.id)

    assert "case_id" in summary
    assert summary["total_evidence_files"] == 1


def test_report_service_timeline_summary(db_session: Session):
    """Test ReportService timeline summary."""
    from backend.services.report_service import ReportService

    service = ReportService(db_session)

    case = Case(name="Timeline Service Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    event = TimelineEvent(
        case_id=case.id,
        event_type="message_received",
        source_app="telegram",
        normalized_timestamp=datetime(2024, 2, 1, 12, 0, 0),
    )
    db_session.add(event)
    db_session.commit()

    summary = service.get_timeline_summary(case.id)

    assert "total_events" in summary
    assert summary["total_events"] == 1


def test_report_service_deleted_summary(db_session: Session):
    """Test ReportService deleted messages summary."""
    from backend.services.report_service import ReportService

    service = ReportService(db_session)

    case = Case(name="Deleted Service Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="dsvc123",
    )
    db_session.add(evidence)
    db_session.commit()

    deleted = DeletedMessage(
        case_id=case.id,
        evidence_id=evidence.id,
        source_app="telegram",
        chat_jid="test@chat.com",
        gap_start=100,
        gap_end=105,
        missing_count=5,
        confidence_score=0.75,
        detection_method="missing_record",
    )
    db_session.add(deleted)
    db_session.commit()

    summary = service.get_deleted_summary(case.id)

    assert "total_deletions" in summary
    assert summary["total_deletions"] == 1


def test_report_service_case_not_found(db_session: Session):
    """Test ReportService with non-existent case."""
    from backend.services.report_service import ReportService

    service = ReportService(db_session)

    result = service.generate_report(case_id=9999)

    assert "error" in result
    assert result["status"] == "failed"


def test_report_repository_evidence_data(db_session: Session):
    """Test ReportRepository get_evidence_data."""
    from backend.repositories.report_repo import ReportRepository

    repo = ReportRepository(db_session)

    case = Case(name="Repo Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="repo123",
    )
    db_session.add(evidence)
    db_session.commit()

    data = repo.get_evidence_data(case.id)

    assert data["case_id"] == case.id
    assert data["total_evidence_files"] == 1


def test_report_generation_with_all_types(db_session: Session):
    """Test report generation with different report types."""
    case = Case(name="All Types Test", description="Test")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="all123",
    )
    db_session.add(evidence)
    db_session.commit()

    report_types = ["full", "evidence", "timeline", "deleted", "summary"]

    for rtype in report_types:
        response = client.post(
            f"/api/cases/{case.id}/reports",
            json={"report_type": rtype}
        )
        assert response.status_code == 200


# Clean up
def tear_down():
    app.dependency_overrides.clear()