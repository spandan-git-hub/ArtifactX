"""Pydantic schemas for WhatsApp Contact."""

from typing import Optional

from pydantic import BaseModel, Field


class ContactBase(BaseModel):
    evidence_id: int


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int
    jid: Optional[str] = None
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True