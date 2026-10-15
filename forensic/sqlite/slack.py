"""
SQLite Intra-Page Slack and Freeblock Space Traversal.

Scans live leaf-table pages for unallocated cell pointer gaps, freeblocks,
and slack space per https://www.sqlite.org/fileformat2.html §1.3 and Rules R4, R8, and R12.
"""

from dataclasses import dataclass
import struct
from typing import List, Optional, Set, Union

from forensic.sqlite.constants import (
    BTREE_LEAF_TABLE,
    PAGE_HEADER_SIZE_LEAF,
    PAGE_OFFSET_CELL_COUNT,
    PAGE_OFFSET_CONTENT_START,
    PAGE_OFFSET_FIRST_FREEBLOCK,
    PAGE_OFFSET_FRAG_BYTES,
    PAGE_OFFSET_TYPE,
)
from forensic.sqlite.exceptions import CorruptPage
from forensic.sqlite.image import SQLiteImage


@dataclass(frozen=True)
class Span:
    """An unallocated byte span within a database page."""
    page_no: int
    offset: int      # Byte offset relative to page start
    length: int      # Length in bytes
    kind: str        # 'freeblock' | 'unallocated_gap'
    fragmented_free_bytes: int = 0


def walk_page_spans(image: SQLiteImage, page_no: int) -> List[Span]:
    """
    Extract unallocated spans (freeblock chain + cell pointer gap) from a leaf-table page.

    Args:
        image: SQLiteImage
        page_no: 1-indexed page number

    Returns:
        List of Span objects.
    """
    spans: List[Span] = []
    page_mv = image.get_page(page_no)
    hdr_offset = 100 if page_no == 1 else 0

    if len(page_mv) < hdr_offset + PAGE_HEADER_SIZE_LEAF:
        return spans

    page_type = page_mv[hdr_offset + PAGE_OFFSET_TYPE]
    if page_type != BTREE_LEAF_TABLE:
        return spans

    first_freeblock = struct.unpack_from(">H", page_mv, hdr_offset + PAGE_OFFSET_FIRST_FREEBLOCK)[0]
    cell_count = struct.unpack_from(">H", page_mv, hdr_offset + PAGE_OFFSET_CELL_COUNT)[0]
    raw_content_start = struct.unpack_from(">H", page_mv, hdr_offset + PAGE_OFFSET_CONTENT_START)[0]
    frag_bytes = page_mv[hdr_offset + PAGE_OFFSET_FRAG_BYTES]

    content_start = 65536 if raw_content_start == 0 else raw_content_start
    usable = image.usable_page_size

    # (a) Unallocated gap between end of cell pointer array and start of cell content area
    ptr_end = hdr_offset + PAGE_HEADER_SIZE_LEAF + 2 * cell_count
    if content_start > ptr_end and ptr_end <= usable:
        gap_len = min(content_start, usable) - ptr_end
        if gap_len > 0:
            spans.append(
                Span(
                    page_no=page_no,
                    offset=ptr_end,
                    length=gap_len,
                    kind="unallocated_gap",
                    fragmented_free_bytes=frag_bytes,
                )
            )

    # (b) Walk the freeblock chain
    visited_offsets: Set[int] = set()
    curr_freeblock = first_freeblock

    while curr_freeblock > 0:
        if curr_freeblock in visited_offsets or curr_freeblock < ptr_end or curr_freeblock >= usable:
            # Corrupt chain or loop
            break

        visited_offsets.add(curr_freeblock)
        if curr_freeblock + 4 > usable:
            break

        next_freeblock, fb_size = struct.unpack_from(">HH", page_mv, curr_freeblock)

        # Freeblock size must be at least 4 bytes and within page
        if fb_size >= 4 and curr_freeblock + fb_size <= usable:
            spans.append(
                Span(
                    page_no=page_no,
                    offset=curr_freeblock,
                    length=fb_size,
                    kind="freeblock",
                    fragmented_free_bytes=frag_bytes,
                )
            )
        else:
            break

        # Freeblocks must be chained in ascending offset order
        if next_freeblock > 0 and next_freeblock <= curr_freeblock:
            break

        curr_freeblock = next_freeblock

    return spans


def get_span_bytes(image: SQLiteImage, span: Span) -> bytes:
    """Read the raw bytes for a given page span."""
    page_mv = image.get_page(span.page_no)
    return bytes(page_mv[span.offset : span.offset + span.length])
