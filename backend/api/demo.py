"""Demo mode endpoints for testing without real evidence."""

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.models.models import (
    Case,
    Evidence,
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    TimelineEvent,
    DeletedMessage,
    MediaItem,
)

router = APIRouter()


class DemoData(BaseModel):
    """Demo data structure."""
    case_name: str = Field(default_factory=lambda: f"Demo Case - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
    has_whatsapp: bool = True
    has_telegram: bool = True
    message_count: int = 100
    contact_count: int = 15


# Demo data templates
DEMO_CONTACTS = [
    ("+12025551234", "Alice Johnson", "alice_j"),
    ("+12025551235", "Bob Smith", "bob_smith"),
    ("+12025551236", "Carol Williams", "carol_w"),
    ("+12025551237", "David Brown", "david_b"),
    ("+12025551238", "Eve Davis", "eve_d"),
    ("+12025551239", "Frank Miller", "frank_m"),
    ("+12025551240", "Grace Lee", "grace_lee"),
    ("+12025551241", "Henry Wilson", "henry_w"),
    ("+12025551242", "Ivy Chen", "ivy_chen"),
    ("+12025551243", "Jack Taylor", "jack_t"),
]

REALISTIC_EXCHANGES = [
    {
        "wa": "Can you check the encrypted file I emailed you?",
        "tg": "Got it. Downloading the file on Telegram channel now."
    },
    {
        "wa": "Switch to Telegram for the sensitive details.",
        "tg": "I am on Telegram now. Send the key here."
    },
    {
        "wa": "Are we still meeting at the dock at 4 PM?",
        "tg": "Yes, standby. Bringing the hardware package."
    },
    {
        "wa": "WhatsApp call keeps dropping, calling on Telegram.",
        "tg": "Connection is clean here, ringing you back."
    },
    {
        "wa": "Did you verify the transaction hash?",
        "tg": "Verified on blockchain explorer, transfer of 2.5 BTC confirmed."
    },
    {
        "wa": "Delete the chat history after reading.",
        "tg": "Timer set to auto-delete after 24 hours."
    },
    {
        "wa": "Need the passport scans for the flight reservation.",
        "tg": "Sending high-res scan as document on TG."
    },
    {
        "wa": "Where are the server access logs?",
        "tg": "Archived in the restricted channel, check your admin invite."
    },
    {
        "wa": "Did David confirm the rendezvous point?",
        "tg": "He just messaged on Telegram, location confirmed near Sector 4."
    },
    {
        "wa": "Can you send the location coordinates?",
        "tg": "Shared live location on Telegram map."
    },
]

DEMO_MESSAGES = [item["wa"] for item in REALISTIC_EXCHANGES]



@router.post("/create-demo-case")
def create_demo_case(data: DemoData, db: Session = Depends(get_db)) -> dict:
    """
    Create a demo case with mock forensic data for testing.
    Returns the case ID and statistics.
    """
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")

    # Create case
    case = Case(
        name=data.case_name,
        description="Demo case created for testing ArtifactX functionality",
        investigator="Demo User",
        status="active"
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    stats = {"case_id": case.id, "whatsapp": {}, "telegram": {}}

    # Create demo WhatsApp evidence if requested
    if data.has_whatsapp:
        wa_stats = _create_demo_whatsapp(db, case.id, data.message_count, data.contact_count)
        stats["whatsapp"] = wa_stats

    # Create demo Telegram evidence if requested
    if data.has_telegram:
        tg_stats = _create_demo_telegram(db, case.id, data.message_count, data.contact_count)
        stats["telegram"] = tg_stats

    db.commit()

    # Automatically run correlation engine for demo data
    from backend.services.correlation_service import correlation_service
    edge_count = correlation_service.correlate_case(db, case.id)
    stats["correlation_edges"] = edge_count

    # Log the demo case creation
    from backend.services.log_service import get_log_service
    log_service = get_log_service(db)
    log_service.log_activity(
        case_id=case.id,
        action="create_demo_case",
        description=f"Demo case created: {case.name} with {edge_count} correlation edges"
    )

    return stats



def _create_demo_whatsapp(db: Session, case_id: int, message_count: int, contact_count: int) -> dict:
    """Create demo WhatsApp messages and contacts."""
    # Create demo evidence
    evidence = Evidence(
        case_id=case_id,
        original_filename="demo_whatsapp.db",
        storage_path="demo/wa_demo.db",
        sha256="0" * 64,
        evidence_type="demo",
        metadata_={"source": "demo_mode", "app": "whatsapp"}
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    evidence_id = evidence.id

    # Create demo contacts
    contacts_to_create = DEMO_CONTACTS[:min(contact_count, len(DEMO_CONTACTS))]
    contacts = []
    for jid_suffix, (phone, name, username) in enumerate(contacts_to_create):
        jid = f"{phone}@s.whatsapp.net"
        contact = WhatsAppContact(
            evidence_id=evidence_id,
            jid=jid,
            display_name=name,
            phone_number=phone,
            status=f"Demo contact {name}"
        )
        contacts.append(contact)
    db.add_all(contacts)

    # Create demo messages
    base_time = datetime.now(timezone.utc) - timedelta(days=3)
    total_messages = min(message_count, 100)

    messages = []
    events = []
    for i in range(total_messages):
        sender_idx = i % len(contacts_to_create)
        sender_phone = contacts_to_create[sender_idx][0]
        sender_jid = f"{sender_phone}@s.whatsapp.net"

        # Determine chat type (group vs individual)
        if i % 5 == 0:
            chat_jid = "+12025551000@g.us"
        else:
            chat_jid = f"+1202555100{random.randint(1, 9)}@s.whatsapp.net"

        # Determine media type
        media_type = None
        media_path = None
        if i % 10 == 0:
            media_type = random.choice(["image", "video", "audio"])
            media_path = f"/demo/wa_media/msg_{i}.{media_type[0]}"

        # Calculate synchronized timestamp in seconds
        ts_dt = base_time + timedelta(minutes=i * 20)
        ts_sec = int(ts_dt.timestamp())

        msg = WhatsAppMessage(
            evidence_id=evidence_id,
            message_id=f"wa_demo_{i}",
            key_remote_jid=chat_jid,
            sender_jid=sender_jid,
            body=REALISTIC_EXCHANGES[i % len(REALISTIC_EXCHANGES)]["wa"],
            timestamp=ts_sec,
            message_type="text" if not media_type else "media",
            media_type=media_type,
            media_path=media_path,
            status="delivered"
        )
        messages.append(msg)

        # Timeline event for message
        evt = TimelineEvent(
            case_id=case_id,
            evidence_id=evidence_id,
            event_type="message",
            source_app="whatsapp",
            timestamp=ts_sec,
            normalized_timestamp=datetime.fromtimestamp(ts_sec, tz=timezone.utc),
            entity_id=str(msg.message_id),
            entity_type="message",
            description=f"Message: {msg.body[:60]}"
        )
        events.append(evt)

    db.add_all(messages)
    db.add_all(events)

    # Create demo deleted messages
    del_msg1 = DeletedMessage(
        case_id=case_id,
        evidence_id=evidence_id,
        source_app="whatsapp",
        chat_jid="+12025551234@s.whatsapp.net",
        gap_start=int((base_time + timedelta(hours=2)).timestamp()),
        gap_end=int((base_time + timedelta(hours=3)).timestamp()),
        missing_count=2,
        confidence_score=0.85,
        detection_method="sequence_gap_analysis",
        detected_at=datetime.now(timezone.utc)
    )
    del_msg2 = DeletedMessage(
        case_id=case_id,
        evidence_id=evidence_id,
        source_app="whatsapp",
        chat_jid="+12025551000@g.us",
        gap_start=int((base_time + timedelta(hours=10)).timestamp()),
        gap_end=int((base_time + timedelta(hours=11)).timestamp()),
        missing_count=1,
        confidence_score=0.75,
        detection_method="sequence_gap_analysis",
        detected_at=datetime.now(timezone.utc)
    )
    db.add_all([del_msg1, del_msg2])

    db.commit()

    # Count created records
    wa_msg_count = db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id == evidence_id).count()
    wa_contact_count = db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id == evidence_id).count()

    return {
        "messages": wa_msg_count,
        "contacts": wa_contact_count,
        "evidence_id": evidence_id,
    }


def _create_demo_telegram(db: Session, case_id: int, message_count: int, contact_count: int) -> dict:
    """Create demo Telegram messages and contacts."""
    # Create demo evidence
    evidence = Evidence(
        case_id=case_id,
        original_filename="demo_telegram.db",
        storage_path="demo/tg_demo.db",
        sha256="1" * 64,
        evidence_type="demo",
        metadata_={"source": "demo_mode", "app": "telegram"}
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    evidence_id = evidence.id

    # Create demo contacts
    contacts_to_create = DEMO_CONTACTS[:min(contact_count, len(DEMO_CONTACTS))]
    contacts = []
    for user_id, (phone, name, username) in enumerate(contacts_to_create, start=1000):
        contact = TelegramContact(
            evidence_id=evidence_id,
            user_id=user_id,
            first_name=name.split()[0],
            last_name=name.split()[-1] if len(name.split()) > 1 else "",
            username=username,
            phone=phone,
        )
        contacts.append(contact)
    db.add_all(contacts)

    # Create demo messages synchronized with WhatsApp timeline
    base_time = datetime.now(timezone.utc) - timedelta(days=3)
    total_messages = min(message_count, 80)

    messages = []
    events = []
    for i in range(total_messages):
        sender_id = 1000 + (i % len(contacts_to_create))
        dialog_id = f"dialog_{random.randint(1, 100)}"

        # Determine media type
        media_type = None
        media_path = None
        if i % 7 == 0:
            media_type = random.choice(["image", "video", "audio"])
            media_path = f"/demo/tg_media/msg_{i}.{media_type[0]}"

        # Correlate timestamp within 15-45 seconds of WhatsApp message slot
        time_offset = timedelta(minutes=i * 20, seconds=random.randint(15, 45))
        ts_dt = base_time + time_offset
        ts_sec = int(ts_dt.timestamp())

        msg = TelegramMessage(
            evidence_id=evidence_id,
            message_id=2000 + i,
            dialog_id=dialog_id,
            sender_id=sender_id,
            body=REALISTIC_EXCHANGES[i % len(REALISTIC_EXCHANGES)]["tg"],
            timestamp=ts_sec,
            message_type="text" if not media_type else "media",
            media_type=media_type,
            media_path=media_path,
        )

        messages.append(msg)

        # Timeline event for message
        evt = TimelineEvent(
            case_id=case_id,
            evidence_id=evidence_id,
            event_type="message",
            source_app="telegram",
            timestamp=ts_sec,
            normalized_timestamp=datetime.fromtimestamp(ts_sec, tz=timezone.utc),
            entity_id=str(msg.message_id),
            entity_type="message",
            description=f"Message: {msg.body[:60]}"
        )
        events.append(evt)


    db.add_all(messages)
    db.add_all(events)

    # Create demo deleted messages
    del_msg1 = DeletedMessage(
        case_id=case_id,
        evidence_id=evidence_id,
        source_app="telegram",
        chat_jid="dialog_1",
        gap_start=int((base_time + timedelta(hours=4)).timestamp() * 1000),
        gap_end=int((base_time + timedelta(hours=5)).timestamp() * 1000),
        missing_count=3,
        confidence_score=0.85,
        detection_method="sequence_gap_analysis",
        detected_at=datetime.now(timezone.utc)
    )
    del_msg2 = DeletedMessage(
        case_id=case_id,
        evidence_id=evidence_id,
        source_app="telegram",
        chat_jid="dialog_2",
        gap_start=int((base_time + timedelta(hours=12)).timestamp() * 1000),
        gap_end=int((base_time + timedelta(hours=13)).timestamp() * 1000),
        missing_count=1,
        confidence_score=0.60,
        detection_method="sequence_gap_analysis",
        detected_at=datetime.now(timezone.utc)
    )
    db.add_all([del_msg1, del_msg2])

    db.commit()

    # Count created records
    tg_msg_count = db.query(TelegramMessage).filter(TelegramMessage.evidence_id == evidence_id).count()
    tg_contact_count = db.query(TelegramContact).filter(TelegramContact.evidence_id == evidence_id).count()

    return {
        "messages": tg_msg_count,
        "contacts": tg_contact_count,
        "evidence_id": evidence_id,
    }


@router.delete("/demo-case/{case_id}")
def delete_demo_case(case_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a demo case and all associated data."""
    from backend.api.cases import delete_case
    return delete_case(case_id, db)