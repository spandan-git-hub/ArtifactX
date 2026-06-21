"""Service tests for correlation service."""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.correlation_service import correlation_service
from forensic.correlation.matcher import (
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
)


def test_correlation_service_init():
    """Test CorrelationService initialization."""
    service = correlation_service
    assert service.correlation_repo is not None
    assert service.whatsapp_repo is not None
    assert service.telegram_repo is not None
    assert service.media_repo is not None


def test_correlate_case_success():
    """Test successful correlation for a case."""
    service = correlation_service

    # Mock database session
    mock_db = MagicMock()

    # Mock case existence
    mock_case = MagicMock()
    mock_case.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_case

    # Mock evidences for the case
    mock_evidence1 = MagicMock()
    mock_evidence1.id = 1
    mock_evidence1.case_id = 1
    mock_evidence2 = MagicMock()
    mock_evidence2.id = 2
    mock_evidence2.case_id = 1

    # We need to mock the chain: db.query(Evidence).filter(Evidence.case_id == case_id).all()
    # We'll set up the mock for the query to return a mock that when filtered returns a mock that when all() returns the list.
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [mock_evidence1, mock_evidence2]
    mock_db.query.return_value = mock_query

    # Mock WhatsApp repositories
    with patch.object(service.whatsapp_repo, 'get_messages_by_evidence_id') as mock_wa_msgs, \
         patch.object(service.whatsapp_repo, 'get_contacts_by_evidence_id') as mock_wa_contacts:

        # WhatsApp evidence 1
        mock_wa_msgs.side_effect = lambda evidence_id: [
            WhatsAppMessage(
                evidence_id=evidence_id,
                message_id=f"wa_msg{evidence_id}",
                key_remote_jid=f"user{evidence_id}@example.com",
                sender_jid=f"user{evidence_id}@example.com",
                participant_jid=f"user{evidence_id+1}@example.com",
                body="Hello",
                timestamp=1000 * evidence_id,
                media_type="image" if evidence_id == 1 else None,
                media_path=f"/path/to/media/image{evidence_id}.jpg" if evidence_id == 1 else None,
                message_type="image" if evidence_id == 1 else None,
                status="read",
            )
        ] if evidence_id in [1, 2] else []

        mock_wa_contacts.side_effect = lambda evidence_id: [
            WhatsAppContact(
                evidence_id=evidence_id,
                jid=f"user{evidence_id}@example.com",
                display_name=f"User {evidence_id}",
                phone_number=f"{evidence_id}111111111",
                status="active",
            ),
            WhatsAppContact(
                evidence_id=evidence_id,
                jid=f"user{evidence_id+1}@example.com",
                display_name=f"User {evidence_id+1}",
                phone_number=f"{evidence_id+1}111111111",
                status="active",
            )
        ] if evidence_id in [1, 2] else []

    # Mock Telegram repositories
    with patch.object(service.telegram_repo, 'get_messages_by_evidence_id') as mock_tg_msgs, \
         patch.object(service.telegram_repo, 'get_contacts_by_evidence_id') as mock_tg_contacts:

        mock_tg_msgs.side_effect = lambda evidence_id: [
            TelegramMessage(
                evidence_id=evidence_id,
                message_id=evidence_id * 100,
                dialog_id=f"dialog{evidence_id}",
                sender_id=evidence_id * 11111,
                body="Hi",
                timestamp=2000 * evidence_id,
                media_type=None,
                media_path=None,
                message_type=None,
            )
        ] if evidence_id in [1, 2] else []

        mock_tg_contacts.side_effect = lambda evidence_id: [
            TelegramContact(
                evidence_id=evidence_id,
                user_id=evidence_id * 11111,
                first_name="Telegram",
                last_name=f"User{evidence_id}",
                username=f"tguser{evidence_id}",
                phone=f"{evidence_id}111111111",  # Same as WhatsApp user
            )
        ] if evidence_id in [1, 2] else []

    # Mock Media repository
    with patch.object(service.media_repo, 'get_media_items_by_evidence_id') as mock_media:

        mock_media.side_effect = lambda evidence_id: [
            MediaItem(
                evidence_id=evidence_id,
                file_path=f"/path/to/media/image{evidence_id}.jpg",
                sha256=f"sha{evidence_id}",
                mime_type="image/jpeg",
                media_type="image",
                file_size=1000,
                width=800,
                height=600,
                duration=None,
                exif_data={},
                is_orphan=False,
                linked_message_id=f"wa_msg{evidence_id}",
            )
        ] if evidence_id == 1 else []  # Only evidence 1 has media

    # Mock correlation repository
    with patch.object(service.correlation_repo, 'save_edges') as mock_save_edges, \
         patch.object(service.correlation_repo, 'delete_edges_by_case_id') as mock_delete_edges:

        # Call the method
        edge_count = service.correlate_case(mock_db, 1)

        # Verify
        assert edge_count > 0  # We expect some edges to be created
        mock_delete_edges.assert_called_once_with(mock_db, 1)
        mock_save_edges.assert_called_once()

        # Check that the edges passed to save_edges have case_id=1
        args, kwargs = mock_save_edges.call_args
        edges_passed = args[0]  # First argument is the list of edges
        for edge in edges_passed:
            assert edge["case_id"] == 1


def test_correlate_case_no_case():
    """Test correlation when case does not exist."""
    service = correlation_service

    # Mock database session
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Call the method
    edge_count = service.correlate_case(mock_db, 999)

    # Verify
    assert edge_count == 0
    # No correlation edges should be deleted or saved
    service.correlation_repo.delete_edges_by_case_id.assert_not_called()
    service.correlation_repo.save_edges.assert_not_called()


def test_get_edges_for_case():
    """Test getting edges for a case."""
    service = correlation_service

    # Mock database session
    mock_db = MagicMock()

    # Mock case existence
    mock_case = MagicMock()
    mock_case.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_case

    # Mock correlation repository
    with patch.object(service.correlation_repo, 'get_edges_by_case_id') as mock_get_edges:
        mock_get_edges.return_value = [
            MagicMock(
                id=1,
                case_id=1,
                source_type="wa_message",
                source_id="msg1",
                target_type="wa_contact",
                target_id="user1@example.com",
                relation_type="sent_by",
                metadata_={},
            )
        ]

        # Call the method
        edges = service.get_edges_for_case(mock_db, 1)

        # Verify
        assert len(edges) == 1
        assert edges[0]["id"] == 1
        assert edges[0]["case_id"] == 1
        assert edges[0]["source_type"] == "wa_message"
        assert edges[0]["source_id"] == "msg1"
        assert edges[0]["target_type"] == "wa_contact"
        assert edges[0]["target_id"] == "user1@example.com"
        assert edges[0]["relation_type"] == "sent_by"
        mock_get_edges.assert_called_once_with(mock_db, 1)