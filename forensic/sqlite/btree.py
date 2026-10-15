"""
SQLite B-tree traversal and schema introspection.

Safely traverses Table B-tree pages (interior 0x05, leaf 0x0D), reassembles overflow
payload chains, and parses sqlite_master without executing SQL per Rules R4 and R12.
"""

from dataclasses import dataclass
import re
import struct
from typing import Dict, Iterator, List, Optional, Set, Tuple

from forensic.sqlite.constants import (
    BTREE_INTERIOR_INDEX,
    BTREE_INTERIOR_TABLE,
    BTREE_LEAF_INDEX,
    BTREE_LEAF_TABLE,
    PAGE_HEADER_SIZE_INTERIOR,
    PAGE_HEADER_SIZE_LEAF,
    PAGE_OFFSET_CELL_COUNT,
    PAGE_OFFSET_CONTENT_START,
    PAGE_OFFSET_FIRST_FREEBLOCK,
    PAGE_OFFSET_FRAG_BYTES,
    PAGE_OFFSET_RIGHT_CHILD,
    PAGE_OFFSET_TYPE,
)
from forensic.sqlite.exceptions import CorruptDatabase, CorruptPage
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.record import (
    compute_payload_spill,
    decode_record,
    decode_varint,
)


@dataclass(frozen=True)
class Cell:
    """A decoded Leaf Table B-tree cell."""
    page_no: int
    cell_offset: int
    rowid: int
    payload_bytes: bytes
    overflow_complete: bool


@dataclass(frozen=True)
class TableSchema:
    """Table metadata discovered by parsing sqlite_master."""
    name: str
    root_page: int
    sql: str
    columns: List[str]


def parse_create_table_columns(sql: str) -> List[str]:
    """
    Extract column names from a CREATE TABLE SQL statement without executing SQL.

    Handles quotes, brackets, data types, inline constraints, and multi-line formatting.
    """
    if not sql:
        return []

    # Find the parameter list inside the outermost parentheses
    start_paren = sql.find("(")
    end_paren = sql.rfind(")")
    if start_paren == -1 or end_paren == -1 or end_paren <= start_paren:
        return []

    body = sql[start_paren + 1 : end_paren].strip()

    # Split by comma at top-level nesting
    tokens: List[str] = []
    current_token: List[str] = []
    depth = 0
    in_quote: Optional[str] = None

    for char in body:
        if in_quote:
            current_token.append(char)
            if char == in_quote:
                in_quote = None
        elif char in ('"', "'", "`"):
            in_quote = char
            current_token.append(char)
        elif char == "[":
            in_quote = "]"
            current_token.append(char)
        elif char == "(":
            depth += 1
            current_token.append(char)
        elif char == ")":
            if depth > 0:
                depth -= 1
            current_token.append(char)
        elif char == "," and depth == 0:
            token_str = "".join(current_token).strip()
            if token_str:
                tokens.append(token_str)
            current_token = []
        else:
            current_token.append(char)

    last_str = "".join(current_token).strip()
    if last_str:
        tokens.append(last_str)

    # Filter out table-level constraints: PRIMARY KEY (...), FOREIGN KEY (...), UNIQUE (...), CHECK (...)
    constraint_keywords = (
        "constraint",
        "primary key",
        "foreign key",
        "unique",
        "check",
    )

    column_names: List[str] = []
    for col_def in tokens:
        col_clean = col_def.strip()
        lower_def = col_clean.lower()
        if any(lower_def.startswith(kw) for kw in constraint_keywords):
            continue

        # Extract first token (the column name)
        match = re.match(r'^("([^"]+)"|`([^`]+)`|\[([^\]]+)\]|\'([^\']+)\'|([a-zA-Z0-9_]+))', col_clean)
        if match:
            # Pick the matched group that is not None
            name = (
                match.group(2)
                or match.group(3)
                or match.group(4)
                or match.group(5)
                or match.group(6)
            )
            if name:
                column_names.append(name)

    return column_names


