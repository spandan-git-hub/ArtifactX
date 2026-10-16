"""
Test suite for forensic case management, data isolation, and case deletion.

Verifies:
1. Case creation with assigned docket numbers and examiner metadata.
2. Complete data isolation between multiple cases (zero cross-case leakage across evidence,
   messages, contacts, chats, timeline events, recovery, and search).
3. Thorough cascade deletion of case artifacts, evidence records, and disk files.
4. Retention and cryptographic integrity of append-only audit trail across case deletion.
5. Non-interference: deleting Case A leaves Case B 100% intact.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.models.models import (
    AuditLog,
    Case,
    CorrelationEdge,
    CorrelationFinding,
    DeletedMessage,
    DerivedArtifact,
    Evidence,
    EvidenceFile,
    MediaItem,
    PipelineRun,
    PipelineStageRun,
    RecoveredFinding,
    RecoveryRun,
    TelegramChat,
    TelegramContact,
    TelegramDialog,
    TelegramGroup,
    TelegramMessage,
    TelegramUnparsedBlob,
    TelegramUser,
    TimelineEvent,
    WhatsAppChat,
    WhatsAppContact,
    WhatsAppEdit,
    WhatsAppGroup,
    WhatsAppJid,
    WhatsAppMessage,
    WhatsAppRevocation,
)
from backend.services.audit_service import AuditService
from backend.utils.file_storage import save_upload, delete_file


@pytest.fixture(scope="function")
def test_env():
    """Create a completely isolated in-memory database and test uploads directory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {
        "client": client,
        "engine": engine,
        "SessionLocal": TestingSessionLocal,
    }

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_case_creation_and_metadata(test_env):
    """Test creating cases with metadata and sequential docket formatting."""
    client = test_env["client"]

    # 1. Create with custom docket ID
    res1 = client.post("/api/cases", json={
        "name": "Operation Falcon",
        "description": "WhatsApp and Telegram extraction",
        "investigator": "Det. H. Wright",
        "agency": "Special Cyber Forensics Division",
        "case_number": "ARX-2026-FALCON-01",
    })
    assert res1.status_code == 200, res1.text
    case1 = res1.json()
    assert case1["name"] == "Operation Falcon"
    assert case1["case_number"] == "ARX-2026-FALCON-01"
    assert case1["examiner_name"] == "Det. H. Wright"
    assert case1["agency"] == "Special Cyber Forensics Division"

    # 2. Create with auto-assigned sequential docket ID
    res2 = client.post("/api/cases", json={
        "name": "Operation Eagle",
        "investigator": "Inspector J. Miller",
    })
    assert res2.status_code == 200, res2.text
    case2 = res2.json()
    assert case2["case_number"] == "ARX-2026-002"
    assert case2["examiner_name"] == "Inspector J. Miller"

    # 3. List cases
    list_res = client.get("/api/cases")
    assert list_res.status_code == 200
    cases = list_res.json()
    assert len(cases) == 2
    case_ids = [c["id"] for c in cases]
    assert case1["id"] in case_ids
    assert case2["id"] in case_ids


