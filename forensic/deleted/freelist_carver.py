"""
SQLite Freelist trunk traversal and leaf-page record carver.
Recovers unallocated pages freed by deletes or vacuum operations without modifying the database.
"""

import hashlib
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from forensic.deleted.sqlite_record import find_candidate_records


SQLITE_HEADER_STRING = b"SQLite format 3\x00"


@dataclass(frozen=True)
class SqliteDbHeader:
    page_size: int
    page_count: int
    freelist_trunk_page: int
    total_freelist_pages: int


@dataclass
class FreelistPage:
    page_number: int
    byte_offset: int
    is_trunk: bool
    data: bytes
    sha256: str


@dataclass
class FreelistCarvedItem:
    page_number: int
    byte_offset: int
    relative_offset: int
    raw_bytes: bytes
    columns: List[Dict]
    values: List
    sha256: str


class FreelistCarver:
    """Traverses SQLite freelist trunk/leaf chains and carves records from unallocated space."""

    def __init__(self, db_bytes: bytes):
        self.db_bytes = db_bytes
        self.header: Optional[SqliteDbHeader] = None
        self.freelist_pages: List[FreelistPage] = []
        self.carved_records: List[FreelistCarvedItem] = []
        self.diagnostics: List[str] = []

    def parse_header(self) -> bool:
        """Parse SQLite database header (first 100 bytes)."""
        if len(self.db_bytes) < 100:
            self.diagnostics.append(f"Database too small ({len(self.db_bytes)} bytes < 100)")
            return False

        if not self.db_bytes.startswith(SQLITE_HEADER_STRING):
            self.diagnostics.append("Invalid SQLite magic header string")
            return False

        # Page size: 2 bytes at offset 16
        raw_page_size = struct.unpack(">H", self.db_bytes[16:18])[0]
        page_size = 65536 if raw_page_size == 1 else raw_page_size
        if page_size < 512 or (page_size & (page_size - 1)) != 0:
            self.diagnostics.append(f"Invalid page size: {page_size}")
            return False

        page_count = struct.unpack(">I", self.db_bytes[28:32])[0]
        freelist_trunk = struct.unpack(">I", self.db_bytes[32:36])[0]
        total_freelist = struct.unpack(">I", self.db_bytes[36:40])[0]

        self.header = SqliteDbHeader(
            page_size=page_size,
            page_count=page_count,
            freelist_trunk_page=freelist_trunk,
            total_freelist_pages=total_freelist,
        )
        return True

    def traverse_freelist(self) -> List[FreelistPage]:
        """Walk the freelist trunk pages and collect all leaf pages safely."""
        if not self.header and not self.parse_header():
            return []

        if not self.header or self.header.freelist_trunk_page == 0:
            return []

        page_size = self.header.page_size
        visited_pages: Set[int] = set()
        curr_trunk = self.header.freelist_trunk_page

        while curr_trunk > 0:
            if curr_trunk in visited_pages:
                self.diagnostics.append(f"Circular freelist trunk reference at page {curr_trunk}")
                break
            visited_pages.add(curr_trunk)

            trunk_offset = (curr_trunk - 1) * page_size
            if trunk_offset + page_size > len(self.db_bytes):
                self.diagnostics.append(f"Freelist trunk page {curr_trunk} out of file bounds")
                break

            trunk_data = self.db_bytes[trunk_offset : trunk_offset + page_size]
            next_trunk, leaf_count = struct.unpack(">II", trunk_data[:8])

            trunk_page_obj = FreelistPage(
                page_number=curr_trunk,
                byte_offset=trunk_offset,
                is_trunk=True,
                data=trunk_data,
                sha256=hashlib.sha256(trunk_data).hexdigest(),
            )
            self.freelist_pages.append(trunk_page_obj)

            # Extract leaf page numbers
            # Max leaf pointers that fit on a trunk page
            max_leaves = (page_size - 8) // 4
            effective_leaf_count = min(leaf_count, max_leaves)

            for i in range(effective_leaf_count):
                leaf_ptr_offset = 8 + (i * 4)
                leaf_page_num = struct.unpack(">I", trunk_data[leaf_ptr_offset : leaf_ptr_offset + 4])[0]
                if leaf_page_num == 0 or leaf_page_num in visited_pages:
                    continue

                visited_pages.add(leaf_page_num)
                leaf_byte_offset = (leaf_page_num - 1) * page_size
                if leaf_byte_offset + page_size > len(self.db_bytes):
                    self.diagnostics.append(f"Leaf page {leaf_page_num} out of bounds")
                    continue

                leaf_data = self.db_bytes[leaf_byte_offset : leaf_byte_offset + page_size]
                leaf_obj = FreelistPage(
                    page_number=leaf_page_num,
                    byte_offset=leaf_byte_offset,
                    is_trunk=False,
                    data=leaf_data,
                    sha256=hashlib.sha256(leaf_data).hexdigest(),
                )
                self.freelist_pages.append(leaf_obj)

            curr_trunk = next_trunk

        return self.freelist_pages

    def carve_all_freelist_pages(self) -> List[FreelistCarvedItem]:
        """Carve candidate records from all discovered freelist trunk and leaf pages."""
        if not self.freelist_pages:
            self.traverse_freelist()

        for page in self.freelist_pages:
            # Skip page header for trunk pages
            scan_offset = 8 if page.is_trunk else 0
            page_content = page.data[scan_offset:]

            candidates = find_candidate_records(page_content, min_columns=2)
            for c in candidates:
                raw_bytes = c["raw_bytes"]
                exact_offset = page.byte_offset + scan_offset + c["offset"]
                carved = FreelistCarvedItem(
                    page_number=page.page_number,
                    byte_offset=exact_offset,
                    relative_offset=c["offset"],
                    raw_bytes=raw_bytes,
                    columns=c["columns"],
                    values=c["values"],
                    sha256=hashlib.sha256(raw_bytes).hexdigest(),
                )
                self.carved_records.append(carved)

        return self.carved_records
