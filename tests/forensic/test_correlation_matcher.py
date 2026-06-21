"""Tests for correlation matcher."""

from forensic.correlation.matcher import (
    correlate_message_to_contact_whatsapp,
    correlate_message_to_media_whatsapp,
    correlate_message_to_contact_telegram,
    correlate_message_to_media_telegram,
    correlate_cross_app_contact,
    correlate_all,
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
)


def test_correlate_message_to_contact_whatsapp():
    """Test correlating WhatsApp messages to contacts."""
    messages = [
        WhatsAppMessage(
            evidence_id=1,
            message_id="msg1",
            key_remote_jid="group1",
            sender_jid="user1@example.com",
            participant_jid="user2@example.com",
            body="Hello",
            timestamp=1000,
            media_type=None,
            media_path=None,
            message_type=None,
            status="read",
        )
    ]
    contacts = [
        WhatsAppContact(
            evidence_id=1,
            jid="user1@example.com",
            display_name="User One",
            phone_number="1234567890",
            status="active",
        ),
        WhatsAppContact(
            evidence_id=1,
            jid="user2@example.com",
            display_name="User Two",
            phone_number="0987654321",
            status="active",
        ),
    ]

    edges = correlate_message_to_contact_whatsapp(messages, contacts)

    # We expect two edges: one for sender and one for participant
    assert len(edges) == 2

    # Check the sender edge
    sender_edge = next(e for e in edges if e["target_id"] == "user1@example.com")
    assert sender_edge["source_type"] == "wa_message"
    assert sender_edge["source_id"] == "msg1"
    assert sender_edge["target_type"] == "wa_contact"
    assert sender_edge["relation_type"] == "sent_by"

    # Check the participant edge
    participant_edge = next(e for e in edges if e["target_id"] == "user2@example.com")
    assert participant_edge["relation_type"] == "participant_in"


def test_correlate_message_to_media_whatsapp():
    """Test correlating WhatsApp messages to media items."""
    messages = [
        WhatsAppMessage(
            evidence_id=1,
            message_id="msg1",
            key_remote_jid="user1@example.com",
            sender_jid="user1@example.com",
            participant_jid="user2@example.com",
            body="Hello",
            timestamp=1000,
            media_type="image",
            media_path="/path/to/media/image.jpg",
            message_type="image",
            status="read",
        )
    ]
    media_items = [
        MediaItem(
            evidence_id=1,
            file_path="/path/to/media/image.jpg",
            sha256="abc123",
            mime_type="image/jpeg",
            media_type="image",
            file_size=1000,
            width=800,
            height=600,
            duration=None,
            exif_data={},
            is_orphan=False,
            linked_message_id=None,
        )
    ]

    edges = correlate_message_to_media_whatsapp(messages, media_items)

    assert len(edges) == 1
    edge = edges[0]
    assert edge["source_type"] == "wa_message"
    assert edge["source_id"] == "msg1"
    assert edge["target_type"] == "media_item"
    assert edge["target_id"] == "/path/to/media/image.jpg"
    assert edge["relation_type"] == "contains_media"


def test_correlate_message_to_contact_telegram():
    """Test correlating Telegram messages to contacts."""
    messages = [
        TelegramMessage(
            evidence_id=1,
            message_id=100,
            dialog_id="dialog1",
            sender_id=12345,
            body="Hi",
            timestamp=2000,
            media_type=None,
            media_path=None,
            message_type=None,
        )
    ]
    contacts = [
        TelegramContact(
            evidence_id=1,
            user_id=12345,
            first_name="User",
            last_name="One",
            username="userone",
            phone="1234567890",
        )
    ]

    edges = correlate_message_to_contact_telegram(messages, contacts)

    assert len(edges) == 1
    edge = edges[0]
    assert edge["source_type"] == "tg_message"
    assert edge["source_id"] == "100"
    assert edge["target_type"] == "tg_contact"
    assert edge["target_id"] == "12345"
    assert edge["relation_type"] == "sent_by"


