"""WhatsApp analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.services.whatsapp_service import whatsapp_service
from backend.schemas.message import MessageRead
from backend.schemas.contact import ContactRead
from backend.schemas.group import GroupRead

router = APIRouter()


@router.post("/evidence/{evidence_id}/analyze/whatsapp", status_code=status.HTTP_202_ACCEPTED)
async def analyze_whatsapp(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Trigger WhatsApp analysis on evidence."""
    result = await whatsapp_service.analyze_evidence(evidence_id, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or analysis failed"
        )
    return {"message": "WhatsApp analysis started", "evidence_id": evidence_id}


@router.get("/evidence/{evidence_id}/wa-messages", response_model=List[MessageRead])
def get_wa_messages(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted WhatsApp messages for evidence."""
    messages = whatsapp_service.get_messages(evidence_id, db)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return messages


@router.get("/evidence/{evidence_id}/wa-contacts", response_model=List[ContactRead])
def get_wa_contacts(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted WhatsApp contacts for evidence."""
    contacts = whatsapp_service.get_contacts(evidence_id, db)
    if contacts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return contacts


@router.get("/evidence/{evidence_id}/wa-groups", response_model=List[GroupRead])
def get_wa_groups(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted WhatsApp groups for evidence."""
    groups = whatsapp_service.get_groups(evidence_id, db)
    if groups is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return groups


@router.get("/evidence/{evidence_id}/wa-media")
def get_wa_media(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get media references from WhatsApp messages for evidence."""
    media = whatsapp_service.get_media_references(evidence_id, db)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return media