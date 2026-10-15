"""
MTProto TL Serialized Object Dataclasses (spec B9.2).

Frozen dataclasses representing MTProto objects deserialized from binary blobs.
Follows master.md R4, R8, R10, R18.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


@dataclass(frozen=True)
class TgPeer:
    """Telegram peer reference (User, Chat, or Channel)."""
    peer_kind: Literal["user", "chat", "channel"]
    peer_id: int

    def to_dict(self) -> Dict[str, Any]:
        return {"peer_kind": self.peer_kind, "peer_id": self.peer_id}


@dataclass(frozen=True)
class TgEntity:
    """Formatted text message entity (bold, url, code, etc.)."""
    entity_type: str
    offset: int
    length: int
    url: Optional[str] = None
    user_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "offset": self.offset,
            "length": self.length,
            "url": self.url,
            "user_id": self.user_id,
        }


@dataclass(frozen=True)
class TgReplyHeader:
    """Quoted reply header snapshot."""
    reply_to_msg_id: Optional[int] = None
    reply_to_peer: Optional[TgPeer] = None
    quote_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply_to_msg_id": self.reply_to_msg_id,
            "reply_to_peer": self.reply_to_peer.to_dict() if self.reply_to_peer else None,
            "quote_text": self.quote_text,
        }


@dataclass(frozen=True)
class TgForward:
    """Forwarded message origin metadata."""
    date: int
    from_peer: Optional[TgPeer] = None
    from_name: Optional[str] = None
    channel_post: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "from_peer": self.from_peer.to_dict() if self.from_peer else None,
            "from_name": self.from_name,
            "channel_post": self.channel_post,
        }


@dataclass(frozen=True)
class TgMediaPhoto:
    """Photo media reference."""
    photo_id: Optional[int] = None
    access_hash: Optional[int] = None
    file_reference: Optional[bytes] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_kind": "photo",
            "photo_id": self.photo_id,
            "access_hash": self.access_hash,
            "file_reference_hex": self.file_reference.hex() if self.file_reference else None,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
        }


@dataclass(frozen=True)
class TgMediaDocument:
    """Document/file/audio media reference."""
    doc_id: Optional[int] = None
    access_hash: Optional[int] = None
    file_reference: Optional[bytes] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    voice: bool = False
    duration: Optional[int] = None
    file_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_kind": "audio" if self.voice else "document",
            "doc_id": self.doc_id,
            "access_hash": self.access_hash,
            "file_reference_hex": self.file_reference.hex() if self.file_reference else None,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "voice": self.voice,
            "duration": self.duration,
            "file_name": self.file_name,
        }


@dataclass(frozen=True)
class TgMediaGeo:
    """Geographic location coordinates."""
    latitude: float
    longitude: float
    accuracy_radius: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_kind": "location",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy_radius": self.accuracy_radius,
        }


@dataclass(frozen=True)
class TgMediaEmpty:
    """Empty or unsupported media placeholder."""
    def to_dict(self) -> Dict[str, Any]:
        return {"media_kind": "empty"}


@dataclass(frozen=True)
class TgMessage:
    """MTProto TLRPC.Message deserialized object."""
    id: int
    peer: TgPeer
    from_peer: Optional[TgPeer]
    date: int
    message: str
    out: bool
    media: Optional[Any] = None
    reply_to: Optional[TgReplyHeader] = None
    entities: Optional[Tuple[TgEntity, ...]] = None
    fwd_from: Optional[TgForward] = None
    edit_date: Optional[int] = None
    grouped_id: Optional[int] = None
    trailing_bytes: Optional[bytes] = None
    flags: int = 0
    flags2: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "peer": self.peer.to_dict(),
            "from_peer": self.from_peer.to_dict() if self.from_peer else None,
            "date": self.date,
            "message": self.message,
            "out": self.out,
            "media": self.media.to_dict() if hasattr(self.media, "to_dict") else None,
            "reply_to": self.reply_to.to_dict() if self.reply_to else None,
            "entities": [e.to_dict() for e in self.entities] if self.entities else [],
            "fwd_from": self.fwd_from.to_dict() if self.fwd_from else None,
            "edit_date": self.edit_date,
            "grouped_id": self.grouped_id,
            "trailing_bytes_len": len(self.trailing_bytes) if self.trailing_bytes else 0,
        }


@dataclass(frozen=True)
class TgMessageService:
    """MTProto TLRPC.MessageService action message."""
    id: int
    peer: TgPeer
    from_peer: Optional[TgPeer]
    date: int
    out: bool
    action_type: str = "service"
    trailing_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "peer": self.peer.to_dict(),
            "from_peer": self.from_peer.to_dict() if self.from_peer else None,
            "date": self.date,
            "out": self.out,
            "action_type": self.action_type,
        }


@dataclass(frozen=True)
class TgMessageEmpty:
    """MTProto TLRPC.MessageEmpty tombstone."""
    id: int
    peer: Optional[TgPeer] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "peer": self.peer.to_dict() if self.peer else None,
        }


@dataclass(frozen=True)
class TgUser:
    """MTProto TLRPC.User profile."""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    is_self: bool = False
    contact: bool = False
    deleted: bool = False
    bot: bool = False
    trailing_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "phone": self.phone,
            "is_self": self.is_self,
            "contact": self.contact,
            "deleted": self.deleted,
            "bot": self.bot,
        }


@dataclass(frozen=True)
class TgUserEmpty:
    """Empty user placeholder."""
    id: int

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "empty": True}


@dataclass(frozen=True)
class TgChat:
    """MTProto TLRPC.Chat group profile."""
    id: int
    title: str
    participants_count: int = 0
    date: int = 0
    creator: bool = False
    left: bool = False
    deactivated: bool = False
    trailing_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "participants_count": self.participants_count,
            "date": self.date,
            "creator": self.creator,
            "left": self.left,
            "deactivated": self.deactivated,
            "is_channel": False,
        }


@dataclass(frozen=True)
class TgChannel:
    """MTProto TLRPC.Channel supergroup or broadcast channel profile."""
    id: int
    title: str
    username: Optional[str] = None
    participants_count: Optional[int] = None
    date: int = 0
    creator: bool = False
    left: bool = False
    broadcast: bool = False
    megagroup: bool = False
    trailing_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "username": self.username,
            "participants_count": self.participants_count,
            "date": self.date,
            "creator": self.creator,
            "left": self.left,
            "broadcast": self.broadcast,
            "megagroup": self.megagroup,
            "is_channel": True,
        }


@dataclass(frozen=True)
class TgChatEmpty:
    """Empty chat placeholder."""
    id: int

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "empty": True}


@dataclass(frozen=True)
class TgChatForbidden:
    """Forbidden/inaccessible chat."""
    id: int
    title: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "title": self.title, "forbidden": True}
