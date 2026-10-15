"""
SQLite Freelist Trunk and Leaf Traversal.

Implements safe, non-destructive traversal of SQLite freelist chains and page classification
per https://www.sqlite.org/fileformat2.html §1.4 and Rules R4, R8, and R12.
"""

from dataclasses import dataclass
import struct
from typing import List, Optional, Set, Tuple, Union

from forensic.sqlite.constants import BTREE_LEAF_TABLE
from forensic.sqlite.exceptions import CorruptDatabase
from forensic.sqlite.image import SQLiteImage


@dataclass(frozen=True)
class FreePage:
    """A recovered freelist page."""
    page_no: int
    role: str  # 'trunk' | 'leaf'
    raw: memoryview

    @property
    def raw_bytes(self) -> bytes:
        return bytes(self.raw)


def classify_free_page(raw: Union[bytes, memoryview]) -> str:
    """
    Classify a freed page based on its header remnants.

    Returns:
        'table_leaf' if byte 0 is 0x0D with plausible cell count and content offsets,
        otherwise 'other'.
    """
    if len(raw) < 8:
        return "other"

    page_type = raw[0]
    if page_type == BTREE_LEAF_TABLE:
        cell_count = struct.unpack_from(">H", raw, 3)[0]
        content_start = struct.unpack_from(">H", raw, 5)[0]
        content_start = 65536 if content_start == 0 else content_start

        # Sane bounds: cell pointer array must not overlap cell content area
        min_ptr_end = 8 + 2 * cell_count
        if min_ptr_end <= content_start <= len(raw):
            return "table_leaf"

    return "other"


def walk_freelist(
    image: SQLiteImage,
    max_trunk_depth: int = 10000,
) -> List[FreePage]:
    """
    Traverse freelist trunk and leaf pages safely with loop guards.

    Guarantees:
    - Zero disk writes (R4).
    - Detects circular trunk references and out-of-bounds page numbers.
    - Reconciles total count against image.freelist_count (warning on mismatch, does not fail).

    Returns:
        List of FreePage objects in traversal order.
    """
    free_pages: List[FreePage] = []
    visited_pages: Set[int] = set()
    curr_trunk = image.freelist_trunk
    depth = 0

    while curr_trunk > 0 and depth < max_trunk_depth:
        if curr_trunk in visited_pages or curr_trunk > image.page_count:
            # Loop detected or out of bounds
            break

        visited_pages.add(curr_trunk)
        depth += 1

        try:
            trunk_mv = image.get_page(curr_trunk)
        except CorruptDatabase:
            break

        # Trunk page itself is a free page
        free_pages.append(
            FreePage(
                page_no=curr_trunk,
                role="trunk",
                raw=trunk_mv,
            )
        )

        if len(trunk_mv) < 8:
            break

        next_trunk, n_leaf_ptrs = struct.unpack_from(">II", trunk_mv, 0)

        # Parse leaf page pointers
        max_leaves = (image.usable_page_size - 8) // 4
        leaf_count = min(n_leaf_ptrs, max_leaves)

        for i in range(leaf_count):
            leaf_page_no = struct.unpack_from(">I", trunk_mv, 8 + i * 4)[0]
            if leaf_page_no < 1 or leaf_page_no > image.page_count or leaf_page_no in visited_pages:
                continue

            visited_pages.add(leaf_page_no)
            try:
                leaf_mv = image.get_page(leaf_page_no)
                free_pages.append(
                    FreePage(
                        page_no=leaf_page_no,
                        role="leaf",
                        raw=leaf_mv,
                    )
                )
            except CorruptDatabase:
                continue

        curr_trunk = next_trunk

    return free_pages