def test_multi_case_data_isolation(test_env):
    """
    Ensure complete data isolation between Case A and Case B.
    Data ingested into Case A must never overlap or bleed into Case B queries.
    """
    client = test_env["client"]
    db = test_env["SessionLocal"]()

    try:
        # Create Case A and Case B
        case_a = Case(name="Case Alpha", case_number="ARX-2026-001", investigator="Agent A")
        case_b = Case(name="Case Beta", case_number="ARX-2026-002", investigator="Agent B")
        db.add_all([case_a, case_b])
        db.commit()
        db.refresh(case_a)
        db.refresh(case_b)

        # Ingest Evidence A for Case A
        ev_a = Evidence(
            case_id=case_a.id,
            original_filename="alpha_dump.db",
            storage_path="uploads/alpha_dummy.db",
            sha256="a" * 64,
            evidence_type="file",
            integrity_state="OK",
        )
        # Ingest Evidence B for Case B
        ev_b = Evidence(
            case_id=case_b.id,
            original_filename="beta_dump.db",
            storage_path="uploads/beta_dummy.db",
            sha256="b" * 64,
            evidence_type="file",
            integrity_state="OK",
        )
        db.add_all([ev_a, ev_b])
        db.commit()
        db.refresh(ev_a)
        db.refresh(ev_b)

        # Populate WhatsApp records for Case A
        msg_a = WhatsAppMessage(
            evidence_id=ev_a.id,
            message_id="wa_msg_alpha_1",
            key_remote_jid="alice@s.whatsapp.net",
            sender_jid="alice@s.whatsapp.net",
            body="Secret meeting for Alpha",
            timestamp=1700000000000,
        )
        contact_a = WhatsAppContact(
            evidence_id=ev_a.id,
            jid="alice@s.whatsapp.net",
            display_name="Alice Alpha",
            phone_number="+1000000001",
        )
        timeline_a = TimelineEvent(
            case_id=case_a.id,
            evidence_id=ev_a.id,
            event_type="MESSAGE_SENT",
            source_app="whatsapp",
            timestamp=1700000000000,
            description="Alpha event: Secret meeting",
        )

        # Populate WhatsApp records for Case B
        msg_b = WhatsAppMessage(
            evidence_id=ev_b.id,
            message_id="wa_msg_beta_1",
            key_remote_jid="bob@s.whatsapp.net",
            sender_jid="bob@s.whatsapp.net",
            body="Confidential handover for Beta",
            timestamp=1700000005000,
        )
        contact_b = WhatsAppContact(
            evidence_id=ev_b.id,
            jid="bob@s.whatsapp.net",
            display_name="Bob Beta",
            phone_number="+2000000002",
        )
        timeline_b = TimelineEvent(
            case_id=case_b.id,
            evidence_id=ev_b.id,
            event_type="MESSAGE_SENT",
            source_app="whatsapp",
            timestamp=1700000005000,
            description="Beta event: Confidential handover",
        )

        db.add_all([msg_a, contact_a, timeline_a, msg_b, contact_b, timeline_b])
        db.commit()

        # ================= ISOLATION VERIFICATION 1: Chats =================
        # Query Case A chats
        res_chats_a = client.get(f"/api/cases/{case_a.id}/chats")
        assert res_chats_a.status_code == 200
        chats_a = res_chats_a.json()
        assert len(chats_a) == 1
        assert chats_a[0]["jid"] == "alice@s.whatsapp.net"
        assert chats_a[0]["name"] == "Alice Alpha"

        # Query Case B chats
        res_chats_b = client.get(f"/api/cases/{case_b.id}/chats")
        assert res_chats_b.status_code == 200
        chats_b = res_chats_b.json()
        assert len(chats_b) == 1
        assert chats_b[0]["jid"] == "bob@s.whatsapp.net"
        assert chats_b[0]["name"] == "Bob Beta"

        # Query messages for Case A thread
        res_msgs_a = client.get(f"/api/cases/{case_a.id}/chats/alice@s.whatsapp.net/messages")
        assert res_msgs_a.status_code == 200
        msgs_a = res_msgs_a.json()
        assert len(msgs_a["messages"]) == 1
        assert msgs_a["messages"][0]["body"] == "Secret meeting for Alpha"

        # Requesting Bob from Case A must yield 0 messages
        res_msgs_a_bob = client.get(f"/api/cases/{case_a.id}/chats/bob@s.whatsapp.net/messages")
        assert len(res_msgs_a_bob.json()["messages"]) == 0

        # ================= ISOLATION VERIFICATION 2: Timeline =================
        res_time_a = client.get(f"/api/cases/{case_a.id}/timeline")
        assert res_time_a.status_code == 200
        events_a = res_time_a.json()
        assert len(events_a) == 1
        assert "Alpha" in events_a[0]["description"]
        assert "Beta" not in events_a[0]["description"]

        res_time_b = client.get(f"/api/cases/{case_b.id}/timeline")
        assert res_time_b.status_code == 200
        events_b = res_time_b.json()
        assert len(events_b) == 1
        assert "Beta" in events_b[0]["description"]
        assert "Alpha" not in events_b[0]["description"]

        # ================= ISOLATION VERIFICATION 3: Evidence =================
        ev_list_a = client.get(f"/api/evidence?case_id={case_a.id}").json()
        assert len(ev_list_a) == 1
        assert ev_list_a[0]["original_filename"] == "alpha_dump.db"

        ev_list_b = client.get(f"/api/evidence?case_id={case_b.id}").json()
        assert len(ev_list_b) == 1
        assert ev_list_b[0]["original_filename"] == "beta_dump.db"

        # ================= ISOLATION VERIFICATION 4: Search =================
        search_a = client.get(f"/api/search?case_id={case_a.id}&query=Alpha").json()
        assert len(search_a["messages"]) == 1
        search_a_leak = client.get(f"/api/search?case_id={case_a.id}&query=Beta").json()
        assert len(search_a_leak["messages"]) == 0

    finally:
        db.close()


