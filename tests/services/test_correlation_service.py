"""Service tests for correlation service."""

from unittest.mock import MagicMock, patch

from backend.services.correlation_service import CorrelationService


def test_correlation_service_init():
    """Test CorrelationService initialization."""
    service = CorrelationService()
    assert service.correlation_repo is not None
    assert service.whatsapp_repo is not None
    assert service.telegram_repo is not None
    assert service.media_repo is not None


class MockModel:
    """Helper to create model-like mocks with specified attributes."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_correlate_case_success():
    """Test successful correlation for a case."""
    service = CorrelationService()

    # Mock database session - evidence query chain
    mock_evidences = MagicMock()
    mock_evidences.all.return_value = [
        MockModel(id=1, case_id=1),
    ]
    mock_evidences.filter.return_value = mock_evidences
    mock_db = MagicMock()
    mock_db.query.return_value = mock_evidences

    # Mock WhatsApp messages
    wa_msg1 = MockModel(
        evidence_id=1,
        message_id="wa_msg_1",
        key_remote_jid="user1@example.com",
        sender_jid="user1@example.com",
        participant_jid="",
        body="Hello from WA",
        timestamp=1000,
        media_type=None,
        media_path=None,
        message_type="text",
        status="read",
    )

    # Mock WhatsApp contacts
    wa_contact1 = MockModel(
        evidence_id=1,
        jid="user1@example.com",
        display_name="User One",
        phone_number="11111111111",
        status="active",
    )

    # Mock Telegram messages
    tg_msg1 = MockModel(
        evidence_id=1,
        message_id=200,
        dialog_id="dialog1",
        sender_id=22222,
        body="Hello from TG",
        timestamp=2000,
        media_type=None,
        media_path=None,
        message_type="text",
    )

    # Mock Telegram contacts
    tg_contact1 = MockModel(
        evidence_id=1,
        user_id=22222,
        first_name="User",
        last_name="Two",
        username="usertwo",
        phone="11111111111",
    )

    # Mock media items
    media1 = MockModel(
        evidence_id=1,
        file_path="/path/to/image.jpg",
        sha256="sha256abc",
        mime_type="image/jpeg",
        media_type="image",
        file_size=1024,
        width=800,
        height=600,
        duration=None,
        exif_data={},
        is_orphan=False,
        linked_message_id=None,
    )

    # Set up all patches to be active at the same time
    with (patch.object(service.whatsapp_repo, 'get_messages_by_evidence_id') as mock_wa_msgs,
         patch.object(service.whatsapp_repo, 'get_contacts_by_evidence_id') as mock_wa_contacts,
         patch.object(service.telegram_repo, 'get_messages_by_evidence_id') as mock_tg_msgs,
         patch.object(service.telegram_repo, 'get_contacts_by_evidence_id') as mock_tg_contacts,
         patch.object(service.media_repo, 'get_media_items_by_evidence_id') as mock_media,
         patch.object(service.correlation_repo, 'save_edges') as mock_save_edges,
         patch.object(service.correlation_repo, 'delete_edges_by_case_id') as mock_delete_edges):

        mock_wa_msgs.return_value = [wa_msg1]
        mock_wa_contacts.return_value = [wa_contact1]
        mock_tg_msgs.return_value = [tg_msg1]
        mock_tg_contacts.return_value = [tg_contact1]
        mock_media.return_value = [media1]

        # Call the method
        edge_count = service.correlate_case(mock_db, 1)

        # Verify
        assert edge_count > 0  # Edges should be created
        mock_delete_edges.assert_called_once_with(mock_db, 1)
        mock_save_edges.assert_called_once()

        # Check that the edges passed to save_edges have case_id=1
        args, kwargs = mock_save_edges.call_args
        edges_passed = args[0]  # First argument is the list of edges
        for edge in edges_passed:
            assert edge["case_id"] == 1


def test_correlate_case_no_evidence():
    """Test correlation when case has no evidence."""
    service = CorrelationService()

    # Mock database session
    mock_db = MagicMock()

    # Mock query chain: db.query(Evidence).filter(...).all() returns []
    mock_evidences = MagicMock()
    mock_evidences.all.return_value = []
    mock_evidences.filter.return_value = mock_evidences
    mock_db.query.return_value = mock_evidences

    with patch.object(service.correlation_repo, 'delete_edges_by_case_id') as mock_delete_edges:
        # Call the method
        edge_count = service.correlate_case(mock_db, 1)

        # Verify
        assert edge_count == 0
        mock_delete_edges.assert_called_once_with(mock_db, 1)


def test_correlate_case_empty_data():
    """Test correlation when evidence has no data."""
    service = CorrelationService()

    # Mock database session
    mock_db = MagicMock()
    mock_evidences = MagicMock()
    mock_evidences.all.return_value = [MockModel(id=1, case_id=1)]
    mock_evidences.filter.return_value = mock_evidences
    mock_db.query.return_value = mock_evidences

    # All repos return empty lists
    with patch.object(service.whatsapp_repo, 'get_messages_by_evidence_id', return_value=[]), \
         patch.object(service.whatsapp_repo, 'get_contacts_by_evidence_id', return_value=[]), \
         patch.object(service.telegram_repo, 'get_messages_by_evidence_id', return_value=[]), \
         patch.object(service.telegram_repo, 'get_contacts_by_evidence_id', return_value=[]), \
         patch.object(service.media_repo, 'get_media_items_by_evidence_id', return_value=[]), \
         patch.object(service.correlation_repo, 'save_edges') as mock_save_edges, \
         patch.object(service.correlation_repo, 'delete_edges_by_case_id') as mock_delete_edges:

        edge_count = service.correlate_case(mock_db, 1)

        assert edge_count == 0
        mock_delete_edges.assert_called_once_with(mock_db, 1)
        # save_edges takes db as first arg, then edges list
        mock_save_edges.assert_called_once()


def test_get_edges_for_case():
    """Test getting edges for a case."""
    service = CorrelationService()

    # Mock database session
    mock_db = MagicMock()

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


def test_get_edges_for_case_empty():
    """Test getting edges when no edges exist."""
    service = CorrelationService()
    mock_db = MagicMock()

    with patch.object(service.correlation_repo, 'get_edges_by_case_id') as mock_get_edges:
        mock_get_edges.return_value = []
        edges = service.get_edges_for_case(mock_db, 1)
        assert edges == []
