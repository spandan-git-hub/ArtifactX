"""
SQLite record, serial type, and varint decoders with strict boundary enforcement.
Forensic-grade parsing for physical cell and slack space carving.
"""

import struct
from typing import Any, Dict, List, Optional, Tuple


def decode_varint(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Decode a variable-length integer (varint) from SQLite raw bytes.
    SQLite varints are 1 to 9 bytes long.
    Bytes 1 to 8: high bit is continuation flag, low 7 bits are payload.
    Byte 9 (if reached): all 8 bits are used.

    Args:
        data: Byte buffer
        offset: Starting byte position

    Returns:
        (value, bytes_consumed)
    Raises:
        ValueError: If buffer is truncated or invalid.
    """
    if offset >= len(data):
        raise ValueError(f"Varint decode offset {offset} out of bounds (len={len(data)})")

    val = 0
    for i in range(8):
        pos = offset + i
        if pos >= len(data):
            raise ValueError(f"Truncated varint at index {pos}")
        b = data[pos]
        val = (val << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            return val, i + 1

    # 9th byte uses all 8 bits
    pos = offset + 8
    if pos >= len(data):
        raise ValueError(f"Truncated 9-byte varint at index {pos}")
    val = (val << 8) | data[pos]
    return val, 9


def encode_varint(val: int) -> bytes:
    """Encode an integer as an SQLite varint (for testing and synthetic fixture creation)."""
    if val < 0:
        val = val & 0xFFFFFFFFFFFFFFFF

    if val <= 0x7F:
        return bytes([val])

    buf = []
    # Up to 8 groups of 7 bits
    temp = val
    # If it needs 9 bytes
    if temp > 0x00FFFFFFFFFFFFFF:
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


def decode_serial_type(serial_type: int) -> Tuple[str, int]:
    """
    Translate SQLite serial type code to data category and byte length.

    Returns:
        (data_type, byte_length)
    """
    if serial_type == 0:
        return "NULL", 0
    elif serial_type == 1:
        return "INT8", 1
    elif serial_type == 2:
        return "INT16", 2
    elif serial_type == 3:
        return "INT24", 3
    elif serial_type == 4:
        return "INT32", 4
    elif serial_type == 5:
        return "INT48", 6
    elif serial_type == 6:
        return "INT64", 8
    elif serial_type == 7:
        return "FLOAT64", 8
    elif serial_type == 8:
        return "ZERO", 0
    elif serial_type == 9:
        return "ONE", 0
    elif serial_type in (10, 11):
        return "RESERVED", 0
    elif serial_type >= 12:
        if serial_type % 2 == 0:
            # BLOB of length (N - 12) / 2
            length = (serial_type - 12) // 2
            return "BLOB", length
        else:
            # TEXT in database encoding of length (N - 13) / 2
            length = (serial_type - 13) // 2
            return "TEXT", length
    return "UNKNOWN", 0


def parse_record_header(payload: bytes, offset: int = 0) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Parse the SQLite record header.
    Format:
      [header_size (varint)][serial_type_1 (varint)]...[serial_type_N (varint)]
    Followed immediately by column bodies.

    Returns:
        (columns_info, header_size, body_start_offset)
    """
    total_len = len(payload)
    if offset >= total_len:
        raise ValueError(f"Offset {offset} beyond payload length {total_len}")

    header_size, varint_len = decode_varint(payload, offset)
    if header_size < varint_len or offset + header_size > total_len:
        raise ValueError(
            f"Invalid record header size: {header_size} at offset {offset} (total payload {total_len})"
        )

    columns = []
    curr_offset = offset + varint_len
    header_end = offset + header_size

    col_idx = 0
    while curr_offset < header_end:
        serial_type, st_len = decode_varint(payload, curr_offset)
        curr_offset += st_len
        col_type, byte_len = decode_serial_type(serial_type)
        columns.append({
            "index": col_idx,
            "serial_type": serial_type,
            "type": col_type,
            "length": byte_len,
        })
        col_idx += 1

    return columns, header_size, header_end


def unpack_record(payload: bytes, columns: List[Dict[str, Any]], body_start: int) -> List[Any]:
    """
    Unpack record column values using column metadata and enforce boundary checks.

    Returns:
        List of unpacked Python objects (str, bytes, int, float, None).
    """
    values = []
    curr_offset = body_start
    total_len = len(payload)

    for col in columns:
        col_type = col["type"]
        length = col["length"]

        if curr_offset + length > total_len:
            # Truncated record
            values.append(None)
            curr_offset += length
            continue

        raw_slice = payload[curr_offset : curr_offset + length]
        curr_offset += length

        if col_type == "NULL":
            values.append(None)
        elif col_type == "ZERO":
            values.append(0)
        elif col_type == "ONE":
            values.append(1)
        elif col_type == "INT8":
            val = struct.unpack(">b", raw_slice)[0]
            values.append(val)
        elif col_type == "INT16":
            val = struct.unpack(">h", raw_slice)[0]
            values.append(val)
        elif col_type == "INT24":
            # 3-byte signed big-endian integer
            b0, b1, b2 = raw_slice
            val = (b0 << 16) | (b1 << 8) | b2
            if val & 0x800000:
                val -= 0x1000000
            values.append(val)
        elif col_type == "INT32":
            val = struct.unpack(">i", raw_slice)[0]
            values.append(val)
        elif col_type == "INT48":
            # 6-byte signed big-endian integer
            val = int.from_bytes(raw_slice, byteorder="big", signed=True)
            values.append(val)
        elif col_type == "INT64":
            val = struct.unpack(">q", raw_slice)[0]
            values.append(val)
        elif col_type == "FLOAT64":
            val = struct.unpack(">d", raw_slice)[0]
            values.append(val)
        elif col_type == "TEXT":
            try:
                values.append(raw_slice.decode("utf-8").replace("\x00", ""))
            except UnicodeDecodeError:
                values.append(raw_slice.decode("latin-1", errors="replace").replace("\x00", ""))
        elif col_type == "BLOB":
            values.append(raw_slice)
        else:
            values.append(raw_slice)

    return values


def find_candidate_records(
    data: bytes, min_columns: int = 2, max_columns: int = 60
) -> List[Dict[str, Any]]:
    """
    Conservatively scan a byte chunk (e.g. from freelist page or slack space)
    for candidate SQLite record headers.

    Returns:
        List of dicts: {'offset': int, 'columns': list, 'values': list, 'raw_bytes': bytes}
    """
    candidates = []
    data_len = len(data)

    # A valid header must have at least 2 bytes (header_size varint + at least 1 column varint)
    for offset in range(data_len - 3):
        try:
            header_size, varint_len = decode_varint(data, offset)
            # Basic sanity checks for record header
            if header_size <= varint_len or header_size > 200:
                continue
            if offset + header_size > data_len:
                continue

            columns, h_size, body_start = parse_record_header(data, offset)
            if not (min_columns <= len(columns) <= max_columns):
                continue

            # Calculate expected body length
            total_body_len = sum(c["length"] for c in columns)
            if body_start + total_body_len > data_len:
                continue

            # Unpack values
            values = unpack_record(data, columns, body_start)

            # Heuristic check: at least one column should contain non-trivial data
            has_substance = any(
                isinstance(v, str) and len(v.strip()) > 0
                or isinstance(v, (int, float)) and v != 0
                for v in values
            )
            if not has_substance:
                continue

            raw_record = data[offset : body_start + total_body_len]
            candidates.append({
                "offset": offset,
                "header_size": header_size,
                "columns": columns,
                "values": values,
                "raw_bytes": raw_record,
            })
        except Exception:
            continue

    return candidates
