"""
Pure forensic WhatsApp parsing toolkit (spec B7, master.md R4, R8, R12, R18).
"""

from pathlib import Path
from typing import BinaryIO, Union

from forensic.common.sqlite_open import open_sqlite_ro
from forensic.whatsapp.models import (
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
)
from forensic.whatsapp.parser import WAParseResult, WhatsAppParser
from forensic.whatsapp.schema import detect_wa_schema


def is_whatsapp_database(db_source: Union[Path, str, bytes, BinaryIO]) -> bool:
    """Check if the given database source matches a supported WhatsApp SQLite schema."""
    try:
        conn = open_sqlite_ro(db_source)
        try:
            schema = detect_wa_schema(conn)
            return schema.family in ("modern", "legacy")
        finally:
            conn.close()
    except Exception:
        return False


__all__ = [
    "WhatsAppParser",
    "WAParseResult",
    "SchemaFamily",
    "UnsupportedSchemaError",
    "detect_wa_schema",
    "is_whatsapp_database",
    "WAMessage",
    "WAChat",
    "WAContact",
    "WAGroupParticipant",
    "WARevocation",
    "WAEdit",
    "WAMediaRef",
    "WAQuotedRef",
    "WALocationRef",
]
