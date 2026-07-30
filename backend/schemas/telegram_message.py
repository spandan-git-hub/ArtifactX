"""Pydantic schemas for Telegram Message."""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class TelegramMessageBase(BaseModel):
    evidence_id: int


class TelegramMessageCreate(TelegramMessageBase):
    pass


class TelegramMessageRead(TelegramMessageBase):
    id: int
    message_id: Optional[Union[str, int]] = None
    dialog_id: Optional[str] = None
    sender_id: Optional[int] = None
    body: Optional[str] = None
    timestamp: Optional[int] = None
    media_type: Optional[str] = None
    media_path: Optional[str] = None
    message_type: Optional[str] = None

    class Config:
        from_attributes = True