"""Pydantic schemas for WhatsApp Group."""

from typing import Optional

from pydantic import BaseModel, Field


class GroupBase(BaseModel):
    evidence_id: int


class GroupCreate(GroupBase):
    pass


class GroupRead(GroupBase):
    id: int
    group_jid: Optional[str] = None
    subject: Optional[str] = None
    creator_jid: Optional[str] = None
    creation_timestamp: Optional[int] = None

    class Config:
        from_attributes = True