def _assemble_overflow(
    image: SQLiteImage,
    first_overflow_page: int,
    needed_bytes: int,
    visited_pages: Set[int],
    max_overflow_pages: int = 10000,
) -> Tuple[bytes, bool]:
    """
    Follow overflow page chain and assemble payload bytes.

    Returns:
        (assembled_bytes, is_complete)
    """
    chunks: List[bytes] = []
    curr_page_no = first_overflow_page
    remaining = needed_bytes
    pages_walked = 0
    usable = image.usable_page_size

    while curr_page_no > 0 and remaining > 0 and pages_walked < max_overflow_pages:
        if curr_page_no in visited_pages or curr_page_no > image.page_count:
            # Loop detected or out of bounds
            return b"".join(chunks), False

        visited_pages.add(curr_page_no)
        pages_walked += 1

        try:
            page_mv = image.get_page(curr_page_no)
        except CorruptDatabase:
            return b"".join(chunks), False

        # First 4 bytes: next page pointer
        next_page = struct.unpack_from(">I", page_mv, 0)[0]
        chunk_len = min(remaining, usable - 4)
        if chunk_len < 0:
            break

        chunk = bytes(page_mv[4 : 4 + chunk_len])
        chunks.append(chunk)
        remaining -= len(chunk)

        curr_page_no = next_page

    complete = (remaining == 0)
    return b"".join(chunks), complete


