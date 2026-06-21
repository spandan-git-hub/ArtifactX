"""Integration tests for Deleted Message API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.models.models import Case, Evidence, WhatsAppMessage, TelegramMessage, DeletedMessage

client = TestClient(app)


def test_detect_deletions_endpoint(db_session: Session):
    """Test deleted message detection endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for deleted messages")
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

    # Add some WhatsApp and Telegram messages with gaps
    wa_msg1 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="100",
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="First message",
        timestamp=1609459200,  # 2021-01-01 00:00:00 UTC
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    wa_msg2 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="105",  # Gap of 4 messages (101-104 missing)
        key_remote_jid="user@example.com",
        sender_jid="user@example.com",
        participant_jid="user@example.com",
        body="Sixth message",
        timestamp=1609459260,  # 2021-01-01 00:01:00 UTC
        media_type=None,
        media_path=None,
        message_type="text",
        status="delivered"
    )
    tg_msg1 = TelegramMessage(
        evidence_id=evidence.id,
        message_id=200,
        dialog_id="chat1",
        sender_id=12345,
        body="First Telegram message",
        timestamp=1609459320,  # 2021-01-01 00:02:00 UTC
        media_type=None,
        media_path=None,
        message_type="text"
    )
    tg_msg2 = TelegramMessage(
        evidence_id=evidence.id,
        message_id=203,  # Gap of 2 messages (201-202 missing)
        dialog_id="chat1",
        sender_id=12345,
        body="Fourth Telegram message",
        timestamp=1609459380,  # 2021-01-01 00:03:00 UTC
        media_type=None,
        media_path=None,
        message_type="text"
    )
    db_session.add_all([wa_msg1, wa_msg2, tg_msg1, tg_msg2])
    db_session.commit()

    # Mock the deleted service in the API module
    with patch('backend.api.deleted.deleted_service') as mock_service:
        mock_service.detect_deletions_for_case.return_value = 2  # Two deletions detected

        response = client.post(
            f"/api/deleted/cases/{case.id}/deleted/detect",
        )

        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Deleted message detection completed"
        assert data["case_id"] == case.id
        assert data["deletions_detected"] == 2
        mock_service.detect_deletions_for_case.assert_called_once()


def test_get_deleted_messages_endpoint(db_session: Session):
    """Test get deleted messages endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for deleted messages")
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

    # Add a deleted message record
    deleted_msg = DeletedMessage(
        case_id=case.id,
        evidence_id=evidence.id,
        source_app="whatsapp",
        chat_jid="user@example.com",
        gap_start=101,
        gap_end=104,
        missing_count=4,
        confidence_score=0.85,
        detection_method="sequence_gap_analysis"
    )
    db_session.add(deleted_msg)
    db_session.commit()

    response = client.get(
        f"/api/deleted/cases/{case.id}/deleted",
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    deleted_data = data[0]
    assert deleted_data["case_id"] == case.id
    assert deleted_data["evidence_id"] == evidence.id
    assert deleted_data["source_app"] == "whatsapp"
    assert deleted_data["chat_jid"] == "user@example.com"
    assert deleted_data["gap_start"] == 101
    assert deleted_data["gap_end"] == 104
    assert deleted_data["missing_count"] == 4
    assert deleted_data["confidence_score"] == 0.85
    assert deleted_data["detection_method"] == "sequence_gap_analysis"
    assert "detected_at" in deleted_data


def test_get_deleted_messages_endpoint_not_found(db_session: Session):
    """Test get deleted messages endpoint with non-existent case."""
    response = client.get("/api/deleted/cases/999/deleted")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Case not found"