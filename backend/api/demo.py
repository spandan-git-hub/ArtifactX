"""Demo mode endpoints for testing without real evidence."""

import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.models.models import Case, Evidence, WhatsAppMessage, WhatsAppContact, TelegramMessage, TelegramContact

router = APIRouter()


class DemoData(BaseModel):
    """Demo data structure."""
    case_name: str
    has_whatsapp: bool = True
    has_telegram: bool = False
    message_count: int = 50
    contact_count: int = 10


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

DEMO_MESSAGES = [
    "Hey, how are you doing today?",
    "Can you send me the documents when you get a chance?",
    "Meeting at 3pm today, don't forget!",
    "Did you see the latest update?",
    "Thanks for your help with that!",
    "Let's grab lunch tomorrow, works for you?",
    "The report is ready for review.",
    "Can you call me back when you're free?",
    "Happy birthday! Hope you have a great day!",
    "See you later, take care!",
    "What time should we meet?",
    "I've attached the file you requested.",
    "Let me know if you need anything else.",
    "This is great news!",
    "I'll be there in 10 minutes.",
]


@router.post("/create-demo-case")
def create_demo_case(data: DemoData, db: Session = Depends(get_db)) -> dict:
    """
    Create a demo case with mock forensic data for testing.
    Returns the case ID and statistics.
    """
    # Check if demo mode is enabled (allow bypass for now, add check in production)

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

    # Log the demo case creation
    from backend.services.log_service import get_log_service
    log_service = get_log_service(db)
    log_service.log_activity(
        case_id=case.id,
        action="create_demo_case",
        description=f"Demo case created: {case.name}"
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
    for jid_suffix, (phone, name, username) in enumerate(contacts_to_create):
        jid = f"{phone}@s.whatsapp.net"
        contact = WhatsAppContact(
            evidence_id=evidence_id,
            jid=jid,
            display_name=name,
            phone_number=phone,
            status=f"Demo contact {name}"
        )
        db.add(contact)
    db.commit()

    # Create demo messages
    base_time = datetime.utcnow() - timedelta(days=7)
    total_messages = min(message_count, 100)

    for i in range(total_messages):
        sender_idx = i % len(contacts_to_create)
        sender_phone = contacts_to_create[sender_idx][0]
        sender_jid = f"{sender_phone}@s.whatsapp.net"

        # Determine chat type (group vs individual)
        if i % 5 == 0:  # Every 5th message is in a group
            chat_jid = "+12025551000@g.us"
        else:
            chat_jid = f"+1202555100{random.randint(1, 9)}@s.whatsapp.net"

        # Determine media type (10% of messages have media)
        media_type = None
        media_path = None
        if i % 10 == 0:
            media_type = random.choice(["image", "video", "audio"])
            media_path = f"/demo/wa_media/msg_{i}.{media_type[0]}"

        msg = WhatsAppMessage(
            evidence_id=evidence_id,
            message_id=f"wa_demo_{i}",
            key_remote_jid=chat_jid,
            sender_jid=sender_jid,
            body=DEMO_MESSAGES[i % len(DEMO_MESSAGES)],
            timestamp=int((base_time + timedelta(minutes=i * 30)).timestamp() * 1000),
            message_type="text" if not media_type else "media",
            media_type=media_type,
            media_path=media_path,
            status="delivered"
        )
        db.add(msg)

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
    for user_id, (phone, name, username) in enumerate(contacts_to_create, start=1000):
        contact = TelegramContact(
            evidence_id=evidence_id,
            user_id=user_id,
            first_name=name.split()[0],
            last_name=name.split()[-1] if len(name.split()) > 1 else "",
            username=username,
            phone=phone,
        )
        db.add(contact)
    db.commit()

    # Create demo messages
    base_time = datetime.utcnow() - timedelta(days=5)
    total_messages = min(message_count, 80)

    for i in range(total_messages):
        sender_id = 1000 + (i % len(contacts_to_create))
        dialog_id = f"dialog_{random.randint(1, 100)}"

        # Determine media type (15% of messages have media)
        media_type = None
        media_path = None
        if i % 7 == 0:
            media_type = random.choice(["image", "video", "audio"])
            media_path = f"/demo/tg_media/msg_{i}.{media_type[0]}"

        msg = TelegramMessage(
            evidence_id=evidence_id,
            message_id=2000 + i,
            dialog_id=dialog_id,
            sender_id=sender_id,
            body=DEMO_MESSAGES[i % len(DEMO_MESSAGES)],
            timestamp=int((base_time + timedelta(minutes=i * 20)).timestamp() * 1000),
            message_type="text" if not media_type else "media",
            media_type=media_type,
            media_path=media_path,
        )
        db.add(msg)

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
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_name = case.name
    db.delete(case)
    db.commit()

    return {"message": f"Demo case '{case_name}' deleted successfully"}