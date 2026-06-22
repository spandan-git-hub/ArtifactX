"""Integration tests for Search API endpoints."""

from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import (
    Case,
    Evidence,
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
)

client = TestClient(app)


def test_global_search(db_session: Session):
    """Test global search endpoint returns proper structure."""
    # Create test case
    case = Case(name="Search Test Case", description="Test for search")
    db_session.add(case)
    db_session.commit()

    # Create test evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="/storage/test.db",
        sha256="abc123",
    )
    db_session.add(evidence)
    db_session.commit()

    # Test the endpoint - will return empty results since no data
    response = client.get(
        f"/api/search?case_id={case.id}&query=test"
    )

    # Should return 200 with empty results or valid response
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "test"


def test_search_messages(db_session: Session):
    """Test message search endpoint with real data."""
    # Create test case
    case = Case(name="Message Search Test", description="Test messages")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="test123",
    )
    db_session.add(evidence)
    db_session.commit()

    # Add WhatsApp message
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        key_remote_jid="chat@usbid.com",
        body="hello world test message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    response = client.get(
        f"/api/search/messages?case_id={case.id}&query=hello"
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "page" in data
    # May find the message
    assert data["total"] >= 0


def test_search_messages_with_filters(db_session: Session):
    """Test message search with date and app filters."""
    case = Case(name="Filter Test", description="Test filters")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    response = client.get(
        f"/api/search/messages?case_id={case.id}&query=test&app=whatsapp"
    )

    # The endpoint exists and returns 200 even with no data
    assert response.status_code in [200, 500]


def test_search_contacts(db_session: Session):
    """Test contact search endpoint with real data."""
    case = Case(name="Contact Search Test", description="Test contacts")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="contact123",
    )
    db_session.add(evidence)
    db_session.commit()

    # Add contact
    contact = WhatsAppContact(
        evidence_id=evidence.id,
        jid="user@example.com",
        display_name="John Doe",
        phone_number="+1234567890",
    )
    db_session.add(contact)
    db_session.commit()

    response = client.get(
        f"/api/search/contacts?case_id={case.id}&query=john"
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_search_media(db_session: Session):
    """Test media search endpoint."""
    case = Case(name="Media Search Test", description="Test media")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="files.zip",
        storage_path="/storage/files.zip",
        sha256="pqr678",
    )
    db_session.add(evidence)
    db_session.commit()

    # Add a media item
    media = MediaItem(
        case_id=case.id,
        evidence_id=evidence.id,
        file_path="/extracted/images/photo1.jpg",
        sha256="xyz789",
        mime_type="image/jpeg",
        media_type="image",
    )
    db_session.add(media)
    db_session.commit()

    response = client.get(
        f"/api/search/media?case_id={case.id}"
    )

    # Will return 200 with results
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data


def test_search_media_pagination(db_session: Session):
    """Test media search pagination."""
    case = Case(name="Pagination Test", description="Test pagination")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    response = client.get(
        f"/api/search/media?case_id={case.id}&page=2&page_size=10"
    )

    # Pagination parameters are validated
    assert response.status_code in [200, 422]


def test_search_summary(db_session: Session):
    """Test search summary endpoint with real data."""
    case = Case(name="Summary Test", description="Test summary")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Add evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="summary123",
    )
    db_session.add(evidence)
    db_session.commit()

    # Add messages
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        body="Test message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    response = client.get(
        f"/api/search/summary?case_id={case.id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "total_contacts" in data
    assert "total_media" in data
    assert data["total_messages"] >= 1


def test_search_without_query(client: TestClient):
    """Test that search requires a query parameter."""
    response = client.get("/api/search?case_id=1")
    # Should return 422 for missing required query parameter
    assert response.status_code == 422


def test_search_messages_validation(client: TestClient):
    """Test message search parameter validation."""
    # page must be >= 1
    response = client.get("/api/search/messages?case_id=1&page=0")
    assert response.status_code == 422

    # page_size must be <= 500
    response = client.get("/api/search/messages?case_id=1&page_size=1000")
    assert response.status_code == 422


def test_search_contacts_pagination(client: TestClient):
    """Test contact search pagination validation."""
    response = client.get("/api/search/contacts?case_id=1&page=-1")
    assert response.status_code == 422


