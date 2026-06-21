"""Integration tests for Timeline API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.models.models import Case, Evidence, WhatsAppMessage, TelegramMessage, TimelineEvent

client = TestClient(app)


def test_build_timeline_endpoint(db_session: Session):
    """Test timeline build endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for timeline")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="/tmp/test.db",
        sha256="a" * 64,
        evidence_type="file"
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add some WhatsApp and Telegram messages
    wa_msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="wa1",
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="Hello WhatsApp",
        timestamp=1609459200,  # 2021-01-01 00:00:00 UTC
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    tg_msg = TelegramMessage(
        evidence_id=evidence.id,
        message_id=1,
        dialog_id="chat1",
        sender_id=12345,
        body="Hello Telegram",
        timestamp=1609459260,  # 2021-01-01 00:01:00 UTC
        media_type=None,
        media_path=None,
        message_type="text"
    )
    db_session.add_all([wa_msg, tg_msg])
    db_session.commit()

    # Mock the timeline service in the API module
    with patch('backend.api.timeline.timeline_service') as mock_service:
        mock_service.build_timeline_for_case.return_value = 2  # two events

        response = client.post(
            f"/api/timeline/cases/{case.id}/timeline/build",
        )

        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Timeline built"
        assert data["case_id"] == case.id
        assert data["events_created"] == 2
        mock_service.build_timeline_for_case.assert_called_once()


def test_get_timeline_endpoint(db_session: Session):
    """Test get timeline endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for timeline")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="/tmp/test.db",
        sha256="a" * 64,
        evidence_type="file"
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add a WhatsApp message
    wa_msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="wa1",
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="Hello WhatsApp",
        timestamp=1609459200,
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    db_session.add(wa_msg)
    db_session.commit()

    # Build timeline via service (not mocked)
    from backend.services.timeline_service import timeline_service
    timeline_service.build_timeline_for_case(db_session, case.id)

    response = client.get(
        f"/api/timeline/cases/{case.id}/timeline",
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    event = data[0]
    assert event["case_id"] == case.id
    assert event["evidence_id"] == evidence.id
    assert event["event_type"] == "message"
    assert event["source_app"] == "whatsapp"
    assert event["description"] == "Hello WhatsApp"
    assert event["timestamp"] == 1609459200
    # normalized_timestamp should be ISO string
    assert "normalized_timestamp" in event


def test_filter_timeline_endpoint(db_session: Session):
    """Test filter timeline endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for timeline")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="/tmp/test.db",
        sha256="a" * 64,
        evidence_type="file"
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add two WhatsApp messages with different timestamps
    wa_msg1 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="wa1",
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="First message",
        timestamp=1609459200,  # 2021-01-01 00:00:00
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    wa_msg2 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="wa2",
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="Second message",
        timestamp=1609462800,  # 2021-01-01 01:00:00
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    db_session.add_all([wa_msg1, wa_msg2])
    db_session.commit()

    # Build timeline
    from backend.services.timeline_service import timeline_service
    timeline_service.build_timeline_for_case(db_session, case.id)

    # Filter by start_date (after first message)
    from datetime import datetime, timezone
    start_dt = datetime.fromtimestamp(1609460000, tz=timezone.utc)  # between the two messages

    response = client.post(
        f"/api/timeline/cases/{case.id}/timeline/filter",
        json={"start_date": start_dt.isoformat()}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1  # only second message
    event = data[0]
    assert event["description"] == "Second message"
    assert event["timestamp"] == 1609462800