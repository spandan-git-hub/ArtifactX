"""Pydantic schemas for WhatsApp Message (B7.5 additive expansion)."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    evidence_id: int


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    model_config = ConfigDict(from_attributes=True)

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

    # Forensic additions (spec B7.5)
    key_id: Optional[str] = None
    chat_row_id: Optional[int] = None
    message_type_code: Optional[int] = None
    message_type_name: Optional[str] = None
    ts_raw: Optional[int] = None
    ts_unit: Optional[str] = "ms"
    ts_utc_ms: Optional[int] = None
    received_ts_raw: Optional[int] = None
    source_table: Optional[str] = None
    source_row_id: Optional[int] = None
    derived_artifact_id: Optional[str] = None
    evidence_sha256: Optional[str] = None
    quoted_row_id: Optional[int] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    is_revoked: Optional[bool] = False
    is_edited: Optional[bool] = False
    flags: Optional[List[str]] = None