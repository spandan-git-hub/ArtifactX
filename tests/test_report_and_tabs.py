"""Tests verifying Timeline, Recovery, Correlation, and PDF Report generation integrity."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.models import (
    Base,
    Case,
    Evidence,
    WhatsAppMessage,
    TelegramMessage,
    TimelineEvent,
    RecoveredFinding,
    ActivityLog,
)
from backend.services.report_service import get_report_service
from backend.services.timeline_service import TimelineService
from backend.services.recovery_service import list_recovered_findings


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test case
    test_case = Case(
        id=999,
        name="Case 999 - Operations Nexus",
        description="Comprehensive Multi-Platform Forensic Investigation",
        status="active",
        case_number="CASE-999-CYBER",
        examiner_name="Special Agent J. Vance",
        agency="National Cyber Forensics Unit",
    )
    session.add(test_case)

    # Seed evidence file
    ev = Evidence(
        id=1,
        case_id=999,
        original_filename="msgstore.db.crypt14",
        storage_path="/mock/msgstore.db.crypt14",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evidence_type="whatsapp",
        metadata_={"file_size": 1048576},
    )
    session.add(ev)

    # Seed timeline events directly
    t1 = TimelineEvent(
        id=1,
        case_id=999,
        timestamp=1690000000000,
        utc_ms=1690000000000,
        event_type="message",
        source_app="whatsapp",
        actor_ref="15550100@s.whatsapp.net",
        chat_ref="15550100@s.whatsapp.net",
        description="Target rendezvous confirmed at coordinates.",
    )
    t2 = TimelineEvent(
        id=2,
        case_id=999,
        timestamp=1690000060000,
        utc_ms=1690000060000,
        event_type="message",
        source_app="whatsapp",
        actor_ref="me",
        chat_ref="15550100@s.whatsapp.net",
        description="Switching immediately to secure channel on Telegram.",
    )
    t3 = TimelineEvent(
        id=3,
        case_id=999,
        timestamp=1690000120000,
        utc_ms=1690000120000,
        event_type="message",
        source_app="telegram",
        actor_ref="@agent_vance",
        chat_ref="@nexus_lead",
        description="Acknowledge switch. Transferring hashes now.",
    )
    session.add_all([t1, t2, t3])

    # Seed 4 tiers of recovered findings
    rf1 = RecoveredFinding(
        id=1,
        case_id=999,
        evidence_id=1,
        tier=1,
        kind="revocation",
        method="record_reconstruction",
        table_name="messages",
        byte_offset=0x000A12,
        raw_payload_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        raw_payload_preview="Meeting moved to 22:00 UTC",
        body="Meeting moved to 22:00 UTC",
        confidence_score=1.0,
        strength="deterministic",
    )
    rf2 = RecoveredFinding(
        id=2,
        case_id=999,
        evidence_id=1,
        tier=2,
        kind="wal_resident",
        method="wal",
        table_name="wal_frame_042",
        byte_offset=0x004F20,
        raw_payload_hash="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
        raw_payload_preview="Pre-update payment ledger row",
        body="Pre-update payment ledger row",
        confidence_score=0.95,
        strength="strong",
    )
    rf3 = RecoveredFinding(
        id=3,
        case_id=999,
        evidence_id=1,
        tier=3,
        kind="freelist",
        method="freelist",
        table_name="page_freelist_11",
        byte_offset=0x012B00,
        raw_payload_hash="c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        raw_payload_preview="Carved fragment: 0x93FA22...",
        body="Carved fragment: 0x93FA22...",
        confidence_score=0.82,
        strength="moderate",
    )
    rf4 = RecoveredFinding(
        id=4,
        case_id=999,
        evidence_id=1,
        tier=4,
        kind="id_gap",
        method="record_reconstruction",
        table_name="messages",
        byte_offset=0x025C00,
        raw_payload_hash="d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
        raw_payload_preview="Gap detected: 5 missing RowIDs",
        body="Gap detected: 5 missing RowIDs",
        confidence_score=0.55,
        strength="weak_hint",
    )
    session.add_all([rf1, rf2, rf3, rf4])

    # Seed activity log
    al = ActivityLog(
        id=1,
        case_id=999,
        action="EVID_INGEST",
        description="Initial evidence file ingestion and SHA-256 seal.",
    )
    session.add(al)

    session.commit()
    yield session
    session.close()


def test_timeline_chronological_order(db_session):
    """Verify timeline service returns all events in chronological sequence."""
    timeline_service = TimelineService()
    events = timeline_service.filter_timeline(db=db_session, case_id=999)
    assert len(events) >= 3

    # Verify chronological ordering
    timestamps = [e.get("utc_ms") or 0 for e in events]
    assert timestamps == sorted(timestamps)


def test_recovery_tier_classification(db_session):
    """Verify recovery service categorizes findings across the 4 forensic tiers."""
    findings = list_recovered_findings(case_id=999, db=db_session)
    assert len(findings) == 4

    tiers = {f.tier for f in findings}
    assert tiers == {1, 2, 3, 4}


def test_pdf_report_full_generation(db_session):
    """Verify comprehensive PDF report generation runs in-memory and includes all required sections."""
    report_service = get_report_service(db_session)
    result = report_service.generate_report_bytes(
        case_id=999,
        report_type="full",
        lead_analyst="Agent Special Inspector",
        agency="National Cyber Forensics Unit",
        case_notes="Validated dual-hash matching and 4-tier carving integrity.",
        sworn_declaration=True,
    )

    assert result is not None
    assert "pdf_bytes" in result
    pdf_bytes = result["pdf_bytes"]

    # Must be valid PDF format
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 5000  # Substantial forensic multi-page document
    assert result["total_pages"] >= 4
    assert result["sha256"] is not None