def iter_btree_leaf_cells(
    image: SQLiteImage,
    root_page: int,
    max_pages: int = 100000,
) -> Iterator[Cell]:
    """
    Iterate over all leaf cells in key order starting from root_page.

    Guarantees:
    - Zero disk writes (R4).
    - Traverses interior pages (0x05) to leaf pages (0x0D).
    - Assembles overflow payload chains safely.
    - Prevents infinite loops via visited set and page budgets (R12).
    - Raises CorruptPage / CorruptDatabase on malformed page structures.

    Yields:
        Cell(page_no, cell_offset, rowid, payload_bytes, overflow_complete)
    """
    visited_pages: Set[int] = set()
    pages_walked = 0

    # Stack for DFS traversal: (page_no, child_index)
    # Interior pages yield children in order: left_child_0, ..., left_child_N, right_child
    stack: List[Tuple[int, int]] = [(root_page, 0)]

    while stack:
        if pages_walked >= max_pages:
            raise CorruptDatabase(f"Page traversal budget exceeded ({max_pages} pages)", page_number=root_page)

        page_no, child_idx = stack.pop()
        hdr_offset = 100 if page_no == 1 else 0

        page_mv = image.get_page(page_no)
        if len(page_mv) < hdr_offset + PAGE_HEADER_SIZE_LEAF:
            raise CorruptPage(f"Page {page_no} truncated for b-tree header", page_number=page_no)

        page_type = page_mv[hdr_offset + PAGE_OFFSET_TYPE]

        if page_type == BTREE_LEAF_TABLE:
            if page_no in visited_pages:
                continue
            visited_pages.add(page_no)
            pages_walked += 1

            # Leaf page: parse cell pointer array and yield cells
            n_cells = struct.unpack_from(">H", page_mv, hdr_offset + PAGE_OFFSET_CELL_COUNT)[0]
            ptr_offset = hdr_offset + PAGE_HEADER_SIZE_LEAF

            if ptr_offset + 2 * n_cells > image.usable_page_size:
                raise CorruptPage(f"Cell pointer array exceeds usable page on page {page_no}", page_number=page_no)

            for i in range(n_cells):
                cell_off = struct.unpack_from(">H", page_mv, ptr_offset + 2 * i)[0]
                if cell_off < ptr_offset + 2 * n_cells or cell_off >= image.usable_page_size:
                    raise CorruptPage(f"Cell offset {cell_off} out of bounds on page {page_no}", page_number=page_no, offset=cell_off)

                # Decode payload length and rowid varints
                payload_len, c1 = decode_varint(page_mv, cell_off)
                rowid, c2 = decode_varint(page_mv, cell_off + c1)
                if rowid >= 0x8000000000000000:
                    rowid -= 0x10000000000000000

                local_len, has_overflow = compute_payload_spill(
                    usable_page_size=image.usable_page_size,
                    payload_len=payload_len,
                    is_table_leaf=True,
                )

                local_payload_start = cell_off + c1 + c2
                if local_payload_start + local_len > image.usable_page_size:
                    raise CorruptPage(f"Cell payload extends beyond page boundary on page {page_no}", page_number=page_no, offset=cell_off)

                local_bytes = bytes(page_mv[local_payload_start : local_payload_start + local_len])

                if has_overflow:
                    overflow_ptr_off = local_payload_start + local_len
                    if overflow_ptr_off + 4 > image.usable_page_size:
                        raise CorruptPage(f"Overflow pointer truncated on page {page_no}", page_number=page_no, offset=overflow_ptr_off)
                    first_overflow = struct.unpack_from(">I", page_mv, overflow_ptr_off)[0]

                    overflow_visited: Set[int] = set()
                    overflow_bytes, overflow_ok = _assemble_overflow(
                        image=image,
                        first_overflow_page=first_overflow,
                        needed_bytes=payload_len - local_len,
                        visited_pages=overflow_visited,
                    )
                    full_payload = local_bytes + overflow_bytes
                    complete = overflow_ok and len(full_payload) == payload_len
                else:
                    full_payload = local_bytes
                    complete = True

                yield Cell(
                    page_no=page_no,
                    cell_offset=cell_off,
                    rowid=rowid,
                    payload_bytes=full_payload,
                    overflow_complete=complete,
                )

        elif page_type == BTREE_INTERIOR_TABLE:
            if page_no not in visited_pages:
                visited_pages.add(page_no)
                pages_walked += 1

            n_cells = struct.unpack_from(">H", page_mv, hdr_offset + PAGE_OFFSET_CELL_COUNT)[0]
            right_child = struct.unpack_from(">I", page_mv, hdr_offset + PAGE_OFFSET_RIGHT_CHILD)[0]
            ptr_offset = hdr_offset + PAGE_HEADER_SIZE_INTERIOR

            if ptr_offset + 2 * n_cells > image.usable_page_size:
                raise CorruptPage(f"Interior cell pointer array exceeds usable page on page {page_no}", page_number=page_no)

            # Collect all child pages in order: cell 0 left child, ..., cell N-1 left child, right_child
            child_pages: List[int] = []
            for i in range(n_cells):
                cell_off = struct.unpack_from(">H", page_mv, ptr_offset + 2 * i)[0]
                if cell_off < ptr_offset + 2 * n_cells or cell_off + 4 > image.usable_page_size:
                    raise CorruptPage(f"Interior cell offset {cell_off} out of bounds on page {page_no}", page_number=page_no)
                left_child = struct.unpack_from(">I", page_mv, cell_off)[0]
                child_pages.append(left_child)

            if right_child > 0:
                child_pages.append(right_child)

            # Push children onto stack in reverse order so left-to-right order is popped
            for child_page in reversed(child_pages):
                if child_page in visited_pages:
                    raise CorruptDatabase(f"B-tree cycle detected at child page {child_page}", page_number=child_page)
                stack.append((child_page, 0))

        else:
            raise CorruptPage(f"Unexpected B-tree page type 0x{page_type:02x} on page {page_no}", page_number=page_no)


def schema_from_sqlite_master(image: SQLiteImage) -> Dict[str, TableSchema]:
    """
    Parse sqlite_master by reading root page 1 B-tree cells directly.

    Reads table definitions and extracts column names without executing SQL.

    Returns:
        Dict mapping table name to TableSchema.
    """
    tables: Dict[str, TableSchema] = {}

    for cell in iter_btree_leaf_cells(image, root_page=1):
        try:
            rec = decode_record(cell.payload_bytes, text_encoding=image.text_encoding)
        except Exception:
            continue

        if len(rec) < 5:
            continue

        entry_type = rec[0]
        name = rec[1]
        tbl_name = rec[2]
        root_page = rec[3]
        sql = rec[4]

        if entry_type == "table" and isinstance(name, str) and isinstance(root_page, int):
            sql_text = sql if isinstance(sql, str) else ""
            columns = parse_create_table_columns(sql_text)
            tables[name] = TableSchema(
                name=name,
                root_page=root_page,
                sql=sql_text,
                columns=columns,
            )

    return tables
