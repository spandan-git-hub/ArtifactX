"""
SQLite B-tree page parser and cell/freeblock slack space carver.
Recovers deleted records and residual fragments lurking between cell pointers, freeblocks, and slack areas.
"""

import hashlib
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from forensic.deleted.sqlite_record import find_candidate_records


BTREE_LEAF_TABLE = 0x0D
BTREE_INTERIOR_TABLE = 0x05
BTREE_LEAF_INDEX = 0x0A
BTREE_INTERIOR_INDEX = 0x02


@dataclass(frozen=True)
class BtreeHeader:
    page_type: int
    first_freeblock: int
    cell_count: int
    cell_content_start: int
    fragmented_free_bytes: int
    right_child: Optional[int]
    header_offset: int
    header_size: int


@dataclass
class SlackSpan:
    page_number: int
    span_type: str  # 'unallocated_gap', 'freeblock', 'fragmented'
    page_offset: int
    absolute_byte_offset: int
    length: int
    data: bytes
    sha256: str


@dataclass
class SlackCarvedRecord:
    page_number: int
    absolute_byte_offset: int
    span_type: str
    raw_bytes: bytes
    columns: List[Dict]
    values: List
    sha256: str


class SlackCarver:
    """Scans B-tree pages for unallocated cell pointer gap, freeblocks, and cell slack."""

    def __init__(self, db_bytes: bytes, page_size: int = 4096):
        self.db_bytes = db_bytes
        self.page_size = page_size
        self.slack_spans: List[SlackSpan] = []
        self.carved_records: List[SlackCarvedRecord] = []
        self.diagnostics: List[str] = []

    def parse_page_header(self, page_data: bytes, page_num: int) -> Optional[BtreeHeader]:
        """Parse B-tree header for a specific page."""
        hdr_offset = 100 if page_num == 1 else 0
        if len(page_data) < hdr_offset + 8:
            return None

        page_type = page_data[hdr_offset]
        if page_type not in (
            BTREE_LEAF_TABLE,
            BTREE_INTERIOR_TABLE,
            BTREE_LEAF_INDEX,
            BTREE_INTERIOR_INDEX,
        ):
            return None

        first_freeblock, cell_count, raw_content_start, frag_free = struct.unpack(
            ">HHHB", page_data[hdr_offset + 1 : hdr_offset + 8]
        )
        content_start = 65536 if raw_content_start == 0 else raw_content_start

        right_child = None
        hdr_size = 8
        if page_type in (BTREE_INTERIOR_TABLE, BTREE_INTERIOR_INDEX):
            if len(page_data) >= hdr_offset + 12:
                right_child = struct.unpack(">I", page_data[hdr_offset + 8 : hdr_offset + 12])[0]
                hdr_size = 12

        return BtreeHeader(
            page_type=page_type,
            first_freeblock=first_freeblock,
            cell_count=cell_count,
            cell_content_start=content_start,
            fragmented_free_bytes=frag_free,
            right_child=right_child,
            header_offset=hdr_offset,
            header_size=hdr_size,
        )

    def extract_page_slack(self, page_data: bytes, page_num: int) -> List[SlackSpan]:
        """Extract all slack and unallocated spans from a single B-tree page."""
        header = self.parse_page_header(page_data, page_num)
        if not header:
            return []

        spans: List[SlackSpan] = []
        base_file_offset = (page_num - 1) * self.page_size

        # 1. Unallocated space between cell pointer array and cell content start
        cell_ptr_start = header.header_offset + header.header_size
        cell_ptr_end = cell_ptr_start + (header.cell_count * 2)

        content_start = min(header.cell_content_start, len(page_data))
        if cell_ptr_end < content_start:
            gap_len = content_start - cell_ptr_end
            if gap_len >= 8:  # Worth scanning if at least 8 bytes
                gap_data = page_data[cell_ptr_end:content_start]
                spans.append(
                    SlackSpan(
                        page_number=page_num,
                        span_type="unallocated_gap",
                        page_offset=cell_ptr_end,
                        absolute_byte_offset=base_file_offset + cell_ptr_end,
                        length=gap_len,
                        data=gap_data,
                        sha256=hashlib.sha256(gap_data).hexdigest(),
                    )
                )

        # 2. Walk freeblocks
        curr_fb = header.first_freeblock
        visited_fb = set()
        while curr_fb > 0:
            if curr_fb in visited_fb or curr_fb + 4 > len(page_data):
                break
            visited_fb.add(curr_fb)

            next_fb, fb_size = struct.unpack(">HH", page_data[curr_fb : curr_fb + 4])
            if fb_size < 4 or curr_fb + fb_size > len(page_data):
                break

            # The content of the freeblock (excluding header)
            fb_data = page_data[curr_fb + 4 : curr_fb + fb_size]
            if len(fb_data) >= 8:
                spans.append(
                    SlackSpan(
                        page_number=page_num,
                        span_type="freeblock",
                        page_offset=curr_fb + 4,
                        absolute_byte_offset=base_file_offset + curr_fb + 4,
                        length=len(fb_data),
                        data=fb_data,
                        sha256=hashlib.sha256(fb_data).hexdigest(),
                    )
                )

            curr_fb = next_fb

        return spans

    def scan_all_pages(self) -> List[SlackCarvedRecord]:
        """Scan all pages in the database for slack space and carve candidate records."""
        total_pages = len(self.db_bytes) // self.page_size
        for p in range(1, total_pages + 1):
            page_offset = (p - 1) * self.page_size
            page_data = self.db_bytes[page_offset : page_offset + self.page_size]
            spans = self.extract_page_slack(page_data, p)
            self.slack_spans.extend(spans)

            for span in spans:
                candidates = find_candidate_records(span.data, min_columns=2)
                for c in candidates:
                    rec_bytes = c["raw_bytes"]
                    exact_offset = span.absolute_byte_offset + c["offset"]
                    self.carved_records.append(
                        SlackCarvedRecord(
                            page_number=p,
                            absolute_byte_offset=exact_offset,
                            span_type=span.span_type,
                            raw_bytes=rec_bytes,
                            columns=c["columns"],
                            values=c["values"],
                            sha256=hashlib.sha256(rec_bytes).hexdigest(),
                        )
                    )

        return self.carved_records
