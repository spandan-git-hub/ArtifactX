"""
MTProto Type Language (TL) Binary Deserialization Reader (spec B9.2).

Pure-Python, zero-disk, bounds-checked binary reader for Telegram TL blobs.
Follows master.md R4, R12 (hostile-input hardening), and R18.
"""

from __future__ import annotations

import struct
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class TLError(Exception):
    """Base exception for MTProto TL deserialization errors."""

    def __init__(self, message: str, offset: int = 0, constructor_id: Optional[int] = None):
        super().__init__(message)
        self.offset = offset
        self.constructor_id = constructor_id


class TLConstructorNotFoundError(TLError):
    """Raised when an unregistered constructor ID is encountered (triggers UNPARSED_BLOB)."""
    pass


class TLBoundsError(TLError):
    """Raised when a buffer read exceeds bounds."""
    pass


class TLRecursionLimitError(TLError):
    """Raised when nested object depth exceeds security threshold."""
    pass


# Constant Constructor IDs for primitives
CONSTRUCTOR_VECTOR = 0x1CB5C415
CONSTRUCTOR_BOOL_TRUE = 0x997275B5
CONSTRUCTOR_BOOL_FALSE = 0xBC799737

# Hostile-input caps (R12)
MAX_RECURSION_DEPTH = 32
MAX_VECTOR_ELEMENTS = 100000
MAX_BYTE_ARRAY_LENGTH = 32 * 1024 * 1024  # 32 MiB max for a single blob payload