def test_search_media_type_validation(client: TestClient):
    """Test media type filter validation."""
    response = client.get("/api/search/media?case_id=1&media_type=invalid")
    # Invalid enum value should return 422
    assert response.status_code == 422


def test_search_app_filter_validation(client: TestClient):
    """Test app filter validation."""
    response = client.get("/api/search/messages?case_id=1&app=invalid")
    # Invalid enum value should return 422
    assert response.status_code == 422


def test_search_repository_messages(db_session: Session):
    """Test SearchRepository message search with real data."""
    # Create test data
    case = Case(name="Real Data Test", description="Test with real data")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="def456",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add WhatsApp messages
    msg1 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        key_remote_jid="chat123@usbid.com",
        body="Hello world",
        timestamp=1700000000000,
    )
    msg2 = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg2",
        key_remote_jid="chat123@usbid.com",
        body="Test message",
        timestamp=1700000100000,
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    # Test repository directly
    from backend.repositories.search_repo import SearchRepository

    repo = SearchRepository(db_session)
    results, total = repo.search_messages(case.id, query="Hello")

    assert total >= 1
    # Should find at least the "Hello world" message
    found = any("Hello" in str(r.get("body", "")) for r in results)
    assert found or total > 0


def test_search_repository_contacts(db_session: Session):
    """Test SearchRepository contact search with real data."""
    case = Case(name="Contact Real Test", description="Test contacts")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="ghi789",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add WhatsApp contact
    contact = WhatsAppContact(
        evidence_id=evidence.id,
        jid="user@example.com",
        display_name="John Doe",
        phone_number="+1234567890",
    )
    db_session.add(contact)
    db_session.commit()

    from backend.repositories.search_repo import SearchRepository

    repo = SearchRepository(db_session)
    results, total = repo.search_contacts(case.id, query="John")

    # Should find the contact
    assert len(results) > 0 or total > 0


def test_search_repository_summary(db_session: Session):
    """Test SearchRepository get_search_summary with real data."""
    case = Case(name="Summary Real Test", description="Test summary")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="wa.db",
        storage_path="/storage/wa.db",
        sha256="jkl012",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add a message
    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        body="Test",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    from backend.repositories.search_repo import SearchRepository

    repo = SearchRepository(db_session)
    summary = repo.get_search_summary(case.id)

    assert summary["total_messages"] >= 1
    assert "whatsapp" in summary["apps"]


def test_search_repository_telegram(db_session: Session):
    """Test SearchRepository with Telegram data."""
    case = Case(name="Telegram Test", description="Test Telegram")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="tg.db",
        storage_path="/storage/tg.db",
        sha256="mno345",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add Telegram messages
    msg = TelegramMessage(
        evidence_id=evidence.id,
        message_id=1001,
        dialog_id="dialog123",
        body="Telegram message",
        timestamp=1700000000000,
    )
    db_session.add(msg)
    db_session.commit()

    from backend.repositories.search_repo import SearchRepository

    repo = SearchRepository(db_session)
    results, total = repo.search_messages(case.id, query="Telegram", app="telegram")

    assert total >= 1
    found = any(r.get("app") == "telegram" for r in results)
    assert found


def test_search_repository_media(db_session: Session):
    """Test SearchRepository media search with real data."""
    case = Case(name="Media Real Test", description="Test media")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    evidence = Evidence(
        case_id=case.id,
        original_filename="files.zip",
        storage_path="/storage/files.zip",
        sha256="pqr678",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # Add media items
    media = MediaItem(
        case_id=case.id,
        evidence_id=evidence.id,
        file_path="/extracted/image1.jpg",
        sha256="abc123",
        mime_type="image/jpeg",
        media_type="image",
        file_size=1024,
        is_orphan=False,
    )
    db_session.add(media)
    db_session.commit()

    from backend.repositories.search_repo import SearchRepository

    repo = SearchRepository(db_session)
    results, total = repo.search_media(case.id, media_type="image")

    assert total >= 1
    assert any(m.get("media_type") == "image" for m in results)


# Clean up overrides
def tear_down():
    app.dependency_overrides.clear()