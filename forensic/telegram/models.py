"""
Forensic data structures for Telegram parsing (spec B9.0–B9.6, master.md R8, R10).
All data structures are immutable frozen dataclasses conforming to FindingBase and Provenance contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from forensic.common.contracts import FindingBase, Provenance, Strength

TgPeerKind = Literal["user", "chat", "channel", "secret_chat_marker", "unknown"]


@dataclass(frozen=True)
class TgSchemaInfo:
    """Introspected Telegram schema family and capability flags (B9.1)."""
    family: Literal["android_cache4", "unknown"]
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
    """Raised when SQLite database schema does not match known Telegram schemas (B9.1)."""
    def __init__(self, message: str, tables_seen: Set[str]):
        super().__init__(message)
        self.tables_seen = tables_seen


@dataclass(frozen=True)
class TgUnparsedBlob(FindingBase):
    """
    Honest fallback record for unparsable or unknown MTProto blobs (B9.3).
    Guarantees: parsed_count + unparsed_count == rows_seen per table (no silent drops).
    """
    table: str = "messages_v2"
    row_id: int = 0
    mid: Optional[int] = None
    uid: Optional[int] = None
    constructor_id_hex: Optional[str] = None
    length: int = 0
    sha256: str = ""
    reason: str = ""
    container_metadata: Dict[str, Any] = None  # type: ignore

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "table": self.table,
            "row_id": self.row_id,
            "mid": self.mid,
            "uid": self.uid,
            "constructor_id_hex": self.constructor_id_hex,
            "length": self.length,
            "sha256": self.sha256,
            "reason": self.reason,
            "container_metadata": dict(self.container_metadata or {}),
        })
        return d


@dataclass(frozen=True)
class TgDialog(FindingBase):
    """Telegram conversation thread / dialog record (B9.4)."""
    dialog_id: int = 0
    peer_kind: TgPeerKind = "unknown"
    peer_id: int = 0
    title: Optional[str] = None
    last_mid: Optional[int] = None
    unread_count: int = 0
    pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "dialog_id": self.dialog_id,
            "peer_kind": self.peer_kind,
            "peer_id": self.peer_id,
            "title": self.title,
            "last_mid": self.last_mid,
            "unread_count": self.unread_count,
            "pinned": self.pinned,
        })
        return d


@dataclass(frozen=True)
class TgUserRecord(FindingBase):
    """Cached user profile extracted from users table TL blob (B9.4)."""
    uid: int = 0
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    is_self: bool = False
    contact: bool = False
    deleted: bool = False
    bot: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "uid": self.uid,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "phone": self.phone,
            "is_self": self.is_self,
            "contact": self.contact,
            "deleted": self.deleted,
            "bot": self.bot,
        })
        return d


@dataclass(frozen=True)
class TgChatRecord(FindingBase):
    """Group, supergroup or broadcast channel profile (B9.4)."""
    did: int = 0
    chat_id: int = 0
    title: str = ""
    is_channel: bool = False
    is_group: bool = True
    participants_count: int = 0
    participant_uids: Tuple[int, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "did": self.did,
            "chat_id": self.chat_id,
            "title": self.title,
            "is_channel": self.is_channel,
            "is_group": self.is_group,
            "participants_count": self.participants_count,
            "participant_uids": list(self.participant_uids),
        })
        return d


@dataclass(frozen=True)
class TgMessageRecord(FindingBase):
    """Forensic Telegram message record with full provenance and dual timestamps (B9.4, R8, R10)."""
    mid: int = 0
    dialog_id: int = 0
    from_id: Optional[int] = None
    out: int = 0
    date_raw: int = 0
    date_unit: str = "seconds"
    date_utc_ms: int = 0
    text: Optional[str] = None
    media_kind: Optional[str] = None
    media_ref: Optional[str] = None
    reply_to_mid: Optional[int] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    entities: Tuple[Dict[str, Any], ...] = ()
    flags: Tuple[str, ...] = ()
    read_state: int = 1
    send_state: int = 0
    view: str = "main_view"
    trailing_bytes_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "mid": self.mid,
            "dialog_id": self.dialog_id,
            "from_id": self.from_id,
            "out": self.out,
            "date_raw": self.date_raw,
            "date_unit": self.date_unit,
            "date_utc_ms": self.date_utc_ms,
            "text": self.text,
            "media_kind": self.media_kind,
            "media_ref": self.media_ref,
            "reply_to_mid": self.reply_to_mid,
            "geo_lat": self.geo_lat,
            "geo_lon": self.geo_lon,
            "entities": list(self.entities),
            "flags": list(self.flags),
            "read_state": self.read_state,
            "send_state": self.send_state,
            "view": self.view,
            "trailing_bytes_info": dict(self.trailing_bytes_info) if self.trailing_bytes_info else None,
        })
        return d


@dataclass(frozen=True)
class TgParseResult:
    """Forensic parse output container for Telegram artifacts."""
    schema_info: TgSchemaInfo
    messages: Tuple[TgMessageRecord, ...]
    dialogs: Tuple[TgDialog, ...]
    users: Tuple[TgUserRecord, ...]
    chats: Tuple[TgChatRecord, ...]
    unparsed_blobs: Tuple[TgUnparsedBlob, ...]
    views_parsed: Tuple[str, ...]
    limitations: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_info": self.schema_info.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
            "dialogs": [d.to_dict() for d in self.dialogs],
            "users": [u.to_dict() for u in self.users],
            "chats": [c.to_dict() for c in self.chats],
            "unparsed_blobs": [b.to_dict() for b in self.unparsed_blobs],
            "views_parsed": list(self.views_parsed),
            "limitations": list(self.limitations),
        }