class TLReader:
    """
    Bounds-checked memoryview reader for MTProto binary serialization.
    """

    def __init__(
        self,
        data: Union[bytes, bytearray, memoryview],
        registry: Optional[Dict[int, Callable[[TLReader], Any]]] = None,
    ):
        self.view = memoryview(data)
        self.pos = 0
        self.length = len(self.view)
        self.depth = 0
        self.registry = registry or {}

    def tell(self) -> int:
        """Return current byte offset in stream."""
        return self.pos

    def remaining(self) -> int:
        """Return remaining unread byte count."""
        return max(0, self.length - self.pos)

    def remaining_bytes(self) -> bytes:
        """Return all remaining bytes from current position."""
        if self.pos >= self.length:
            return b""
        return bytes(self.view[self.pos :])

    def seek(self, pos: int) -> None:
        """Seek to an absolute byte offset."""
        if pos < 0 or pos > self.length:
            raise TLBoundsError(f"Seek offset {pos} out of range [0, {self.length}]", offset=pos)
        self.pos = pos

    def read(self, n: int) -> bytes:
        """Read n raw bytes from stream."""
        if n < 0:
            raise TLBoundsError(f"Negative read count: {n}", offset=self.pos)
        if self.pos + n > self.length:
            raise TLBoundsError(
                f"Read of {n} bytes exceeds buffer end ({self.pos} + {n} > {self.length})",
                offset=self.pos,
            )
        data = bytes(self.view[self.pos : self.pos + n])
        self.pos += n
        return data

    def read_byte(self) -> int:
        """Read 1 unsigned byte."""
        if self.pos + 1 > self.length:
            raise TLBoundsError("Unexpected EOF reading byte", offset=self.pos)
        val = self.view[self.pos]
        self.pos += 1
        return val

    def read_int(self, signed: bool = True) -> int:
        """Read 32-bit little-endian integer."""
        if self.pos + 4 > self.length:
            raise TLBoundsError("Unexpected EOF reading 32-bit int", offset=self.pos)
        fmt = "<i" if signed else "<I"
        (val,) = struct.unpack_from(fmt, self.view, self.pos)
        self.pos += 4
        return val

    def read_long(self, signed: bool = True) -> int:
        """Read 64-bit little-endian integer."""
        if self.pos + 8 > self.length:
            raise TLBoundsError("Unexpected EOF reading 64-bit long", offset=self.pos)
        fmt = "<q" if signed else "<Q"
        (val,) = struct.unpack_from(fmt, self.view, self.pos)
        self.pos += 8
        return val

    def read_double(self) -> float:
        """Read 64-bit IEEE 754 little-endian double."""
        if self.pos + 8 > self.length:
            raise TLBoundsError("Unexpected EOF reading double", offset=self.pos)
        (val,) = struct.unpack_from("<d", self.view, self.pos)
        self.pos += 8
        return val

    def read_bytes(self) -> bytes:
        """
        Read Telegram length-prefixed bytes array with 4-byte padding alignment.

        If first byte < 254: 1-byte length prefix.
        If first byte == 254: 3-byte little-endian length prefix.
        Total length including prefix is padded with 0-3 bytes to multiple of 4.
        """
        start_pos = self.pos
        first_byte = self.read_byte()
        if first_byte == 254:
            if self.pos + 3 > self.length:
                raise TLBoundsError("Unexpected EOF reading 24-bit bytes length", offset=self.pos)
            b0 = self.read_byte()
            b1 = self.read_byte()
            b2 = self.read_byte()
            byte_len = b0 | (b1 << 8) | (b2 << 16)
            padding = byte_len % 4
        else:
            byte_len = first_byte
            padding = (byte_len + 1) % 4

        if byte_len > MAX_BYTE_ARRAY_LENGTH:
            raise TLBoundsError(
                f"Byte array length {byte_len} exceeds safety ceiling {MAX_BYTE_ARRAY_LENGTH}",
                offset=start_pos,
            )

        if self.pos + byte_len > self.length:
            raise TLBoundsError(
                f"Byte array payload of {byte_len} bytes exceeds buffer end ({self.pos} + {byte_len} > {self.length})",
                offset=self.pos,
            )

        data = self.read(byte_len)

        if padding > 0:
            pad_len = 4 - padding
            if self.pos + pad_len > self.length:
                raise TLBoundsError(
                    f"Padding of {pad_len} bytes exceeds buffer end", offset=self.pos
                )
            self.pos += pad_len

        return data

    def read_string(self) -> str:
        """Read Telegram length-prefixed UTF-8 string."""
        raw_bytes = self.read_bytes()
        return raw_bytes.decode("utf-8", errors="replace")

    def read_date(self) -> int:
        """Read Unix epoch timestamp in seconds (int32)."""
        return self.read_int(signed=True)

    def read_object(self) -> Any:
        """
        Read serialized MTProto object by constructor ID dispatch.

        Handles:
        - boolTrue (0x997275b5) -> True
        - boolFalse (0xbc799737) -> False
        - Vector (0x1cb5c415) -> List[Any]
        - Registered constructor IDs -> Parsed dataclass
        - Unknown constructor IDs -> raises TLConstructorNotFoundError
        """
        if self.depth >= MAX_RECURSION_DEPTH:
            raise TLRecursionLimitError(
                f"Max recursion depth {MAX_RECURSION_DEPTH} exceeded", offset=self.pos
            )

        start_pos = self.pos
        if self.pos + 4 > self.length:
            raise TLBoundsError("Unexpected EOF reading constructor ID", offset=self.pos)

        constructor_id = self.read_int(signed=False)

        if constructor_id == CONSTRUCTOR_BOOL_TRUE:
            return True
        if constructor_id == CONSTRUCTOR_BOOL_FALSE:
            return False
        if constructor_id == CONSTRUCTOR_VECTOR:
            elem_count = self.read_int(signed=True)
            if elem_count < 0 or elem_count > MAX_VECTOR_ELEMENTS:
                raise TLBoundsError(
                    f"Vector element count {elem_count} outside valid bounds [0, {MAX_VECTOR_ELEMENTS}]",
                    offset=start_pos,
                )
            elements: List[Any] = []
            self.depth += 1
            try:
                for _ in range(elem_count):
                    elements.append(self.read_object())
            finally:
                self.depth -= 1
            return elements

        parser_fn = self.registry.get(constructor_id)
        if parser_fn is None:
            raise TLConstructorNotFoundError(
                f"Unknown TL constructor ID 0x{constructor_id:08x} at offset {start_pos}",
                offset=start_pos,
                constructor_id=constructor_id,
            )

        self.depth += 1
        try:
            return parser_fn(self)
        finally:
            self.depth -= 1
