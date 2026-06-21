"""Pydantic schemas for Telegram Contact."""

from typing import Optional

from pydantic import BaseModel, Field


class TelegramContactBase(BaseModel):
    evidence_id: int


class TelegramContactCreate(TelegramContactBase):
    pass


class TelegramContactRead(TelegramContactBase):
    id: int
    user_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True