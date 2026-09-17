"""Deleted message detection and physical SQLite recovery modules."""

from forensic.deleted.detector import DeletedDetector
from forensic.deleted.sqlite_record import (
    decode_varint,
    encode_varint,
    decode_serial_type,
    parse_record_header,
    unpack_record,
    find_candidate_records,
)
from forensic.deleted.wal_carver import WalCarver, WalHeader, WalFrame, WalPageImage
from forensic.deleted.freelist_carver import FreelistCarver, SqliteDbHeader, FreelistPage
from forensic.deleted.slack_carver import SlackCarver, BtreeHeader, SlackSpan
from forensic.deleted.payload_decoder import (
    WhatsAppPayloadDecoder,
    TelegramPayloadDecoder,
    DecodedPayload,
)
from forensic.deleted.orchestrator import DeletedRecoveryEngine, make_hex_preview

__all__ = [
    "DeletedDetector",
    "WalCarver",
    "WalHeader",
    "WalFrame",
    "WalPageImage",
    "FreelistCarver",
    "SqliteDbHeader",
    "FreelistPage",
    "SlackCarver",
    "BtreeHeader",
    "SlackSpan",
    "WhatsAppPayloadDecoder",
    "TelegramPayloadDecoder",
    "DecodedPayload",
    "DeletedRecoveryEngine",
    "decode_varint",
    "encode_varint",
    "decode_serial_type",
    "parse_record_header",
    "unpack_record",
    "find_candidate_records",
    "make_hex_preview",
]