def test_correlate_message_to_media_telegram():
    """Test correlating Telegram messages to media items."""
    messages = [
        TelegramMessage(
            evidence_id=1,
            message_id=100,
            dialog_id="dialog1",
            sender_id=12345,
            body="Hi",
            timestamp=2000,
            media_type="video",
            media_path="/path/to/media/video.mp4",
            message_type="video",
        )
    ]
    media_items = [
        MediaItem(
            evidence_id=1,
            file_path="/path/to/media/video.mp4",
            sha256="def456",
            mime_type="video/mp4",
            media_type="video",
            file_size=2000,
            width=None,
            height=None,
            duration=120.0,
            exif_data={},
            is_orphan=False,
            linked_message_id=None,
        )
    ]

    edges = correlate_message_to_media_telegram(messages, media_items)

    assert len(edges) == 1
    edge = edges[0]
    assert edge["source_type"] == "tg_message"
    assert edge["source_id"] == "100"
    assert edge["target_type"] == "media_item"
    assert edge["target_id"] == "/path/to/media/video.mp4"
    assert edge["relation_type"] == "contains_media"


def test_correlate_cross_app_contact():
    """Test correlating contacts across WhatsApp and Telegram."""
    wa_contacts = [
        WhatsAppContact(
        evidence_id=1,
        jid="user1@example.com",
        display_name="User One",
        phone_number="1234567890",
        status="active",
        )
    ]
    tg_contacts = [
        TelegramContact(
            evidence_id=1,
            user_id=12345,
            first_name="User",
            last_name="One",
            username="userone",
            phone="1234567890",
        )
    ]

    edges = correlate_cross_app_contact(wa_contacts, tg_contacts)

    assert len(edges) == 1
    edge = edges[0]
    assert edge["source_type"] == "wa_contact"
    assert edge["source_id"] == "user1@example.com"
    assert edge["target_type"] == "tg_contact"
    assert edge["target_id"] == "12345"
    assert edge["relation_type"] == "matches_contact"


def test_correlate_all():
    """Test the combined correlation function."""
    wa_messages = [
        WhatsAppMessage(
            evidence_id=1,
            message_id="msg1",
            key_remote_jid="user1@example.com",
            sender_jid="user1@example.com",
            participant_jid="user2@example.com",
            body="Hello",
            timestamp=1000,
            media_type="image",
            media_path="/path/to/media/image.jpg",
            message_type="image",
            status="read",
        )
    ]
    wa_contacts = [
        WhatsAppContact(
            evidence_id=1,
            jid="user1@example.com",
            display_name="User One",
            phone_number="1234567890",
            status="active",
        ),
        WhatsAppContact(
            evidence_id=1,
            jid="user2@example.com",
            display_name="User Two",
            phone_number="0987654321",
            status="active",
        )
    ]
    tg_messages = [
        TelegramMessage(
            evidence_id=1,
            message_id=100,
            dialog_id="dialog1",
            sender_id=12345,
            body="Hi",
            timestamp=2000,
            media_type=None,
            media_path=None,
            message_type=None,
        )
    ]
    tg_contacts = [
        TelegramContact(
            evidence_id=1,
            user_id=12345,
            first_name="User",
            last_name="One",
            username="userone",
            phone="1234567890",
        )
    ]
    media_items = [
        MediaItem(
            evidence_id=1,
            file_path="/path/to/media/image.jpg",
            sha256="abc123",
            mime_type="image/jpeg",
            media_type="image",
            file_size=1000,
            width=800,
            height=600,
            duration=None,
            exif_data={},
            is_orphan=False,
            linked_message_id=None,
        )
    ]

    edges = correlate_all(wa_messages, wa_contacts, tg_messages, tg_contacts, media_items)

    # We expect:
    #   - wa_message to wa_contact (sent_by) for sender
    #   - wa_message to wa_contact (participant_in) for participant
    #   - wa_message to media_item (contains_media)
    #   - tg_message to tg_contact (sent_by)
    #   - wa_contact to tg_contact (matches_contact)
    #   - Note: tg_message has no media, so no media correlation for tg
    #
    #   Total: 5 edges.

    assert len(edges) == 5

    # Check that we have the cross app correlation
    cross_edge = next(e for e in edges if e["relation_type"] == "matches_contact")
    assert cross_edge["source_type"] == "wa_contact"
    assert cross_edge["target_type"] == "tg_contact"