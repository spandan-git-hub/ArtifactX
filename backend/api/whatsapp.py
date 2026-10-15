"""WhatsApp forensic analysis and artifact extraction API endpoints (spec B7.5)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.schemas.contact import ContactRead
from backend.schemas.group import GroupRead
from backend.schemas.message import MessageRead
from backend.services.whatsapp_service import whatsapp_service

router = APIRouter()


@router.post("/parse/{evidence_id}", status_code=status.HTTP_200_OK)
def parse_whatsapp(
    evidence_id: int,
    derived_artifact_id: Optional[str] = Query(None, description="Optional derived artifact ID (e.g. from decryption)"),
    db: Session = Depends(get_db),
):
    """
    Trigger forensic WhatsApp parsing on evidence or decrypted derived artifact (spec B7.5).
    Runs pre-flight integrity check, hash-chained audit logging, and atomic persistence.
    """
    try:
        result = whatsapp_service.parse_evidence_sync(
            evidence_id=evidence_id,
            db=db,
            derived_artifact_id=derived_artifact_id,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/evidence/{evidence_id}/analyze/whatsapp", status_code=status.HTTP_200_OK)
async def analyze_whatsapp_legacy(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Trigger WhatsApp analysis on evidence (compatible with legacy route)."""
    try:
        result = whatsapp_service.parse_evidence_sync(evidence_id, db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/evidence/{evidence_id}/wa-messages", response_model=List[MessageRead])
def get_wa_messages(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted WhatsApp messages with forensic provenance for evidence."""
    messages = whatsapp_service.get_messages(evidence_id, db)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return messages


@router.get("/evidence/{evidence_id}/wa-chats")
def get_wa_chats(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted WhatsApp chat threads for evidence."""
    chats = whatsapp_service.get_chats(evidence_id, db)
    if chats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return [
        {
            "id": c.id,
            "evidence_id": c.evidence_id,
            "chat_row_id": c.chat_row_id,
            "jid": c.jid,
            "subject": c.subject,
            "is_group": c.is_group,
            "hidden": c.hidden,
            "archived": c.archived,
            "last_message_row_id": c.last_message_row_id,
            "participant_jids": c.participant_jids or [],
            "provenance": c.provenance or {},
        }
        for c in chats
    ]


@router.get("/evidence/{evidence_id}/wa-contacts", response_model=List[ContactRead])
def get_wa_contacts(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted WhatsApp contacts for evidence."""
    contacts = whatsapp_service.get_contacts(evidence_id, db)
    if contacts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return contacts


@router.get("/evidence/{evidence_id}/wa-groups", response_model=List[GroupRead])
def get_wa_groups(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted WhatsApp groups for evidence."""
    groups = whatsapp_service.get_groups(evidence_id, db)
    if groups is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return groups


@router.get("/evidence/{evidence_id}/wa-revocations")
def get_wa_revocations(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Tier-1 message revocation findings for evidence."""
    revs = whatsapp_service.get_revocations(evidence_id, db)
    if revs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return [
        {
            "id": r.id,
            "evidence_id": r.evidence_id,
            "message_row_id": r.message_row_id,
            "revoked_key_id": r.revoked_key_id,
            "revoke_ts": r.revoke_ts,
            "admin_jid": r.admin_jid,
            "finding_id": r.finding_id,
            "confidence_score": r.confidence_score,
            "strength": r.strength,
            "limitations": r.limitations or [],
            "provenance": r.provenance or {},
        }
        for r in revs
    ]


@router.get("/evidence/{evidence_id}/wa-edits")
def get_wa_edits(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted message edit history findings for evidence."""
    edits = whatsapp_service.get_edits(evidence_id, db)
    if edits is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return [
        {
            "id": e.id,
            "evidence_id": e.evidence_id,
            "message_row_id": e.message_row_id,
            "original_key_id": e.original_key_id,
            "edited_ts": e.edited_ts,
            "sender_ts": e.sender_ts,
            "prior_text_not_present": e.prior_text_not_present,
            "edited_text": e.edited_text,
            "finding_id": e.finding_id,
            "confidence_score": e.confidence_score,
            "strength": e.strength,
            "limitations": e.limitations or [],
            "provenance": e.provenance or {},
        }
        for e in edits
    ]


@router.get("/evidence/{evidence_id}/wa-media")
def get_wa_media(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get media references from WhatsApp messages for evidence."""
    media = whatsapp_service.get_media_references(evidence_id, db)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return media