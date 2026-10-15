"""
In-memory read-only SQLite database image reader.

Provides zero-disk-write, boundary-checked page extraction and metadata inspection
conforming to Rules R4 and R12.
"""

import struct
from typing import Optional

from forensic.sqlite.constants import (
    HEADER_OFFSET_CHANGE_COUNTER,
    HEADER_OFFSET_FREELIST_COUNT,
    HEADER_OFFSET_FREELIST_TRUNK,
    HEADER_OFFSET_MAGIC,
    HEADER_OFFSET_PAGE_COUNT,
    HEADER_OFFSET_PAGE_SIZE,
    HEADER_OFFSET_READ_VERSION,
    HEADER_OFFSET_RESERVED,
    HEADER_OFFSET_TEXT_ENCODING,
    HEADER_OFFSET_VERSION_VALID,
    HEADER_OFFSET_WRITE_VERSION,
    SQLITE_HEADER_SIZE,
    SQLITE_HEADER_STRING,
    TEXT_ENCODING_UTF8,
    TEXT_ENCODING_UTF16BE,
    TEXT_ENCODING_UTF16LE,
)
from forensic.sqlite.exceptions import CorruptDatabase


class SQLiteImage:
    """
    Read-only in-memory wrapper around an SQLite database byte image.

    Guarantees:
    - Never writes to disk (R4).
    - Validates 100-byte header format, page size powers of 2, and boundary constraints (R12).
    - Exposes pages as zero-copy memoryviews.
    """

    def __init__(self, data: bytes):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("SQLiteImage data must be bytes, bytearray, or memoryview")

        self._mv = memoryview(data)
        if len(self._mv) < SQLITE_HEADER_SIZE:
            raise CorruptDatabase(
                f"File too small for SQLite header ({len(self._mv)} < 100 bytes)",
                offset=0,
            )

        # Validate magic
        if bytes(self._mv[:16]) != SQLITE_HEADER_STRING:
            raise CorruptDatabase("Invalid SQLite magic header string", offset=0)

        # Page size: 2 bytes big-endian at offset 16. Value 1 means 65536.
        raw_page_size = struct.unpack_from(">H", self._mv, HEADER_OFFSET_PAGE_SIZE)[0]
        if raw_page_size == 1:
            self.page_size = 65536
        else:
            self.page_size = raw_page_size

        # Valid page sizes: 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536
        if self.page_size < 512 or self.page_size > 65536 or (self.page_size & (self.page_size - 1)) != 0:
            raise CorruptDatabase(f"Invalid SQLite page size: {self.page_size}", offset=HEADER_OFFSET_PAGE_SIZE)

        # Reserved bytes per page (offset 20)
        self.reserved = self._mv[HEADER_OFFSET_RESERVED]
        if self.reserved > self.page_size - 480:
            raise CorruptDatabase(f"Unusable page size: reserved bytes ({self.reserved}) too large", offset=HEADER_OFFSET_RESERVED)

        self.usable_page_size = self.page_size - self.reserved

        # Write & Read versions (1=legacy, 2=WAL)
        self.write_version = self._mv[HEADER_OFFSET_WRITE_VERSION]
        self.read_version = self._mv[HEADER_OFFSET_READ_VERSION]

        # File change counter & version valid for
        self.change_counter = struct.unpack_from(">I", self._mv, HEADER_OFFSET_CHANGE_COUNTER)[0]
        self.version_valid_for = struct.unpack_from(">I", self._mv, HEADER_OFFSET_VERSION_VALID)[0]

        # In-header page count (offset 28)
        self.header_page_count = struct.unpack_from(">I", self._mv, HEADER_OFFSET_PAGE_COUNT)[0]

        # Physical page count based on buffer length
        physical_pages = len(self._mv) // self.page_size
        if self.header_page_count > 0 and self.change_counter == self.version_valid_for:
            self.page_count = self.header_page_count
        else:
            self.page_count = physical_pages

        # Freelist trunk page & count (offsets 32, 36)
        self.freelist_trunk = struct.unpack_from(">I", self._mv, HEADER_OFFSET_FREELIST_TRUNK)[0]
        self.freelist_count = struct.unpack_from(">I", self._mv, HEADER_OFFSET_FREELIST_COUNT)[0]

        # Text encoding (offset 56: 1=UTF-8, 2=UTF-16LE, 3=UTF-16BE)
        self.text_encoding = struct.unpack_from(">I", self._mv, HEADER_OFFSET_TEXT_ENCODING)[0]
        if self.text_encoding not in (TEXT_ENCODING_UTF8, TEXT_ENCODING_UTF16LE, TEXT_ENCODING_UTF16BE):
            # Default to UTF-8 if corrupt/unrecognized
            self.text_encoding = TEXT_ENCODING_UTF8

    @property
    def data(self) -> memoryview:
        """Raw memoryview of the complete database buffer."""
        return self._mv

    def get_page(self, page_no: int) -> memoryview:
        """
        Get zero-copy memoryview of 1-based page_no.

        Args:
            page_no: 1-indexed page number (1 <= page_no <= page_count).

        Returns:
            memoryview of length self.page_size.

        Raises:
            CorruptDatabase: If page_no is out of bounds.
        """
        if page_no < 1:
            raise CorruptDatabase(f"Invalid page number {page_no} (pages are 1-indexed)", page_number=page_no)

        start = (page_no - 1) * self.page_size
        end = start + self.page_size

        if end > len(self._mv):
            raise CorruptDatabase(
                f"Page {page_no} extends beyond buffer bounds ({end} > {len(self._mv)})",
                page_number=page_no,
            )

        return self._mv[start:end]

    def get_page_bytes(self, page_no: int) -> bytes:
        """Convenience helper returning bytes for a page."""
        return bytes(self.get_page(page_no))
