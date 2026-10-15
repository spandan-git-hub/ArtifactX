"""Forensic analysis engine for ArtifactX."""

from forensic.whatsapp import (
    SchemaFamily,
    UnsupportedSchemaError,
    WAChat,
    WAContact,
    WAEdit,
    WAGroupParticipant,
    WALocationRef,
    WAMediaRef,
    WAMessage,
    WAQuotedRef,
    WARevocation,
    WAParseResult,
    WhatsAppParser,
    detect_wa_schema,
    is_whatsapp_database,
)

from forensic.telegram import (
    TelegramParser,
    detect_tg_schema,
    resolve_peer_from_did,
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


def is_telegram_database(conn_or_bytes) -> bool:
    """Helper to detect if database is Android Telegram cache4."""
    try:
        info = detect_tg_schema(conn_or_bytes)
        return info.family == "android_cache4"
    except Exception:
        return False


__all__ = [
    # WhatsApp
    "is_whatsapp_database",
    "extract_messages",
    "extract_contacts",
    "extract_groups",
    "extract_media_references",
    # Telegram
    "is_telegram_database",
    "TelegramParser",
    "detect_tg_schema",
    "resolve_peer_from_did",
    "TgChatRecord",
    "TgDialog",
    "TgMessageRecord",
    "TgParseResult",
    "TgPeerKind",
    "TgSchemaInfo",
    "TgUnparsedBlob",
    "TgUserRecord",
    "UnsupportedSchemaError",
    # Timeline
    "TimelineBuilder",
    "normalize_timestamp",
    # Deleted
    "DeletedDetector",
    # Media
    "detect_media_type",
    "extract_image_metadata",
    "extract_media_metadata",
    "find_orphan_media_items",
    "find_orphan_files",
    "mark_media_orphan_status",
    # Correlation
    "correlate_all",
    "EvidenceGraph",
]