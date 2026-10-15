"""Telegram forensic analysis API endpoints (spec B9.5, B9.6)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.services.telegram_service import telegram_service
from backend.schemas.telegram_message import TelegramMessageRead
from backend.schemas.telegram_contact import TelegramContactRead
from backend.schemas.telegram_group import TelegramGroupRead
from backend.schemas.telegram_forensics import (
    TelegramChatRead,
    TelegramDialogRead,
    TelegramUnparsedBlobRead,
    TelegramUserRead,
)

router = APIRouter()


@router.post("/parse/{evidence_id}", status_code=status.HTTP_200_OK)
def parse_telegram(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger forensic Telegram parsing on evidence (spec B9.5, B9.6).
    Runs pre-flight integrity check, hash-chained audit logging, and atomic persistence.
    """
    try:
        result = telegram_service.parse_evidence_sync(evidence_id=evidence_id, db=db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/evidence/{evidence_id}/analyze/telegram", status_code=status.HTTP_200_OK)
def analyze_telegram(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Trigger Telegram analysis on evidence (sync execution matching WhatsApp B7.5 pattern)."""
    try:
        result = telegram_service.parse_evidence_sync(evidence_id=evidence_id, db=db)
        return {"message": "Telegram analysis completed", "evidence_id": evidence_id, "details": result}
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/evidence/{evidence_id}/tg-messages", response_model=List[TelegramMessageRead])
def get_tg_messages(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram messages for evidence."""
    messages = telegram_service.get_messages(evidence_id, db)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return messages


@router.get("/evidence/{evidence_id}/tg-dialogs", response_model=List[TelegramDialogRead])
def get_tg_dialogs(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram dialogs for evidence (spec B9.4, B9.6)."""
    dialogs = telegram_service.get_dialogs(evidence_id, db)
    if dialogs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return dialogs


@router.get("/evidence/{evidence_id}/tg-users", response_model=List[TelegramUserRead])
def get_tg_users(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram users for evidence (spec B9.4, B9.6)."""
    users = telegram_service.get_users(evidence_id, db)
    if users is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return users


@router.get("/evidence/{evidence_id}/tg-chats", response_model=List[TelegramChatRead])
def get_tg_chats(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram chats/channels for evidence (spec B9.4, B9.6)."""
    chats = telegram_service.get_chats(evidence_id, db)
    if chats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return chats


@router.get("/evidence/{evidence_id}/tg-unparsed-blobs", response_model=List[TelegramUnparsedBlobRead])
def get_tg_unparsed_blobs(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get unparsed TL blobs for evidence (spec B9.3, B9.6)."""
    blobs = telegram_service.get_unparsed_blobs(evidence_id, db)
    if blobs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return blobs


@router.get("/evidence/{evidence_id}/tg-contacts", response_model=List[TelegramContactRead])
def get_tg_contacts(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram contacts for evidence (legacy compatibility)."""
    contacts = telegram_service.get_contacts(evidence_id, db)
    if contacts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return contacts


@router.get("/evidence/{evidence_id}/tg-groups", response_model=List[TelegramGroupRead])
def get_tg_groups(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get extracted Telegram groups for evidence (legacy compatibility)."""
    groups = telegram_service.get_groups(evidence_id, db)
    if groups is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return groups


@router.get("/evidence/{evidence_id}/tg-media")
def get_tg_media(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Get media references from Telegram messages for evidence."""
    media = telegram_service.get_media_references(evidence_id, db)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found",
        )
    return media