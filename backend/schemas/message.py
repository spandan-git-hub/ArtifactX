"""Pydantic schemas for WhatsApp Message."""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    evidence_id: int


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    message_id: Optional[Union[str, int]] = None
    key_remote_jid: Optional[str] = None
    sender_jid: Optional[str] = None
    participant_jid: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[int] = None
    media_type: Optional[str] = None
    media_path: Optional[str] = None
    message_type: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True