"""
Integration tests for Telegram parsing API, audit logging, idempotency, and repository storage (spec B9.5, B9.6).
"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.models.models import (
    AuditLog,
    Case,
    Evidence,
    EvidenceFile,
    TelegramChat,
    TelegramDialog,
    TelegramMessage,
    TelegramUnparsedBlob,
    TelegramUser,
)
from backend.services.audit_service import AuditService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def tg_evidence(db_session: Session) -> Evidence:
    """Create a test Case and Evidence with DS-05-dev cache4.db content."""
    ds05_path = Path("testdata/DS-05-dev/cache4.db")
    if not ds05_path.exists():
        pytest.skip("DS-05-dev/cache4.db fixture not found")

    content = ds05_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    test_case = Case(
        name="Telegram Forensic Test Case",
        case_number="CASE-TG-001",
        investigator="Agent Forensic",
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    ev = Evidence(
        case_id=test_case.id,
        original_filename="cache4.db",
        storage_path=str(ds05_path),
        sha256=sha256,
        content_bytes=content,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    return ev


def test_telegram_parse_api_and_audit(client: TestClient, db_session: Session, tg_evidence: Evidence):
    """Verify POST /api/telegram/parse/{id} triggers parsing and writes hash-chained audit log."""
    res = client.post(f"/api/telegram/parse/{tg_evidence.id}")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["evidence_id"] == tg_evidence.id
    assert data["schema_family"] == "android_cache4"
    assert data["messages_count"] >= 30
    assert data["dialogs_count"] >= 1
    assert data["users_count"] >= 1
    assert data["chats_count"] >= 1
    assert data["unparsed_blobs_count"] >= 2
    assert "post_wal_view" in data["views_parsed"]

    # Verify audit log entry
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.evidence_id == tg_evidence.id, AuditLog.action == "STAGE_COMPLETED")
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.details_json["schema_family"] == "android_cache4"
    assert audit_entry.details_json["messages_count"] == data["messages_count"]

    # Verify entire cryptographic audit hash chain
    chain_result = AuditService.verify_audit_chain(db_session)
    assert chain_result.ok is True


def test_telegram_parse_idempotency(client: TestClient, db_session: Session, tg_evidence: Evidence):
    """
    Assert parsing twice on the same evidence replaces existing rows atomically
    and does not duplicate messages, dialogs, users, chats, or unparsed blobs (B9.6).
    """
    res1 = client.post(f"/api/telegram/parse/{tg_evidence.id}")
    assert res1.status_code == 200
    count1 = res1.json()["messages_count"]

    db_msgs_1 = db_session.query(TelegramMessage).filter(TelegramMessage.evidence_id == tg_evidence.id).count()
    db_dialogs_1 = db_session.query(TelegramDialog).filter(TelegramDialog.evidence_id == tg_evidence.id).count()
    db_users_1 = db_session.query(TelegramUser).filter(TelegramUser.evidence_id == tg_evidence.id).count()
    db_chats_1 = db_session.query(TelegramChat).filter(TelegramChat.evidence_id == tg_evidence.id).count()
    db_blobs_1 = db_session.query(TelegramUnparsedBlob).filter(TelegramUnparsedBlob.evidence_id == tg_evidence.id).count()

    # Second parse
    res2 = client.post(f"/api/telegram/parse/{tg_evidence.id}")
    assert res2.status_code == 200
    count2 = res2.json()["messages_count"]

    db_msgs_2 = db_session.query(TelegramMessage).filter(TelegramMessage.evidence_id == tg_evidence.id).count()
    db_dialogs_2 = db_session.query(TelegramDialog).filter(TelegramDialog.evidence_id == tg_evidence.id).count()
    db_users_2 = db_session.query(TelegramUser).filter(TelegramUser.evidence_id == tg_evidence.id).count()
    db_chats_2 = db_session.query(TelegramChat).filter(TelegramChat.evidence_id == tg_evidence.id).count()
    db_blobs_2 = db_session.query(TelegramUnparsedBlob).filter(TelegramUnparsedBlob.evidence_id == tg_evidence.id).count()

    assert count1 == count2
    assert db_msgs_1 == db_msgs_2 == count1
    assert db_dialogs_1 == db_dialogs_2
    assert db_users_1 == db_users_2
    assert db_chats_1 == db_chats_2
    assert db_blobs_1 == db_blobs_2


def test_telegram_get_endpoints(client: TestClient, db_session: Session, tg_evidence: Evidence):
    """Verify all Telegram GET endpoints expose forensic data with additive fields and findings."""
    client.post(f"/api/telegram/parse/{tg_evidence.id}")

    # 1. Messages endpoint
    msgs_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-messages")
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) >= 30

    m0 = msgs[0]
    assert "mid" in m0
    assert "dialog_id" in m0
    assert "date_raw" in m0
    assert "date_unit" in m0
    assert "date_utc_ms" in m0
    assert "source_table" in m0
    assert m0["source_table"] == "messages_v2"
    assert "view" in m0
    assert "finding_id" in m0
    assert "provenance" in m0

    # 2. Dialogs endpoint
    dialogs_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-dialogs")
    assert dialogs_res.status_code == 200
    dialogs = dialogs_res.json()
    assert len(dialogs) >= 1
    d0 = dialogs[0]
    assert "dialog_id" in d0
    assert "peer_kind" in d0
    assert "peer_id" in d0

    # 3. Users endpoint
    users_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-users")
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 1
    u0 = users[0]
    assert "uid" in u0
    assert "first_name" in u0

    # 4. Chats endpoint
    chats_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-chats")
    assert chats_res.status_code == 200
    chats = chats_res.json()
    assert len(chats) >= 1
    c0 = chats[0]
    assert "did" in c0
    assert "chat_id" in c0
    assert "title" in c0

    # 5. Unparsed blobs endpoint
    blobs_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-unparsed-blobs")
    assert blobs_res.status_code == 200
    blobs = blobs_res.json()
    assert len(blobs) >= 2
    b0 = blobs[0]
    assert "table" in b0
    assert "row_id" in b0
    assert "sha256" in b0
    assert "reason" in b0
    assert "container_metadata" in b0

    # 6. Media references endpoint
    media_res = client.get(f"/api/telegram/evidence/{tg_evidence.id}/tg-media")
    assert media_res.status_code == 200
    media = media_res.json()
    assert len(media) >= 1
    med0 = media[0]
    assert "message_id" in med0
    assert "dialog_id" in med0
    assert "media_type" in med0


def test_telegram_legacy_analyze_endpoint(client: TestClient, db_session: Session, tg_evidence: Evidence):
    """Verify legacy POST /api/telegram/evidence/{id}/analyze/telegram returns 200."""
    res = client.post(f"/api/telegram/evidence/{tg_evidence.id}/analyze/telegram")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Telegram analysis completed"
    assert data["evidence_id"] == tg_evidence.id
    assert data["details"]["status"] == "success"


def test_telegram_evidence_set_grouping(client: TestClient, db_session: Session):
    """
    Verify multi-file evidence set grouping (B9.5):
    cache4.db and cache4.db-wal as separate evidence items linked by evidence_set_id.
    """
    ds05_dir = Path("testdata/DS-05-dev")
    db_file = ds05_dir / "cache4.db"
    wal_file = ds05_dir / "cache4.db-wal"
    shm_file = ds05_dir / "cache4.db-shm"

    if not db_file.exists() or not wal_file.exists():
        pytest.skip("DS-05-dev fixture missing")

    test_case = Case(
        name="Telegram Evidence Set Case",
        case_number="CASE-TG-SET-001",
        investigator="Agent Forensic",
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    set_id = "evset-telegram-001"
    ev_db = Evidence(
        case_id=test_case.id,
        original_filename="cache4.db",
        storage_path=str(db_file),
        sha256=hashlib.sha256(db_file.read_bytes()).hexdigest(),
        content_bytes=db_file.read_bytes(),
        evidence_set_id=set_id,
        evidence_role="db",
        integrity_state="OK",
    )
    ev_wal = Evidence(
        case_id=test_case.id,
        original_filename="cache4.db-wal",
        storage_path=str(wal_file),
        sha256=hashlib.sha256(wal_file.read_bytes()).hexdigest(),
        content_bytes=wal_file.read_bytes(),
        evidence_set_id=set_id,
        evidence_role="wal",
        integrity_state="OK",
    )
    ev_shm = Evidence(
        case_id=test_case.id,
        original_filename="cache4.db-shm",
        storage_path=str(shm_file),
        sha256=hashlib.sha256(shm_file.read_bytes()).hexdigest(),
        content_bytes=shm_file.read_bytes(),
        evidence_set_id=set_id,
        evidence_role="shm",
        integrity_state="OK",
    )
    db_session.add_all([ev_db, ev_wal, ev_shm])
    db_session.commit()
    db_session.refresh(ev_db)

    # Ingest main DB evidence item
    res = client.post(f"/api/telegram/parse/{ev_db.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "post_wal_view" in data["views_parsed"]
