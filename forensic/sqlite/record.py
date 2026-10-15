"""
SQLite record, serial type, and varint decoders.

Implements SQLite record header decoding, type-safe column unpacking,
text encoding handling (UTF-8, UTF-16LE, UTF-16BE), and cell spill calculations
per https://www.sqlite.org/fileformat2.html §1.6 and §2.1.
"""

from dataclasses import dataclass
import struct
from typing import Any, List, Optional, Tuple, Union

from forensic.sqlite.constants import (
    TEXT_ENCODING_UTF8,
    TEXT_ENCODING_UTF16BE,
    TEXT_ENCODING_UTF16LE,
)
from forensic.sqlite.exceptions import CorruptPage


def decode_varint(data: Union[bytes, memoryview], offset: int = 0) -> Tuple[int, int]:
    """
    Decode a variable-length integer (varint) from SQLite raw bytes.

    SQLite varints are 1 to 9 bytes long.
    - Bytes 1 to 8: high bit is continuation flag, low 7 bits are payload.
    - Byte 9 (if reached): all 8 bits are used.

    Returns:
        (value, bytes_consumed)

    Raises:
        CorruptPage: If buffer is truncated or offset out of bounds.
    """
    buf_len = len(data)
    if offset >= buf_len:
        raise CorruptPage(f"Varint decode offset {offset} out of bounds (len={buf_len})", offset=offset)

    val = 0
    for i in range(8):
        pos = offset + i
        if pos >= buf_len:
            raise CorruptPage(f"Truncated varint at byte {pos}", offset=pos)
        b = data[pos]
        val = (val << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            return val, i + 1

    # 9th byte uses all 8 bits directly
    pos = offset + 8
    if pos >= buf_len:
        raise CorruptPage(f"Truncated 9-byte varint at byte {pos}", offset=pos)
    val = (val << 8) | data[pos]
    return val, 9


def encode_varint(val: int) -> bytes:
    """
    Encode a non-negative integer as an SQLite varint.
    Used for unit testing, synthetic pages, and record encoding.
    """
    if val < 0:
        # SQLite interprets negative numbers as two's complement 64-bit int
        val = val & 0xFFFFFFFFFFFFFFFF

    if val <= 0x7F:
        return bytes([val])

    buf = []
    temp = val
    if temp > 0x00FFFFFFFFFFFFFF:
        # 9th byte takes full 8 bits
        buf.append(temp & 0xFF)
        temp >>= 8
        while temp > 0:
            buf.append((temp & 0x7F) | 0x80)
            temp >>= 7
        return bytes(reversed(buf))

    while temp > 0:
        b = temp & 0x7F
        temp >>= 7
        if buf:
            b |= 0x80
        buf.append(b)
    return bytes(reversed(buf))


def compute_payload_spill(
    usable_page_size: int,
    payload_len: int,
    is_table_leaf: bool = True,
) -> Tuple[int, bool]:
    """
    Compute local vs overflow payload length per SQLite fileformat2.html §1.6.

    Let U be the usable page size (page_size - reserved).
    For Table B-tree Leaf cells:
      X = U - 35
      M = ((U - 12) * 32 // 255) - 23
    If payload_len <= X:
      local_len = payload_len, overflow = False
    Else:
      K = M + ((payload_len - M) % (U - 4))
      local_len = K if K <= X else M
      overflow = True

    Returns:
        (local_payload_len, has_overflow)
    """
    U = usable_page_size
    if is_table_leaf:
        X = U - 35
        M = ((U - 12) * 32 // 255) - 23
    else:
        # Index or interior page
        X = ((U - 12) * 64 // 255) - 23
        M = ((U - 12) * 32 // 255) - 23

    if payload_len <= X:
        return payload_len, False

    K = M + ((payload_len - M) % (U - 4))
    local_len = K if K <= X else M
    return local_len, True


@dataclass(frozen=True)
class DecodedRecord:
    """Detailed result of decoding an SQLite record."""
    values: List[Any]
    serial_types: List[int]
    header_length: int
    has_encoding_errors: bool


def decode_record(
    payload: Union[bytes, memoryview],
    text_encoding: int = TEXT_ENCODING_UTF8,
) -> List[Any]:
    """
    Decode an SQLite record payload into a list of Python values.

    Args:
        payload: Complete record payload bytes (local + assembled overflow).
        text_encoding: 1=UTF-8, 2=UTF-16LE, 3=UTF-16BE.

    Returns:
        list of decoded values (None, int, float, str, bytes).
    """
    return decode_record_detailed(payload, text_encoding).values


def decode_record_detailed(
    payload: Union[bytes, memoryview],
    text_encoding: int = TEXT_ENCODING_UTF8,
) -> DecodedRecord:
    """
    Decode an SQLite record payload with full metadata (serial types and encoding errors).

    Handles all serial types 0..9, BLOB (>=12 even), and TEXT (>=13 odd).
    """
    if len(payload) == 0:
        return DecodedRecord(values=[], serial_types=[], header_length=0, has_encoding_errors=False)

    hdr_len, consumed = decode_varint(payload, 0)
    if hdr_len < consumed or hdr_len > len(payload):
        raise CorruptPage(f"Invalid record header length {hdr_len} (payload len={len(payload)})", offset=0)

    serial_types: List[int] = []
    off = consumed
    while off < hdr_len:
        st, c = decode_varint(payload, off)
        serial_types.append(st)
        off += c

    values: List[Any] = []
    val_off = hdr_len
    has_enc_err = False

    enc_map = {
        TEXT_ENCODING_UTF8: "utf-8",
        TEXT_ENCODING_UTF16LE: "utf-16le",
        TEXT_ENCODING_UTF16BE: "utf-16be",
    }
    codec = enc_map.get(text_encoding, "utf-8")

    for st in serial_types:
        if st == 0:
            values.append(None)
        elif st == 1:
            if val_off + 1 > len(payload):
                raise CorruptPage("Truncated INT8 column in record", offset=val_off)
            val = struct.unpack_from(">b", payload, val_off)[0]
            values.append(val)
            val_off += 1
        elif st == 2:
            if val_off + 2 > len(payload):
                raise CorruptPage("Truncated INT16 column in record", offset=val_off)
            val = struct.unpack_from(">h", payload, val_off)[0]
            values.append(val)
            val_off += 2
        elif st == 3:
            if val_off + 3 > len(payload):
                raise CorruptPage("Truncated INT24 column in record", offset=val_off)
            raw = bytes(payload[val_off : val_off + 3])
            ext = b"\xff" if raw[0] >= 0x80 else b"\x00"
            val = struct.unpack(">i", ext + raw)[0]
            values.append(val)
            val_off += 3
        elif st == 4:
            if val_off + 4 > len(payload):
                raise CorruptPage("Truncated INT32 column in record", offset=val_off)
            val = struct.unpack_from(">i", payload, val_off)[0]
            values.append(val)
            val_off += 4
        elif st == 5:
            if val_off + 6 > len(payload):
                raise CorruptPage("Truncated INT48 column in record", offset=val_off)
            raw = bytes(payload[val_off : val_off + 6])
            ext = b"\xff\xff" if raw[0] >= 0x80 else b"\x00\x00"
            val = struct.unpack(">q", ext + raw)[0]
            values.append(val)
            val_off += 6
        elif st == 6:
            if val_off + 8 > len(payload):
                raise CorruptPage("Truncated INT64 column in record", offset=val_off)
            val = struct.unpack_from(">q", payload, val_off)[0]
            values.append(val)
            val_off += 8
        elif st == 7:
            if val_off + 8 > len(payload):
                raise CorruptPage("Truncated FLOAT64 column in record", offset=val_off)
            val = struct.unpack_from(">d", payload, val_off)[0]
            values.append(val)
            val_off += 8
        elif st == 8:
            values.append(0)
        elif st == 9:
            values.append(1)
        elif st in (10, 11):
            values.append(None)
        elif st >= 12 and (st % 2 == 0):
            # BLOB
            blen = (st - 12) // 2
            if val_off + blen > len(payload):
                raise CorruptPage(f"Truncated BLOB column (len {blen}) in record", offset=val_off)
            values.append(bytes(payload[val_off : val_off + blen]))
            val_off += blen
        elif st >= 13 and (st % 2 == 1):
            # TEXT
            tlen = (st - 13) // 2
            if val_off + tlen > len(payload):
                raise CorruptPage(f"Truncated TEXT column (len {tlen}) in record", offset=val_off)
            raw_text = bytes(payload[val_off : val_off + tlen])
            try:
                decoded_str = raw_text.decode(codec)
            except UnicodeDecodeError:
                decoded_str = raw_text.decode(codec, errors="replace")
                has_enc_err = True
            values.append(decoded_str)
            val_off += tlen
        else:
            values.append(None)

    return DecodedRecord(
        values=values,
        serial_types=serial_types,
        header_length=hdr_len,
        has_encoding_errors=has_enc_err,
    )
