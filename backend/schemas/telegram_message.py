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
    mid: Optional[int] = None
    message_id: Optional[Union[str, int]] = None
    dialog_id: Optional[str] = None
    from_id: Optional[int] = None
    sender_id: Optional[int] = None
    out: Optional[int] = 0
    text: Optional[str] = None
    body: Optional[str] = None
    date_raw: Optional[int] = None
    date_unit: Optional[str] = "seconds"
    date_utc_ms: Optional[int] = None
    timestamp: Optional[int] = None
    media_kind: Optional[str] = None
    media_type: Optional[str] = None
    media_ref: Optional[str] = None
    media_path: Optional[str] = None
    message_type: Optional[str] = None
    reply_to_mid: Optional[int] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    entities: Optional[list] = None
    flags: Optional[list] = None
    read_state: Optional[int] = 1
    send_state: Optional[int] = 0
    view: Optional[str] = "main_view"
    source_table: Optional[str] = "messages_v2"
    source_row_id: Optional[int] = None
    finding_id: Optional[str] = None
    confidence_score: Optional[float] = 1.0
    strength: Optional[str] = "deterministic"
    provenance: Optional[dict] = None
    limitations: Optional[list] = None
    trailing_bytes_info: Optional[dict] = None

    class Config:
        from_attributes = True