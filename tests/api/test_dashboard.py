"""Integration tests for Dashboard API endpoints."""

from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import (
    Case,
    Evidence,
    WhatsAppMessage,
    WhatsAppContact,
    WhatsAppGroup,
    TelegramMessage,
    TelegramContact,
    TimelineEvent,
    MediaItem,
    DeletedMessage,
    CorrelationEdge,
)

client = TestClient(app)


def test_get_case_stats(db_session: Session):
    """Test getting case statistics."""
    # Create test case
    case = Case(name="Stats Test Case", description="Test stats")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Create evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="abc123",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add messages
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        body="Test message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "total_contacts" in data
    assert "total_media" in data
    assert "total_deleted" in data
    assert "total_groups" in data
    assert "whatsapp" in data
    assert "telegram" in data


def test_get_case_stats_not_found(db_session: Session):
    """Test getting stats for non-existent case."""
    response = client.get("/api/cases/9999/stats")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Case not found"


def test_get_correlation_stats(db_session: Session):
    """Test getting correlation statistics."""
    case = Case(name="Correlation Stats Test", description="Test correlation")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add a correlation edge
    edge = CorrelationEdge(
        case_id=case.id,
        source_type="wa_message",
        target_type="wa_contact",
        source_id="msg1",
        target_id="user@example.com",
        relation_type="sent_by",
    )
    db_session.add(edge)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/correlation-stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_edges" in data
    assert "message_contact_links" in data
    assert "message_media_links" in data
    assert "cross_app_links" in data
    assert data["total_edges"] >= 1


def test_get_timeline_stats(db_session: Session):
    """Test getting timeline statistics."""
    case = Case(name="Timeline Stats Test", description="Test timeline")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add timeline events
    event1 = TimelineEvent(
        case_id=case.id,
        event_type="message_sent",
        source_app="whatsapp",
        normalized_timestamp=datetime(2024, 1, 15, 10, 0, 0),
    )
    event2 = TimelineEvent(
        case_id=case.id,
        event_type="message_received",
        source_app="whatsapp",
        normalized_timestamp=datetime(2024, 1, 15, 11, 0, 0),
    )
    db_session.add_all([event1, event2])
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/timeline-stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "events_by_type" in data
    assert "events_by_app" in data
    assert data["total_events"] == 2


def test_get_case_overview(db_session: Session):
    """Test getting comprehensive case overview."""
    case = Case(name="Overview Test", description="Test overview")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Create evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="def456",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add message
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        body="Test message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    # Add timeline event
    event = TimelineEvent(
        case_id=case.id,
        event_type="message_sent",
        source_app="whatsapp",
        normalized_timestamp=datetime(2024, 1, 15, 10, 0, 0),
    )
    db_session.add(event)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case.id
    assert data["case_name"] == "Overview Test"
    assert "stats" in data
    assert "correlation_stats" in data
    assert "timeline_stats" in data
    assert "recent_events" in data
    assert "apps" in data


def test_get_case_stats_with_whatsapp_and_telegram(db_session: Session):
    """Test stats with both WhatsApp and Telegram data."""
    case = Case(name="Dual App Test", description="Test both apps")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # WhatsApp evidence
    wa_evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="wa123",
    )
    db_session.add(wa_evidence)
    db_session.commit()
    db_session.refresh(wa_evidence)

    # Telegram evidence
    tg_evidence = Evidence(
        case_id=case.id,
        original_filename="tg.db",
        storage_path="/storage/tg.db",
        sha256="tg456",
    )
    db_session.add(tg_evidence)
    db_session.commit()
    db_session.refresh(tg_evidence)

    # Add WhatsApp messages
    wa_msg = WhatsAppMessage(
        evidence_id=wa_evidence.id,
        message_id="wa_msg1",
        body="WhatsApp message",
        timestamp=1700000000000,
    )
    db_session.add(wa_msg)

    # Add Telegram messages
    tg_msg = TelegramMessage(
        evidence_id=tg_evidence.id,
        message_id=1001,
        body="Telegram message",
        timestamp=1700000100000,
    )
    db_session.add(tg_msg)
    db_session.commit()

    response = client.get(f"/api/cases/{case.id}/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] >= 2
    assert data["whatsapp"]["message_count"] >= 1
    assert data["telegram"]["message_count"] >= 1


def test_get_correlation_stats_not_found(db_session: Session):
    """Test getting correlation stats for non-existent case."""
    response = client.get("/api/cases/9999/correlation-stats")

    assert response.status_code == 404


def test_get_timeline_stats_not_found(db_session: Session):
    """Test getting timeline stats for non-existent case."""
    response = client.get("/api/cases/9999/timeline-stats")

    assert response.status_code == 404


def test_get_case_overview_not_found(db_session: Session):
    """Test getting overview for non-existent case."""
    response = client.get("/api/cases/9999/overview")

    assert response.status_code == 404


def test_dashboard_repository_stats(db_session: Session):
    """Test DashboardRepository directly."""
    from backend.repositories.dashboard_repo import DashboardRepository

    case = Case(name="Repo Test", description="Test repo")
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
    db_session.refresh(evidence)

    # Add contacts
    contact = WhatsAppContact(
        evidence_id=evidence.id,
        jid="test@example.com",
        display_name="Test User",
        phone_number="+1234567890",
    )
    db_session.add(contact)

    # Add groups
    group = WhatsAppGroup(
        evidence_id=evidence.id,
        group_jid="group@example.com",
        subject="Test Group",
    )
    db_session.add(group)

    # Add message (required to detect app)
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        body="Test message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    repo = DashboardRepository(db_session)

    # Test get_case_stats
    stats = repo.get_case_stats(case.id)
    assert stats["total_contacts"] >= 1
    assert stats["total_groups"] >= 1

    # Test get_apps_for_case
    apps = repo.get_apps_for_case(case.id)
    assert "whatsapp" in apps

    # Test get_correlation_stats
    corr_stats = repo.get_correlation_stats(case.id)
    assert "total_edges" in corr_stats

    # Test get_timeline_stats (no events yet)
    tl_stats = repo.get_timeline_stats(case.id)
    assert "total_events" in tl_stats
    assert tl_stats["total_events"] == 0


def test_dashboard_repository_empty_case(db_session: Session):
    """Test DashboardRepository with empty case."""
    from backend.repositories.dashboard_repo import DashboardRepository

    case = Case(name="Empty Test", description="No data")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    repo = DashboardRepository(db_session)

    stats = repo.get_case_stats(case.id)
    assert stats["total_messages"] == 0
    assert stats["total_contacts"] == 0
    assert stats["total_media"] == 0

    apps = repo.get_apps_for_case(case.id)
    assert len(apps) == 0


# Clean up
def tear_down():
    app.dependency_overrides.clear()