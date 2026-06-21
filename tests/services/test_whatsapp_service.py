"""Service tests for WhatsApp analysis."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from backend.services.whatsapp_service import WhatsAppService
from backend.app.config import UPLOADS_DIR


def test_whatsapp_service_init():
    """Test WhatsAppService initialization."""
    service = WhatsAppService()
    assert service.repository is not None


def test_analyze_evidence_success():
    """Test successful evidence analysis."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()

    # Mock evidence
    mock_evidence = MagicMock()
    mock_evidence.id = 1
    mock_evidence.extracted_path = None
    mock_evidence.storage_path = "/tmp/test.db"

    mock_db.query.return_value.filter.return_value.first.return_value = mock_evidence

    # Mock the file path existence check
    with patch('backend.services.whatsapp_service.Path') as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        # Mock the database detector
        with patch('backend.services.whatsapp_service.is_whatsapp_database') as mock_is_whatsapp:
            mock_is_whatsapp.return_value = True

            # Mock the background analysis - simplified since we removed the async complexity
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = MagicMock()
                mock_get_loop.return_value = mock_loop

                # Call the method
                import asyncio
                result = asyncio.run(service.analyze_evidence(1, mock_db))

                # Verify
                assert result is True
                mock_db.commit.assert_called()
                assert mock_evidence.analyzed_at is not None


def test_analyze_evidence_not_found():
    """Test analysis with non-existent evidence."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Call the method
    import asyncio
    result = asyncio.run(service.analyze_evidence(999, mock_db))

    # Verify
    assert result is False
    mock_db.commit.assert_not_called()


def test_analyze_evidence_not_whatsapp_db():
    """Test analysis with non-WhatsApp database."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()

    # Mock evidence
    mock_evidence = MagicMock()
    mock_evidence.id = 1
    mock_evidence.extracted_path = None
    mock_evidence.storage_path = "/tmp/test.db"

    mock_db.query.return_value.filter.return_value.first.return_value = mock_evidence

    # Mock the file path existence check
    with patch('backend.services.whatsapp_service.Path') as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        # Mock the database detector to return False
        with patch('backend.services.whatsapp_service.is_whatsapp_database') as mock_is_whatsapp:
            mock_is_whatsapp.return_value = False

            # Call the method
            import asyncio
            result = asyncio.run(service.analyze_evidence(1, mock_db))

            # Verify
            assert result is False
            mock_db.commit.assert_not_called()


def test_get_messages():
    """Test getting messages."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()

    # Mock evidence
    mock_evidence = MagicMock()
    mock_evidence.id = 1

    mock_db.query.return_value.filter.return_value.first.return_value = mock_evidence

    # Mock repository
    with patch.object(service.repository, 'get_messages_by_evidence_id') as mock_repo_method:
        mock_repo_method.return_value = [{"id": 1, "message_id": "msg_1"}]

        # Call the method
        result = service.get_messages(1, mock_db)

        # Verify
        assert result == [{"id": 1, "message_id": "msg_1"}]
        mock_repo_method.assert_called_once_with(mock_db, 1)


def test_get_messages_not_found():
    """Test getting messages for non-existent evidence."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Mock repository
    with patch.object(service.repository, 'get_messages_by_evidence_id') as mock_repo_method:
        # Call the method
        result = service.get_messages(999, mock_db)

        # Verify
        assert result is None
        mock_repo_method.assert_not_called()


def test_get_media_references():
    """Test getting media references."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()

    # Mock evidence
    mock_evidence = MagicMock()
    mock_evidence.id = 1

    mock_db.query.return_value.filter.return_value.first.return_value = mock_evidence

    # Mock repository
    with patch.object(service.repository, 'get_messages_by_evidence_id') as mock_repo_method:
        mock_repo_method.return_value = [
            MagicMock(message_id="msg_1", media_path="/tmp/image.jpg", media_type="image"),
            MagicMock(message_id="msg_2", media_path=None, media_type=None)
        ]

        # Call the method
        result = service.get_media_references(1, mock_db)

        # Verify
        assert len(result) == 1  # Only one with media_path
        assert result[0]["message_id"] == "msg_1"
        assert result[0]["media_path"] == "/tmp/image.jpg"
        assert result[0]["media_type"] == "image"


# Additional test for the background analysis method
def test_perform_analysis():
    """Test the background analysis method."""
    service = WhatsAppService()

    # Mock database session
    mock_db = MagicMock()

    # Mock parsers return values
    mock_messages = [{"evidence_id": 1, "message_id": "msg_1"}]
    mock_contacts = [{"evidence_id": 1, "jid": "contact_1"}]
    mock_groups = [{"evidence_id": 1, "group_jid": "group_1"}]

    with patch('backend.services.whatsapp_service.extract_messages') as mock_extract_messages, \
         patch('backend.services.whatsapp_service.extract_contacts') as mock_extract_contacts, \
         patch('backend.services.whatsapp_service.extract_groups') as mock_extract_groups:

        mock_extract_messages.return_value = mock_messages
        mock_extract_contacts.return_value = mock_contacts
        mock_extract_groups.return_value = mock_groups

        # Mock repository
        with patch.object(service.repository, 'save_messages') as mock_save_messages, \
             patch.object(service.repository, 'save_contacts') as mock_save_contacts, \
             patch.object(service.repository, 'save_groups') as mock_save_groups:

            # Call the method
            service._perform_analysis(1, Path("/tmp/test.db"), mock_db)

            # Verify parsers were called
            mock_extract_messages.assert_called_once_with(Path("/tmp/test.db"), 1)
            mock_extract_contacts.assert_called_once_with(Path("/tmp/test.db"), 1)
            mock_extract_groups.assert_called_once_with(Path("/tmp/test.db"), 1)

            # Verify repository methods were called
            mock_save_messages.assert_called_once_with(mock_db, mock_messages)
            mock_save_contacts.assert_called_once_with(mock_db, mock_contacts)
            mock_save_groups.assert_called_once_with(mock_db, mock_groups)