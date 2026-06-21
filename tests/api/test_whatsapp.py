"""Integration tests for WhatsApp API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.models.models import Case, Evidence


client = TestClient(app)


def test_analyze_whatsapp_endpoint(db_session: Session):
    """Test WhatsApp analysis endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for WhatsApp")
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

    # Mock the WhatsApp service to avoid actual file processing
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_service.analyze_evidence.return_value = True

        response = client.post(
            f"/api/whatsapp/evidence/{evidence.id}/analyze/whatsapp",
        )

        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "WhatsApp analysis started"
        assert data["evidence_id"] == evidence.id
        mock_service.analyze_evidence.assert_called_once_with(evidence.id, db_session)


def test_analyze_whatsapp_endpoint_not_found(db_session: Session):
    """Test WhatsApp analysis endpoint with non-existent evidence."""
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_service.analyze_evidence.return_value = False

        response = client.post(
            "/api/whatsapp/evidence/999/analyze/whatsapp",
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Evidence not found or analysis failed"


def test_get_wa_messages_endpoint(db_session: Session):
    """Test getting WhatsApp messages endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for WhatsApp")
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

    # Mock the WhatsApp service
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_messages = [
            {
                "id": 1,
                "evidence_id": evidence.id,
                "message_id": "msg_1",
                "key_remote_jid": "123@s.whatsapp.net",
                "sender_jid": "123@s.whatsapp.net",
                "participant_jid": "123@s.whatsapp.net",
                "body": "Test message",
                "timestamp": 1625097600000,
                "media_type": "text",
                "media_path": None,
                "message_type": "text",
                "status": "1"
            }
        ]
        mock_service.get_messages.return_value = mock_messages

        response = client.get(f"/api/whatsapp/evidence/{evidence.id}/wa-messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["message_id"] == "msg_1"
        assert data[0]["body"] == "Test message"
        mock_service.get_messages.assert_called_once_with(evidence.id, db_session)


def test_get_wa_messages_endpoint_not_found(db_session: Session):
    """Test getting WhatsApp messages endpoint with non-existent evidence."""
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_service.get_messages.return_value = None

        response = client.get("/api/whatsapp/evidence/999/wa-messages")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Evidence not found"


def test_get_wa_contacts_endpoint(db_session: Session):
    """Test getting WhatsApp contacts endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for WhatsApp")
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

    # Mock the WhatsApp service
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_contacts = [
            {
                "id": 1,
                "evidence_id": evidence.id,
                "jid": "123@s.whatsapp.net",
                "display_name": "Test Contact",
                "phone_number": "+1234567890",
                "status": "0"
            }
        ]
        mock_service.get_contacts.return_value = mock_contacts

        response = client.get(f"/api/whatsapp/evidence/{evidence.id}/wa-contacts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Test Contact"
        mock_service.get_contacts.assert_called_once_with(evidence.id, db_session)


def test_get_wa_groups_endpoint(db_session: Session):
    """Test getting WhatsApp groups endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for WhatsApp")
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

    # Mock the WhatsApp service
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_groups = [
            {
                "id": 1,
                "evidence_id": evidence.id,
                "group_jid": "group@g.us",
                "subject": "Test Group",
                "creator_jid": "creator@s.whatsapp.net",
                "creation_timestamp": 1625097500000
            }
        ]
        mock_service.get_groups.return_value = mock_groups

        response = client.get(f"/api/whatsapp/evidence/{evidence.id}/wa-groups")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Test Group"
        mock_service.get_groups.assert_called_once_with(evidence.id, db_session)


def test_get_wa_media_endpoint(db_session: Session):
    """Test getting WhatsApp media endpoint."""
    # Create test case and evidence
    case = Case(name="Test Case", description="Test case for WhatsApp")
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

    # Mock the WhatsApp service
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_media = [
            {
                "message_id": "msg_1",
                "media_path": "/tmp/image.jpg",
                "media_type": "image",
                "file_size": 1024,
                "width": 800,
                "height": 600,
                "duration": None
            }
        ]
        mock_service.get_media_references.return_value = mock_media

        response = client.get(f"/api/whatsapp/evidence/{evidence.id}/wa-media")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["media_type"] == "image"
        assert data[0]["file_size"] == 1024
        mock_service.get_media_references.assert_called_once_with(evidence.id, db_session)


def test_get_wa_media_endpoint_not_found(db_session: Session):
    """Test getting WhatsApp media endpoint with non-existent evidence."""
    with patch('backend.services.whatsapp_service.whatsapp_service') as mock_service:
        mock_service.get_media_references.return_value = None

        response = client.get("/api/whatsapp/evidence/999/wa-media")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Evidence not found"


# Clean up overrides
def tear_down():
    app.dependency_overrides.clear()