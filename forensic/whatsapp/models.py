"""
Data structures for WhatsApp forensic parsing (spec B7.0–B7.4, master.md R8, R10).
All data structures are immutable frozen dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from forensic.common.contracts import FindingBase, Provenance, Strength


@dataclass(frozen=True)
class SchemaFamily:
    """Introspected WhatsApp schema family and capability flags (B7.1)."""
    family: Literal["modern", "legacy", "unknown"]
    tables: Tuple[str, ...]
    columns: Dict[str, Tuple[str, ...]]
    capabilities: Dict[str, bool]
    notes: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "tables": list(self.tables),
            "columns": {k: list(v) for k, v in self.columns.items()},
            "capabilities": dict(self.capabilities),
            "notes": list(self.notes),
        }


class UnsupportedSchemaError(Exception):
    """Raised when SQLite database schema does not match known WhatsApp schemas (B7.1)."""
    def __init__(self, message: str, tables_seen: Set[str]):
        super().__init__(message)
        self.tables_seen = tables_seen


@dataclass(frozen=True)
class WAMediaRef:
    """Extracted media attachment reference (B7.3)."""
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    media_name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    file_hash: Optional[str] = None
    media_key_present: bool = False
    media_missing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "media_name": self.media_name,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "file_hash": self.file_hash,
            "media_key_present": self.media_key_present,
            "media_missing": self.media_missing,
        }


@dataclass(frozen=True)
class WAQuotedRef:
    """Quoted reply snapshot metadata (B7.3)."""
    quoted_row_id: Optional[int] = None
    key_id: Optional[str] = None
    parent_key_id: Optional[str] = None
    sender_jid: Optional[str] = None
    timestamp_raw: Optional[int] = None
    message_type: Optional[int] = None
    text_data: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quoted_row_id": self.quoted_row_id,
            "key_id": self.key_id,
            "parent_key_id": self.parent_key_id,
            "sender_jid": self.sender_jid,
            "timestamp_raw": self.timestamp_raw,
            "message_type": self.message_type,
            "text_data": self.text_data,
        }


@dataclass(frozen=True)
class WALocationRef:
    """Extracted geographic location coordinates (B7.3)."""
    latitude: float
    longitude: float
    place_name: Optional[str] = None
    place_address: Optional[str] = None
    url: Optional[str] = None
    live_duration: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "place_name": self.place_name,
            "place_address": self.place_address,
            "url": self.url,
            "live_duration": self.live_duration,
        }


@dataclass(frozen=True)
class WAMessage:
    """Forensic WhatsApp message record with full provenance (B7.3)."""
    row_id: int
    key_id: str
    chat_row_id: Optional[int]
    chat_jid: str
    from_me: int
    sender_jid: str
    message_type_code: int
    message_type_name: str
    text: Optional[str]
    ts_raw: int
    ts_unit: str
    ts_utc_ms: int
    received_ts_raw: Optional[int]
    status: int
    starred: bool
    media_ref: Optional[WAMediaRef]
    quoted_ref: Optional[WAQuotedRef]
    location_ref: Optional[WALocationRef]
    flags: Tuple[str, ...]
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "key_id": self.key_id,
            "chat_row_id": self.chat_row_id,
            "chat_jid": self.chat_jid,
            "from_me": self.from_me,
            "sender_jid": self.sender_jid,
            "message_type_code": self.message_type_code,
            "message_type_name": self.message_type_name,
            "text": self.text,
            "ts_raw": self.ts_raw,
            "ts_unit": self.ts_unit,
            "ts_utc_ms": self.ts_utc_ms,
            "received_ts_raw": self.received_ts_raw,
            "status": self.status,
            "starred": self.starred,
            "media_ref": self.media_ref.to_dict() if self.media_ref else None,
            "quoted_ref": self.quoted_ref.to_dict() if self.quoted_ref else None,
            "location_ref": self.location_ref.to_dict() if self.location_ref else None,
            "flags": list(self.flags),
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True)
class WARevocation(FindingBase):
    """Tier-1 explicit revocation record for 'Delete for Everyone' messages (B7.4)."""
    message_row_id: int = 0
    revoked_key_id: str = ""
    revoke_ts: Optional[int] = None
    admin_jid: Optional[str] = None
    original_sender: Optional[str] = None
    original_ts: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "message_row_id": self.message_row_id,
            "revoked_key_id": self.revoked_key_id,
            "revoke_ts": self.revoke_ts,
            "admin_jid": self.admin_jid,
            "original_sender": self.original_sender,
            "original_ts": self.original_ts,
        })
        return d


@dataclass(frozen=True)
class WAEdit(FindingBase):
    """Edit history record for modified messages (B7.4)."""
    message_row_id: int = 0
    original_key_id: str = ""
    edited_ts: int = 0
    sender_ts: Optional[int] = None
    prior_text_not_present: bool = True
    edited_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "message_row_id": self.message_row_id,
            "original_key_id": self.original_key_id,
            "edited_ts": self.edited_ts,
            "sender_ts": self.sender_ts,
            "prior_text_not_present": self.prior_text_not_present,
            "edited_text": self.edited_text,
        })
        return d


@dataclass(frozen=True)
class WAChat:
    """WhatsApp chat thread (B7.2)."""
    chat_row_id: int
    chat_jid: str
    subject: Optional[str]
    is_group: bool
    hidden: int
    archived: int
    last_message_row_id: Optional[int]
    participant_jids: Tuple[str, ...]
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_row_id": self.chat_row_id,
            "chat_jid": self.chat_jid,
            "subject": self.subject,
            "is_group": self.is_group,
            "hidden": self.hidden,
            "archived": self.archived,
            "last_message_row_id": self.last_message_row_id,
            "participant_jids": list(self.participant_jids),
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True)
class WAContact:
    """WhatsApp contact (B7.2)."""
    jid: str
    display_name: str
    phone_number: Optional[str]
    is_group: bool
    source: str
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jid": self.jid,
            "display_name": self.display_name,
            "phone_number": self.phone_number,
            "is_group": self.is_group,
            "source": self.source,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True)
class WAGroupParticipant:
    """Group participant membership record (B7.2)."""
    group_jid: str
    user_jid: str
    rank: int
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_jid": self.group_jid,
            "user_jid": self.user_jid,
            "rank": self.rank,
            "provenance": self.provenance.to_dict(),
        }
