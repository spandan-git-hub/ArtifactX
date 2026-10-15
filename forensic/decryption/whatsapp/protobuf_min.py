"""
Minimal, dependency-free Protocol Buffers wire format reader.
Specifically designed for WhatsApp backup container headers (BackupPrefix).
Strictly adheres to master.md R12 (untrusted input hardening).
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple, Union

from forensic.decryption.whatsapp.errors import HeaderError, TruncatedInput
from forensic.decryption.whatsapp.types import ParsedHeader


def decode_varint(buffer: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Decode an unsigned protobuf varint from buffer starting at offset.
    Returns (value, next_offset).
    Raises TruncatedInput if buffer ends before varint terminates.
    Raises HeaderError if varint exceeds 10 bytes (64-bit int max).
    """
    value = 0
    shift = 0
    idx = offset
    buf_len = len(buffer)

    while True:
        if idx >= buf_len:
            raise TruncatedInput("Buffer truncated while reading protobuf varint.")
        byte = buffer[idx]
        idx += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
        if shift > 70:
            raise HeaderError("Protobuf varint exceeds maximum allowable length.")

    return value, idx


class ProtobufReader:
    """Minimal protobuf wire parser operating strictly on memory slices."""

    WIRE_VARINT = 0
    WIRE_64BIT = 1
    WIRE_LENGTH_DELIMITED = 2
    WIRE_32BIT = 5

    @classmethod
    def parse_fields(cls, data: bytes) -> Dict[int, List[Tuple[int, Any]]]:
        """
        Parse raw protobuf message bytes into a dictionary of field_number -> [(wire_type, value)].
        Handles multi-occurrence fields gracefully.
        """
        fields: Dict[int, List[Tuple[int, Any]]] = {}
        offset = 0
        buf_len = len(data)

        while offset < buf_len:
            tag, offset = decode_varint(data, offset)
            field_number = tag >> 3
            wire_type = tag & 0x07

            if wire_type == cls.WIRE_VARINT:
                val, offset = decode_varint(data, offset)
                fields.setdefault(field_number, []).append((wire_type, val))

            elif wire_type == cls.WIRE_64BIT:
                if offset + 8 > buf_len:
                    raise TruncatedInput("Truncated 64-bit protobuf field.")
                val = data[offset : offset + 8]
                offset += 8
                fields.setdefault(field_number, []).append((wire_type, val))

            elif wire_type == cls.WIRE_LENGTH_DELIMITED:
                length, offset = decode_varint(data, offset)
                if length < 0 or offset + length > buf_len:
                    raise TruncatedInput(f"Truncated length-delimited field of length {length}.")
                val = data[offset : offset + length]
                offset += length
                fields.setdefault(field_number, []).append((wire_type, val))

            elif wire_type == cls.WIRE_32BIT:
                if offset + 4 > buf_len:
                    raise TruncatedInput("Truncated 32-bit protobuf field.")
                val = data[offset : offset + 4]
                offset += 4
                fields.setdefault(field_number, []).append((wire_type, val))

            else:
                raise HeaderError(f"Unsupported protobuf wire type: {wire_type}")

        return fields

    @classmethod
    def parse_header(cls, buffer: bytes) -> ParsedHeader:
        """
        Parse WhatsApp BackupPrefix container header from raw file buffer.
        Extracts format (crypt14 vs crypt15), IV, salts, and metadata.
        """
        if len(buffer) < 4:
            raise TruncatedInput("Buffer too small to contain WhatsApp backup header.")

        # 1. Read varint prefix indicating length of BackupPrefix protobuf
        protobuf_size, header_offset = decode_varint(buffer, 0)
        total_header_size = header_offset + protobuf_size

        if total_header_size > len(buffer):
            raise TruncatedInput(
                f"Buffer truncated: header specifies {protobuf_size} bytes protobuf, "
                f"total header requires {total_header_size} bytes, got {len(buffer)} bytes."
            )

        protobuf_raw = buffer[header_offset:total_header_size]
        raw_header = buffer[:total_header_size]

        fields = cls.parse_fields(protobuf_raw)

        # Inspect BackupPrefix fields:
        # Field 1: key_type_deprecated (varint)
        # Field 2: wa_provided_key_data (embedded C14Cipher)
        # Field 3: e2ee_key_data (embedded C15IV)
        # Field 4: backup_metadata (embedded BackupExpiry)
        # Field 6: key_type_new (varint)

        key_type = None
        if 6 in fields:
            key_type = fields[6][0][1]
        elif 1 in fields:
            key_type = fields[1][0][1]

        # Check crypt15 (Field 3: e2ee_key_data)
        if 3 in fields:
            e2ee_bytes = fields[3][0][1]
            e2ee_fields = cls.parse_fields(e2ee_bytes)
            # Inside C15IV: Field 1 is encryption_iv (bytes)
            if 1 in e2ee_fields:
                iv = e2ee_fields[1][0][1]
                app_version, jid_suffix = cls._extract_metadata(fields)
                return ParsedHeader(
                    format_id="crypt15",
                    header_size=total_header_size,
                    iv=iv,
                    key_type=key_type,
                    app_version=app_version,
                    jid_suffix=jid_suffix,
                    raw_header=raw_header,
                )

        # Check crypt14 (Field 2: wa_provided_key_data)
        if 2 in fields:
            c14_bytes = fields[2][0][1]
            c14_fields = cls.parse_fields(c14_bytes)
            # Inside C14Cipher:
            # Field 3: server_salt (bytes)
            # Field 4: google_id_salt (bytes)
            # Field 5: encryption_iv (bytes)
            iv = c14_fields[5][0][1] if 5 in c14_fields else b""
            server_salt = c14_fields[3][0][1] if 3 in c14_fields else None
            google_id_salt = c14_fields[4][0][1] if 4 in c14_fields else None
            app_version, jid_suffix = cls._extract_metadata(fields)

            return ParsedHeader(
                format_id="crypt14",
                header_size=total_header_size,
                iv=iv,
                key_type=key_type,
                server_salt=server_salt,
                google_id_salt=google_id_salt,
                app_version=app_version,
                jid_suffix=jid_suffix,
                raw_header=raw_header,
            )

        raise HeaderError("Unrecognized WhatsApp backup header: neither crypt14 nor crypt15 key data found.")

    @classmethod
    def _extract_metadata(cls, fields: Dict[int, List[Tuple[int, Any]]]) -> Tuple[Optional[str], Optional[str]]:
        """Extract app_version and jid_suffix from backup_metadata (field 4)."""
        app_version = None
        jid_suffix = None
        if 4 in fields:
            meta_bytes = fields[4][0][1]
            meta_fields = cls.parse_fields(meta_bytes)
            # Field 1 in BackupExpiry is app_version (string/bytes)
            if 1 in meta_fields:
                raw_ver = meta_fields[1][0][1]
                if isinstance(raw_ver, bytes):
                    app_version = raw_ver.decode("utf-8", errors="replace")
            # Field 2 in BackupExpiry is jid_suffix (string/bytes)
            if 2 in meta_fields:
                raw_suf = meta_fields[2][0][1]
                if isinstance(raw_suf, bytes):
                    jid_suffix = raw_suf.decode("utf-8", errors="replace")
        return app_version, jid_suffix
