"""Test database models and basic connectivity."""

from datetime import datetime

from backend.models.models import (
    ActivityLog,
    AnalysisLog,
    AnalysisResult,
    Case,
    CorrelationEdge,
    DeletedMessage,
    Evidence,
    EvidenceFile,
    MediaItem,
    TelegramContact,
    TelegramGroup,
    TelegramMessage,
    TimelineEvent,
    WhatsAppContact,
    WhatsAppGroup,
    WhatsAppMessage,
)


def test_create_case(db_session):
    case = Case(name="Test Case", description="A test case", investigator="Test User")
    db_session.add(case)
    db_session.commit()

    result = db_session.query(Case).filter(Case.name == "Test Case").first()
    assert result is not None
    assert result.id is not None
    assert result.status == "open"
    assert isinstance(result.created_at, datetime)


def test_create_evidence(db_session):
    case = Case(name="Evidence Test Case")
    db_session.add(case)
    db_session.commit()

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.zip",
        storage_path="uploads/test.zip",
        sha256="a" * 64,
    )
    db_session.add(evidence)
    db_session.commit()

    result = db_session.query(Evidence).filter(Evidence.case_id == case.id).first()
    assert result is not None
    assert result.original_filename == "test.zip"
    assert result.case.name == "Evidence Test Case"


def test_cascade_delete_case(db_session):
    case = Case(name="Cascade Test")
    db_session.add(case)
    db_session.commit()

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.zip",
        storage_path="uploads/test.zip",
        sha256="b" * 64,
    )
    db_session.add(evidence)
    db_session.commit()

    assert db_session.query(Evidence).count() == 1

    db_session.delete(case)
    db_session.commit()

    assert db_session.query(Case).count() == 0
    assert db_session.query(Evidence).count() == 0


def test_whatsapp_message(db_session):
    case = Case(name="WA Test")
    db_session.add(case)
    db_session.commit()

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="uploads/test.db",
        sha256="c" * 64,
    )
    db_session.add(evidence)
    db_session.commit()

    msg = WhatsAppMessage(
        evidence_id=evidence.id,
        message_id="msg1",
        key_remote_jid="12345@s.whatsapp.net",
        body="Hello World",
        timestamp=1625097600000,
    )
    db_session.add(msg)
    db_session.commit()

    result = db_session.query(WhatsAppMessage).first()
    assert result.body == "Hello World"


def test_telegram_message(db_session):
    case = Case(name="TG Test")
    db_session.add(case)
    db_session.commit()

    evidence = Evidence(
        case_id=case.id,
        original_filename="test.db",
        storage_path="uploads/test.db",
        sha256="d" * 64,
    )
    db_session.add(evidence)
    db_session.commit()

    msg = TelegramMessage(
        evidence_id=evidence.id,
        message_id=1,
        dialog_id="chat_123",
        body="Hello from Telegram",
        timestamp=1625097600000,
    )
    db_session.add(msg)
    db_session.commit()

    result = db_session.query(TelegramMessage).first()
    assert result.body == "Hello from Telegram"


def test_timeline_event(db_session):
    case = Case(name="Timeline Test")
    db_session.add(case)
    db_session.commit()

    event = TimelineEvent(
        case_id=case.id,
        event_type="message",
        source_app="whatsapp",
        timestamp=1625097600000,
        description="Test event",
    )
    db_session.add(event)
    db_session.commit()

    result = db_session.query(TimelineEvent).first()
    assert result.event_type == "message"
    assert result.source_app == "whatsapp"


def test_deleted_message(db_session):
    case = Case(name="Deleted Test")
    db_session.add(case)
    db_session.commit()

    deleted = DeletedMessage(
        case_id=case.id,
        source_app="whatsapp",
        chat_jid="12345@s.whatsapp.net",
        gap_start=10,
        gap_end=20,
        missing_count=5,
        confidence_score=0.85,
        detection_method="sequence_gap",
    )
    db_session.add(deleted)
    db_session.commit()

    result = db_session.query(DeletedMessage).first()
    assert result.missing_count == 5
    assert result.confidence_score == 0.85


def test_media_item(db_session):
    case = Case(name="Media Test")
    db_session.add(case)
    db_session.commit()

    media = MediaItem(
        case_id=case.id,
        file_path="uploads/image.jpg",
        mime_type="image/jpeg",
        media_type="image",
        width=1920,
        height=1080,
    )
    db_session.add(media)
    db_session.commit()

    result = db_session.query(MediaItem).first()
    assert result.media_type == "image"
    assert result.width == 1920


def test_correlation_edge(db_session):
    case = Case(name="Correlation Test")
    db_session.add(case)
    db_session.commit()

    edge = CorrelationEdge(
        case_id=case.id,
        source_type="message",
        target_type="contact",
        source_id="msg_1",
        target_id="contact_1",
        relation_type="sent_by",
    )
    db_session.add(edge)
    db_session.commit()

    result = db_session.query(CorrelationEdge).first()
    assert result.relation_type == "sent_by"


def test_analysis_log(db_session):
    log = AnalysisLog(
        log_type="analysis",
        message="Analysis started",
    )
    db_session.add(log)
    db_session.commit()

    result = db_session.query(AnalysisLog).first()
    assert result.log_type == "analysis"


def test_activity_log(db_session):
    case = Case(name="Activity Test")
    db_session.add(case)
    db_session.commit()

    log = ActivityLog(
        case_id=case.id,
        action="case_created",
        description="Case was created",
    )
    db_session.add(log)
    db_session.commit()

    result = db_session.query(ActivityLog).first()
    assert result.action == "case_created"