def test_case_deletion_cascade_and_isolation(test_env):
    """
    Test case deletion:
    1. Case A and all its evidence, messages, contacts, files, runs are removed.
    2. Case B remains 100% unaffected.
    3. Audit log chain is preserved without breakages (ondelete SET NULL).
    """
    client = test_env["client"]
    db = test_env["SessionLocal"]()

    try:
        # Create Case A and Case B
        case_a = Case(name="Case Alpha To Delete", case_number="ARX-2026-DEL", investigator="Agent A")
        case_b = Case(name="Case Beta Survives", case_number="ARX-2026-SURV", investigator="Agent B")
        db.add_all([case_a, case_b])
        db.commit()
        db.refresh(case_a)
        db.refresh(case_b)

        # Create temporary dummy evidence files on disk
        temp_dir = tempfile.mkdtemp(prefix="arx_test_ev_")
        storage_file_a = Path(temp_dir) / "alpha_evidence.bin"
        storage_file_a.write_bytes(b"ALPHA_PAYLOAD_EVIDENCE")
        extract_dir_a = Path(temp_dir) / "alpha_extracted"
        extract_dir_a.mkdir()
        (extract_dir_a / "subfile.txt").write_text("extracted file")

        # Create Evidence and dependent entities for Case A
        ev_a = Evidence(
            case_id=case_a.id,
            original_filename="alpha_evidence.bin",
            storage_path=str(storage_file_a),
            extracted_path=str(extract_dir_a),
            sha256="a" * 64,
            evidence_type="file",
            integrity_state="OK",
        )
        db.add(ev_a)
        db.commit()
        db.refresh(ev_a)

        # Add records to all tables for Case A
        wa_msg = WhatsAppMessage(evidence_id=ev_a.id, message_id="wa_1", body="msg 1")
        wa_contact = WhatsAppContact(evidence_id=ev_a.id, jid="wa_contact_1")
        wa_chat = WhatsAppChat(evidence_id=ev_a.id, jid="wa_chat_1")
        wa_jid = WhatsAppJid(evidence_id=ev_a.id, raw_string="wa_jid_1")
        wa_rev = WhatsAppRevocation(evidence_id=ev_a.id, revoked_key_id="rev_1")
        wa_edit = WhatsAppEdit(evidence_id=ev_a.id, original_key_id="edit_1")

        tg_msg = TelegramMessage(evidence_id=ev_a.id, message_id=101, dialog_id="tg_1", text="tg 1")
        tg_contact = TelegramContact(evidence_id=ev_a.id, user_id=201)
        tg_group = TelegramGroup(evidence_id=ev_a.id, group_id=301)
        tg_chat = TelegramChat(evidence_id=ev_a.id, did=401, chat_id=401, title="TG Group")
        tg_user = TelegramUser(evidence_id=ev_a.id, uid=501, first_name="TG User")
        tg_dialog = TelegramDialog(evidence_id=ev_a.id, dialog_id=601, peer_kind="user", peer_id=601)

        time_ev = TimelineEvent(case_id=case_a.id, evidence_id=ev_a.id, description="timeline a")
        del_msg = DeletedMessage(case_id=case_a.id, evidence_id=ev_a.id, chat_jid="c1")
        media = MediaItem(case_id=case_a.id, evidence_id=ev_a.id, file_path="m.jpg")
        corr_edge = CorrelationEdge(case_id=case_a.id, source_id="s1", target_id="t1")
        rec_run = RecoveryRun(case_id=case_a.id, status="COMPLETED")
        db.add(rec_run)
        db.commit()
        db.refresh(rec_run)

        rec_finding = RecoveredFinding(case_id=case_a.id, run_id=rec_run.id, evidence_id=ev_a.id, raw_payload_hash="h" * 64, method="wal")
        pipe_run = PipelineRun(id="run_alpha_1", case_id=case_a.id, status="COMPLETED")
        db.add(pipe_run)
        db.commit()
        pipe_stage = PipelineStageRun(run_id="run_alpha_1", stage="integrity", status="SUCCESS")

        db.add_all([
            wa_msg, wa_contact, wa_chat, wa_jid, wa_rev, wa_edit,
            tg_msg, tg_contact, tg_group, tg_chat, tg_user, tg_dialog,
            time_ev, del_msg, media, corr_edge, rec_finding, pipe_stage,
        ])
        db.commit()

        # Add AuditLog for Case A
        AuditService.append(
            db=db,
            action="INGEST",
            actor="test_user",
            case_id=case_a.id,
            evidence_id=ev_a.id,
            details={"file": "alpha_evidence.bin"},
        )

        # Evidence and records for Case B
        ev_b = Evidence(
            case_id=case_b.id,
            original_filename="beta_evidence.bin",
            storage_path="uploads/beta.bin",
            sha256="b" * 64,
            evidence_type="file",
        )
        db.add(ev_b)
        db.commit()
        db.refresh(ev_b)
        msg_b = WhatsAppMessage(evidence_id=ev_b.id, message_id="wa_b_1", body="Beta persists")
        timeline_b = TimelineEvent(case_id=case_b.id, evidence_id=ev_b.id, description="Beta timeline")
        db.add_all([msg_b, timeline_b])
        db.commit()

        case_a_id = case_a.id
        ev_a_id = ev_a.id
        case_b_id = case_b.id
        ev_b_id = ev_b.id

        # ================= EXECUTE DELETE CASE A =================
        assert storage_file_a.exists()
        assert extract_dir_a.exists()

        del_res = client.delete(f"/api/cases/{case_a_id}")
        assert del_res.status_code == 200, del_res.text
        data = del_res.json()
        assert data["case_id"] == case_a_id
        assert "deleted successfully" in data["message"]

        # Verify disk files were removed
        assert not storage_file_a.exists()
        assert not extract_dir_a.exists()

        # Verify Case A is 404
        get_res = client.get(f"/api/cases/{case_a_id}")
        assert get_res.status_code == 404

        # Verify all Case A entities are gone
        assert db.query(Case).filter(Case.id == case_a_id).first() is None
        assert db.query(Evidence).filter(Evidence.case_id == case_a_id).count() == 0
        assert db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == ev_a_id).count() == 0
        assert db.query(TelegramMessage).filter(TelegramMessage.evidence_id == ev_a_id).count() == 0
        assert db.query(TimelineEvent).filter(TimelineEvent.case_id == case_a_id).count() == 0
        assert db.query(PipelineRun).filter(PipelineRun.case_id == case_a_id).count() == 0
        assert db.query(RecoveryRun).filter(RecoveryRun.case_id == case_a_id).count() == 0

        # ================= VERIFY CASE B REMAINS 100% INTACT =================
        case_b_db = db.query(Case).filter(Case.id == case_b_id).first()
        assert case_b_db is not None
        assert case_b_db.name == "Case Beta Survives"

        ev_b_list = db.query(Evidence).filter(Evidence.case_id == case_b_id).all()
        assert len(ev_b_list) == 1
        assert ev_b_list[0].id == ev_b_id

        msgs_b = db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == ev_b_id).all()
        assert len(msgs_b) == 1
        assert msgs_b[0].body == "Beta persists"

        # ================= VERIFY AUDIT LOG CHAIN INTEGRITY =================
        verify_result = AuditService.verify_audit_chain(db)
        assert verify_result.ok is True
        assert verify_result.checked >= 2

        # Verify immutable historical audit entries for Case A are preserved
        ingest_entry = db.query(AuditLog).filter(AuditLog.action == "INGEST").first()
        assert ingest_entry is not None
        assert ingest_entry.case_id == case_a_id

        # Verify CASE_DELETED event was appended to the chain
        del_entry = db.query(AuditLog).filter(AuditLog.action == "CASE_DELETED").first()
        assert del_entry is not None
        assert del_entry.case_id == case_a_id

        # Clean up temporary test directory if any remnants
        shutil.rmtree(temp_dir, ignore_errors=True)

    finally:
        db.close()


def test_delete_nonexistent_case(test_env):
    """Deleting a non-existent case ID must return 404."""
    client = test_env["client"]
    res = client.delete("/api/cases/9999999")
    assert res.status_code == 404
    assert "Case not found" in res.json()["detail"]
