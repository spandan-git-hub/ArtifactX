"""Telegram analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.services.telegram_service import telegram_service
from backend.schemas.telegram_message import TelegramMessageRead
from backend.schemas.telegram_contact import TelegramContactRead
from backend.schemas.telegram_group import TelegramGroupRead

router = APIRouter()


@router.post("/evidence/{evidence_id}/analyze/telegram", status_code=status.HTTP_202_ACCEPTED)
async def analyze_telegram(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Trigger Telegram analysis on evidence."""
    result = await telegram_service.analyze_evidence(evidence_id, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or analysis failed"
        )
    return {"message": "Telegram analysis started", "evidence_id": evidence_id}


@router.get("/evidence/{evidence_id}/tg-messages", response_model=List[TelegramMessageRead])
def get_tg_messages(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted Telegram messages for evidence."""
    messages = telegram_service.get_messages(evidence_id, db)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return messages


@router.get("/evidence/{evidence_id}/tg-contacts", response_model=List[TelegramContactRead])
def get_tg_contacts(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted Telegram contacts for evidence."""
    contacts = telegram_service.get_contacts(evidence_id, db)
    if contacts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return contacts


@router.get("/evidence/{evidence_id}/tg-groups", response_model=List[TelegramGroupRead])
def get_tg_groups(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted Telegram groups for evidence."""
    groups = telegram_service.get_groups(evidence_id, db)
    if groups is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return groups


@router.get("/evidence/{evidence_id}/tg-media")
def get_tg_media(
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """Get media references from Telegram messages for evidence."""
    media = telegram_service.get_media_references(evidence_id, db)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    return media