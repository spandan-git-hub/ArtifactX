"""Pydantic schemas for Telegram forensic models (B9.6)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TelegramDialogRead(BaseModel):
    id: int
    evidence_id: int
    dialog_id: int
    peer_kind: str
    peer_id: int
    title: Optional[str] = None
    last_mid: Optional[int] = None
    unread_count: int = 0
    pinned: bool = False
    finding_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    limitations: Optional[List[str]] = None

    class Config:
        from_attributes = True


class TelegramUserRead(BaseModel):
    id: int
    evidence_id: int
    uid: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    is_self: bool = False
    contact: bool = False
    deleted: bool = False
    bot: bool = False
    finding_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TelegramChatRead(BaseModel):
    id: int
    evidence_id: int
    did: int
    chat_id: int
    title: str
    is_channel: bool = False
    is_group: bool = True
    participants_count: int = 0
    participant_uids: Optional[List[int]] = None
    finding_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TelegramUnparsedBlobRead(BaseModel):
    id: int
    evidence_id: int
    table: str
    row_id: int
    mid: Optional[int] = None
    uid: Optional[int] = None
    constructor_id_hex: Optional[str] = None
    length: int
    sha256: str
    reason: str
    container_metadata: Optional[Dict[str, Any]] = None
    finding_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
