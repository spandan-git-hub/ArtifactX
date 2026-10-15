"""
Forensic Telegram Analysis Package (spec B9.0–B9.6).

Zero-disk read-only operations for Telegram cache4.db evidence.
"""

from forensic.telegram.models import (
    TgChatRecord,
    TgDialog,
    TgMessageRecord,
    TgParseResult,
    TgPeerKind,
    TgSchemaInfo,
    TgUnparsedBlob,
    TgUserRecord,
    UnsupportedSchemaError,
)
from forensic.telegram.parser import TelegramParser, resolve_peer_from_did
from forensic.telegram.schema import detect_tg_schema

__all__ = [
    "TelegramParser",
    "resolve_peer_from_did",
    "detect_tg_schema",
    "TgChatRecord",
    "TgDialog",
    "TgMessageRecord",
    "TgParseResult",
    "TgPeerKind",
    "TgSchemaInfo",
    "TgUnparsedBlob",
    "TgUserRecord",
    "UnsupportedSchemaError",
]
