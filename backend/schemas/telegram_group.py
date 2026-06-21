"""Pydantic schemas for Telegram Group."""

from typing import Optional

from pydantic import BaseModel, Field


class TelegramGroupBase(BaseModel):
    evidence_id: int


class TelegramGroupCreate(TelegramGroupBase):
    pass


class TelegramGroupRead(TelegramGroupBase):
    id: int
    group_id: Optional[int] = None
    title: Optional[str] = None
    username: Optional[str] = None
    type: Optional[str] = None

    class Config:
        from_attributes = True