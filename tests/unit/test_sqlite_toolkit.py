"""
Unit tests for SQLite Forensics Toolkit (B8.1, B8.2, B8.3, B8.4, B8.6).

Tests crafted pages, varints, serial types, B-tree traversal, overflow reassembly,
freelist traversal, and WAL multi-version parsing with endian-aware checksums.
"""

import struct
import pytest

from forensic.sqlite.btree import (
    Cell,
    iter_btree_leaf_cells,
    parse_create_table_columns,
    schema_from_sqlite_master,
)
from forensic.sqlite.constants import (
    BTREE_INTERIOR_TABLE,
    BTREE_LEAF_TABLE,
    SQLITE_HEADER_SIZE,
    SQLITE_HEADER_STRING,
    TEXT_ENCODING_UTF8,
    TEXT_ENCODING_UTF16BE,
    TEXT_ENCODING_UTF16LE,
    WAL_HEADER_SIZE,
    WAL_MAGIC_BE,
    WAL_MAGIC_LE,
    WAL_VERSION,
)
from forensic.sqlite.exceptions import (
    CorruptDatabase,
    CorruptPage,
    CorruptWalError,
)
from forensic.sqlite.freelist import (
    classify_free_page,
    walk_freelist,
)
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.record import (
    compute_payload_spill,
    decode_record,
    decode_record_detailed,
    decode_varint,
    encode_varint,
)
from forensic.sqlite.slack import (
    get_span_bytes,
    walk_page_spans,
)
from forensic.sqlite.wal import (
    apply_wal,
    parse_wal,
    wal_checksum,
    wal_page_history,
)


def _make_header(
    page_size: int = 4096,
    page_count: int = 1,
    freelist_trunk: int = 0,
    freelist_count: int = 0,
    text_encoding: int = 1,
) -> bytearray:
    """Build a valid 100-byte SQLite database header."""
    hdr = bytearray(100)
    hdr[:16] = SQLITE_HEADER_STRING
    raw_ps = 1 if page_size == 65536 else page_size
    struct.pack_into(">H", hdr, 16, raw_ps)
    hdr[18] = 1  # write version
    hdr[19] = 1  # read version
    hdr[20] = 0  # reserved bytes
    hdr[21] = 64 # max fraction
    hdr[22] = 32 # min fraction
    hdr[23] = 32 # leaf fraction
    struct.pack_into(">I", hdr, 24, 1)  # change counter
    struct.pack_into(">I", hdr, 28, page_count)
    struct.pack_into(">I", hdr, 32, freelist_trunk)
    struct.pack_into(">I", hdr, 36, freelist_count)
    struct.pack_into(">I", hdr, 44, 4)  # schema format
    struct.pack_into(">I", hdr, 56, text_encoding)
    struct.pack_into(">I", hdr, 92, 1)  # version valid for
    return hdr


def _build_record(values: list, text_encoding: int = 1) -> bytes:
    """Helper to build a serialized SQLite record for testing."""
    serial_types = []
    body_chunks = []
    codec = "utf-8" if text_encoding == 1 else ("utf-16le" if text_encoding == 2 else "utf-16be")

    for v in values:
        if v is None:
            serial_types.append(0)
        elif isinstance(v, bool):
            serial_types.append(9 if v else 8)
        elif isinstance(v, int):
            if v == 0:
                serial_types.append(8)
            elif v == 1:
                serial_types.append(9)
            elif -128 <= v <= 127:
                serial_types.append(1)
                body_chunks.append(struct.pack(">b", v))
            elif -32768 <= v <= 32767:
                serial_types.append(2)
                body_chunks.append(struct.pack(">h", v))
            elif -8388608 <= v <= 8388607:
                serial_types.append(3)
                raw = struct.pack(">i", v)[1:]
                body_chunks.append(raw)
            elif -2147483648 <= v <= 2147483647:
                serial_types.append(4)
                body_chunks.append(struct.pack(">i", v))
            else:
                serial_types.append(6)
                body_chunks.append(struct.pack(">q", v))
        elif isinstance(v, float):
            serial_types.append(7)
            body_chunks.append(struct.pack(">d", v))
        elif isinstance(v, str):
            encoded = v.encode(codec)
            st = len(encoded) * 2 + 13
            serial_types.append(st)
            body_chunks.append(encoded)
        elif isinstance(v, (bytes, bytearray)):
            st = len(v) * 2 + 12
            serial_types.append(st)
            body_chunks.append(bytes(v))

    st_varints = b"".join(encode_varint(st) for st in serial_types)
    hdr_len = len(encode_varint(len(st_varints) + 1)) + len(st_varints)
    # Re-calculate in case varint size shifted
    hdr_len_varint = encode_varint(hdr_len)
    if len(hdr_len_varint) + len(st_varints) != hdr_len:
        hdr_len = len(encode_varint(hdr_len + 1)) + len(st_varints)
        hdr_len_varint = encode_varint(hdr_len)

    header = hdr_len_varint + st_varints
    return header + b"".join(body_chunks)


# =====================================================================
# Varint & Serial Type Tests
# =====================================================================

def test_varint_roundtrip_all_sizes():
    """Test 1 to 9 byte varint boundaries and edge cases."""
    test_values = [
        0, 1, 127, 128, 255, 16383, 16384,
        2097151, 2097152, 268435455, 268435456,
        34359738367, 34359738368, 4398046511103,
        562949953421311, 72057594037927935,
        0xFFFFFFFFFFFFFFFF,
    ]
    for val in test_values:
        encoded = encode_varint(val)
        assert 1 <= len(encoded) <= 9
        decoded, consumed = decode_varint(encoded, 0)
        assert decoded == val
        assert consumed == len(encoded)


def test_varint_offset_out_of_bounds():
    """Verify bounds check raises CorruptPage without leaking IndexError."""
    with pytest.raises(CorruptPage):
        decode_varint(b"\x80\x01", offset=5)


def test_serial_types_and_record_decoder():
    """Verify all serial types: NULL, integers, float, 0, 1, BLOB, TEXT."""
    values = [
        None,
        42,
        -1200,
        100000,
        -5000000000,
        3.14159,
        0,
        1,
        b"\xde\xad\xbe\xef",
        "Forensic Evidence",
    ]
    rec_bytes = _build_record(values)
    decoded = decode_record(rec_bytes)
    assert decoded[0] is None
    assert decoded[1] == 42
    assert decoded[2] == -1200
    assert decoded[3] == 100000
    assert decoded[4] == -5000000000
    assert pytest.approx(decoded[5], 0.0001) == 3.14159
    assert decoded[6] == 0
    assert decoded[7] == 1
    assert decoded[8] == b"\xde\xad\xbe\xef"
    assert decoded[9] == "Forensic Evidence"


def test_text_encodings_and_replacement():
    """Test UTF-8, UTF-16LE, UTF-16BE and invalid UTF-8 replacement with flag."""
    text = "Exhibit № 1 — ₹ 500"
    # UTF-8
    rec_utf8 = _build_record([text], text_encoding=TEXT_ENCODING_UTF8)
    assert decode_record(rec_utf8, text_encoding=TEXT_ENCODING_UTF8) == [text]

    # UTF-16LE
    rec_16le = _build_record([text], text_encoding=TEXT_ENCODING_UTF16LE)
    assert decode_record(rec_16le, text_encoding=TEXT_ENCODING_UTF16LE) == [text]

    # UTF-16BE
    rec_16be = _build_record([text], text_encoding=TEXT_ENCODING_UTF16BE)
    assert decode_record(rec_16be, text_encoding=TEXT_ENCODING_UTF16BE) == [text]

    # Invalid UTF-8 bytes in text column: must decode with replace and set flag
    bad_utf8 = b"\x02\x17\xff\xfe\xaa\xbb\xcc"  # header len 2, serial type 23 (TEXT len 5), 5 invalid UTF-8 bytes
    res = decode_record_detailed(bad_utf8, text_encoding=TEXT_ENCODING_UTF8)
    assert res.has_encoding_errors is True
    assert "\ufffd" in res.values[0]


# =====================================================================
# SQLiteImage & Page Size Tests
# =====================================================================

def test_page_size_65536_encoding():
    """Header page size offset 16 storing value 1 encodes 65536."""
    hdr = _make_header(page_size=65536, page_count=1)
    full_data = bytes(hdr) + b"\x00" * (65536 - 100)
    image = SQLiteImage(full_data)
    assert image.page_size == 65536
    assert image.usable_page_size == 65536
    assert image.page_count == 1
    p1 = image.get_page(1)
    assert len(p1) == 65536


def test_corrupt_database_header_checks():
    """Ensure invalid magic, truncated header, or illegal page size raise CorruptDatabase."""
    with pytest.raises(CorruptDatabase):
        SQLiteImage(b"Short")

    with pytest.raises(CorruptDatabase):
        SQLiteImage(b"Bad Magic String 12345" + b"\x00" * 100)

    # Illegal page size (not power of 2)
    bad_hdr = _make_header()
    struct.pack_into(">H", bad_hdr, 16, 3000)
    with pytest.raises(CorruptDatabase):
        SQLiteImage(bytes(bad_hdr) + b"\x00" * 4096)


# =====================================================================
# B-Tree Traversal, Cells, and Freeblocks
# =====================================================================

def test_crafted_leaf_page_with_three_cells():
    """Construct a crafted leaf page with 3 cells and verify cell iteration."""
    page_size = 4096
    hdr = _make_header(page_size=page_size, page_count=1)
    page_buf = bytearray(hdr) + bytearray(page_size - 100)

    # Page 1 B-tree header starts at offset 100
    b_off = 100
    page_buf[b_off] = BTREE_LEAF_TABLE  # 0x0D
    struct.pack_into(">H", page_buf, b_off + 1, 0)  # first freeblock = 0
    struct.pack_into(">H", page_buf, b_off + 3, 3)  # cell count = 3

    # Cells to place at end of page
    records = [
        _build_record(["Cell A", 10]),
        _build_record(["Cell B", 20]),
        _build_record(["Cell C", 30]),
    ]

    cell_offsets = []
    curr_end = page_size
    for i, rec in enumerate(records):
        rowid = i + 1
        payload_var = encode_varint(len(rec))
        rowid_var = encode_varint(rowid)
        cell_bytes = payload_var + rowid_var + rec
        curr_end -= len(cell_bytes)
        page_buf[curr_end : curr_end + len(cell_bytes)] = cell_bytes
        cell_offsets.append(curr_end)

    # Cell pointer array
    ptr_start = b_off + 8
    for i, c_off in enumerate(cell_offsets):
        struct.pack_into(">H", page_buf, ptr_start + i * 2, c_off)

    struct.pack_into(">H", page_buf, b_off + 5, curr_end)  # content start

    image = SQLiteImage(bytes(page_buf))
    cells = list(iter_btree_leaf_cells(image, root_page=1))
    assert len(cells) == 3
    assert [c.rowid for c in cells] == [1, 2, 3]
    assert decode_record(cells[0].payload_bytes) == ["Cell A", 10]
    assert decode_record(cells[1].payload_bytes) == ["Cell B", 20]
    assert decode_record(cells[2].payload_bytes) == ["Cell C", 30]


def test_freeblock_found_when_middle_cell_deleted():
    """Mark middle cell as freed and link into freeblock chain -> walk_page_spans finds it."""
    page_size = 4096
    hdr = _make_header(page_size=page_size, page_count=1)
    page_buf = bytearray(hdr) + bytearray(page_size - 100)
    b_off = 100

    page_buf[b_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", page_buf, b_off + 3, 2)  # Active cell count = 2 (middle removed)

    rec1 = _build_record(["Cell 1"])
    rec2 = _build_record(["Deleted Cell 2"])
    rec3 = _build_record(["Cell 3"])

    c3_bytes = encode_varint(len(rec3)) + encode_varint(3) + rec3
    c2_bytes = encode_varint(len(rec2)) + encode_varint(2) + rec2
    c1_bytes = encode_varint(len(rec1)) + encode_varint(1) + rec1

    off3 = page_size - len(c3_bytes)
    off2 = off3 - len(c2_bytes)
    off1 = off2 - len(c1_bytes)

    page_buf[off3 : off3 + len(c3_bytes)] = c3_bytes
    page_buf[off2 : off2 + len(c2_bytes)] = c2_bytes
    page_buf[off1 : off1 + len(c1_bytes)] = c1_bytes

    # Freeblock at off2 (middle cell)
    # Freeblock header: 2 bytes next (0), 2 bytes size
    struct.pack_into(">HH", page_buf, off2, 0, len(c2_bytes))
    struct.pack_into(">H", page_buf, b_off + 1, off2)  # first freeblock pointer

    # Active pointers: off1 and off3
    ptr_start = b_off + 8
    struct.pack_into(">H", page_buf, ptr_start, off1)
    struct.pack_into(">H", page_buf, ptr_start + 2, off3)
    struct.pack_into(">H", page_buf, b_off + 5, off1)

    image = SQLiteImage(bytes(page_buf))
    spans = walk_page_spans(image, 1)

    freeblock_spans = [s for s in spans if s.kind == "freeblock"]
    assert len(freeblock_spans) == 1
    assert freeblock_spans[0].offset == off2
    assert freeblock_spans[0].length == len(c2_bytes)
    fb_bytes = get_span_bytes(image, freeblock_spans[0])
    assert len(fb_bytes) == len(c2_bytes)


def test_corrupt_freeblock_loop_cycle_detection():
    """Circular freeblock reference must be detected and not hang."""
    page_size = 4096
    hdr = _make_header(page_size=page_size, page_count=1)
    page_buf = bytearray(hdr) + bytearray(page_size - 100)
    b_off = 100
    page_buf[b_off] = BTREE_LEAF_TABLE

    fb1 = 2000
    fb2 = 3000
    struct.pack_into(">H", page_buf, b_off + 1, fb1)  # first freeblock = fb1
    # fb1 points to fb2, fb2 points back to fb1 (circular)
    struct.pack_into(">HH", page_buf, fb1, fb2, 16)
    struct.pack_into(">HH", page_buf, fb2, fb1, 16)

    image = SQLiteImage(bytes(page_buf))
    # Must terminate cleanly
    spans = walk_page_spans(image, 1)
    assert len(spans) >= 1


def test_interior_page_with_two_leaves():
    """Craft 3-page DB: Page 1 = interior root, Page 2 = left leaf, Page 3 = right leaf."""
    page_size = 4096
    db_buf = bytearray(page_size * 3)

    # Header on Page 1
    hdr = _make_header(page_size=page_size, page_count=3)
    db_buf[:100] = hdr

    # Page 1: Interior table (0x05)
    b1_off = 100
    db_buf[b1_off] = BTREE_INTERIOR_TABLE
    struct.pack_into(">H", db_buf, b1_off + 3, 1)  # 1 cell
    struct.pack_into(">I", db_buf, b1_off + 8, 3)  # right child = page 3

    # Cell 0 on interior page: left child page 2, rowid 10
    int_cell = struct.pack(">I", 2) + encode_varint(10)
    int_cell_off = page_size - len(int_cell)
    db_buf[int_cell_off : int_cell_off + len(int_cell)] = int_cell
    struct.pack_into(">H", db_buf, b1_off + 12, int_cell_off)
    struct.pack_into(">H", db_buf, b1_off + 5, int_cell_off)

    # Page 2: Leaf table with rowid 5
    p2_off = page_size
    db_buf[p2_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", db_buf, p2_off + 3, 1)
    rec2 = _build_record(["Left Leaf Msg", 5])
    c2 = encode_varint(len(rec2)) + encode_varint(5) + rec2
    c2_off = page_size - len(c2)
    db_buf[p2_off + c2_off : p2_off + c2_off + len(c2)] = c2
    struct.pack_into(">H", db_buf, p2_off + 8, c2_off)
    struct.pack_into(">H", db_buf, p2_off + 5, c2_off)

    # Page 3: Leaf table with rowid 15
    p3_off = 2 * page_size
    db_buf[p3_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", db_buf, p3_off + 3, 1)
    rec3 = _build_record(["Right Leaf Msg", 15])
    c3 = encode_varint(len(rec3)) + encode_varint(15) + rec3
    c3_off = page_size - len(c3)
    db_buf[p3_off + c3_off : p3_off + c3_off + len(c3)] = c3
    struct.pack_into(">H", db_buf, p3_off + 8, c3_off)
    struct.pack_into(">H", db_buf, p3_off + 5, c3_off)

    image = SQLiteImage(bytes(db_buf))
    cells = list(iter_btree_leaf_cells(image, root_page=1))
    assert len(cells) == 2
    assert cells[0].rowid == 5
    assert cells[1].rowid == 15
    assert decode_record(cells[0].payload_bytes) == ["Left Leaf Msg", 5]
    assert decode_record(cells[1].payload_bytes) == ["Right Leaf Msg", 15]


def test_overflow_payload_reassembly():
    """Craft a cell spilling onto an overflow page and verify complete reassembly."""
    page_size = 4096
    db_buf = bytearray(page_size * 2)

    hdr = _make_header(page_size=page_size, page_count=2)
    db_buf[:100] = hdr

    # Page 1: Leaf table with 1 huge cell
    b_off = 100
    db_buf[b_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", db_buf, b_off + 3, 1)

    # Huge payload: 5000 bytes > 4061
    large_text = "A" * 4980
    huge_rec = _build_record([large_text])
    payload_len = len(huge_rec)
    assert payload_len > 4061

    local_len, has_overflow = compute_payload_spill(4096, payload_len, is_table_leaf=True)
    assert has_overflow is True

    local_chunk = huge_rec[:local_len]
    overflow_chunk = huge_rec[local_len:]

    # Cell structure on page 1: varint(payload_len) + varint(rowid=1) + local_chunk + overflow_page_ptr(page 2)
    c_bytes = encode_varint(payload_len) + encode_varint(1) + local_chunk + struct.pack(">I", 2)
    c_off = page_size - len(c_bytes)
    db_buf[c_off : c_off + len(c_bytes)] = c_bytes
    struct.pack_into(">H", db_buf, b_off + 8, c_off)
    struct.pack_into(">H", db_buf, b_off + 5, c_off)

    # Page 2: Overflow page
    p2_off = page_size
    # 4 bytes next page pointer = 0 (end of chain)
    struct.pack_into(">I", db_buf, p2_off, 0)
    db_buf[p2_off + 4 : p2_off + 4 + len(overflow_chunk)] = overflow_chunk

    image = SQLiteImage(bytes(db_buf))
    cells = list(iter_btree_leaf_cells(image, root_page=1))
    assert len(cells) == 1
    assert cells[0].overflow_complete is True
    assert len(cells[0].payload_bytes) == payload_len
    decoded = decode_record(cells[0].payload_bytes)
    assert decoded[0] == large_text


# =====================================================================
# Freelist Traversal Tests
# =====================================================================

def test_freelist_trunk_chain_of_three():
    """Construct a freelist with 3 trunk pages chaining to each other and holding leaf pages."""
    page_size = 4096
    total_pages = 6
    db_buf = bytearray(page_size * total_pages)

    # Trunk pages: 2, 4, 6
    # Leaf pages: 3, 5
    hdr = _make_header(
        page_size=page_size,
        page_count=total_pages,
        freelist_trunk=2,
        freelist_count=5,  # 3 trunks + 2 leaves
    )
    db_buf[:100] = hdr

    # Trunk 1 (Page 2): next trunk = 4, 1 leaf = Page 3
    off_t1 = page_size
    struct.pack_into(">II", db_buf, off_t1, 4, 1)
    struct.pack_into(">I", db_buf, off_t1 + 8, 3)

    # Trunk 2 (Page 4): next trunk = 6, 1 leaf = Page 5
    off_t2 = 3 * page_size
    struct.pack_into(">II", db_buf, off_t2, 6, 1)
    struct.pack_into(">I", db_buf, off_t2 + 8, 5)

    # Trunk 3 (Page 6): next trunk = 0, 0 leaves
    off_t3 = 5 * page_size
    struct.pack_into(">II", db_buf, off_t3, 0, 0)

    # Classify leaf page 3 as table_leaf remnants
    off_p3 = 2 * page_size
    db_buf[off_p3] = BTREE_LEAF_TABLE
    struct.pack_into(">HHHB", db_buf, off_p3 + 1, 0, 0, 4096, 0)

    image = SQLiteImage(bytes(db_buf))
    free_pages = walk_freelist(image)

    assert len(free_pages) == 5
    roles = [p.role for p in free_pages]
    page_nos = [p.page_no for p in free_pages]
    assert roles == ["trunk", "leaf", "trunk", "leaf", "trunk"]
    assert page_nos == [2, 3, 4, 5, 6]

    assert classify_free_page(free_pages[1].raw) == "table_leaf"
    assert classify_free_page(b"\x00" * 100) == "other"


# =====================================================================
# WAL Parser, Checksum, and View Tests
# =====================================================================

def test_wal_with_two_commits_uncommitted_and_stale_generation():
    """Craft WAL with: commit 1, commit 2, uncommitted frame, stale frame, and corrupted checksum."""
    page_size = 4096
    salt1, salt2 = 0x11223344, 0x55667788

    # 1. Header (32 bytes)
    wal_buf = bytearray(WAL_HEADER_SIZE)
    struct.pack_into(">I", wal_buf, 0, WAL_MAGIC_LE)
    struct.pack_into(">IIIII", wal_buf, 4, WAL_VERSION, page_size, 1, salt1, salt2)

    # Compute header checksum
    h_s1, h_s2 = wal_checksum(wal_buf[:24], 0, 0, is_big_endian=False)
    struct.pack_into(">II", wal_buf, 24, h_s1, h_s2)

    frame_size = 24 + page_size

    def make_frame(page_no: int, commit_size: int, s1: int, s2: int, running_s1: int, running_s2: int, mutate_cksum: bool = False):
        f = bytearray(frame_size)
        struct.pack_into(">IIII", f, 0, page_no, commit_size, s1, s2)
        # fill page data with patterned bytes
        f[24:] = bytes([(page_no + i) % 256 for i in range(page_size)])
        ck_input = bytes(f[:8]) + bytes(f[24:])
        c1, c2 = wal_checksum(ck_input, running_s1, running_s2, is_big_endian=False)
        if mutate_cksum:
            c1 ^= 0xDEADBEEF
        struct.pack_into(">II", f, 16, c1, c2)
        return bytes(f), c1, c2

    # Frame 1: commit 1 (page 2, commit_size=2)
    f1, r_s1, r_s2 = make_frame(2, 2, salt1, salt2, h_s1, h_s2)
    wal_buf.extend(f1)

    # Frame 2: commit 2 (page 3, commit_size=3)
    f2, r_s1, r_s2 = make_frame(3, 3, salt1, salt2, r_s1, r_s2)
    wal_buf.extend(f2)

    # Frame 3: valid uncommitted frame (page 2, commit_size=0)
    f3, r_s1, r_s2 = make_frame(2, 0, salt1, salt2, r_s1, r_s2)
    wal_buf.extend(f3)

    # Frame 4: stale generation (mismatched salt)
    f4, _, _ = make_frame(4, 0, 0x99999999, 0xAAAAAAAA, r_s1, r_s2)
    wal_buf.extend(f4)

    # Frame 5: corrupted checksum
    f5, _, _ = make_frame(5, 0, salt1, salt2, r_s1, r_s2, mutate_cksum=True)
    wal_buf.extend(f5)

    wal = parse_wal(bytes(wal_buf), page_size_hint=page_size)
    assert wal.header.magic == WAL_MAGIC_LE
    assert wal.header.is_big_endian is False
    assert len(wal.frames) == 5

    # Frame 1 & 2: valid and committed
    assert wal.frames[0].valid is True and wal.frames[0].committed is True
    assert wal.frames[1].valid is True and wal.frames[1].committed is True
    assert wal.max_committed_frame == 2

    # Frame 3: valid but NOT committed
    assert wal.frames[2].valid is True
    assert wal.frames[2].committed is False
    assert wal.frames[2].stale_generation is False

    # Frame 4: stale generation
    assert wal.frames[3].stale_generation is True
    assert wal.frames[3].valid is False

    # Frame 5: checksum mismatch
    assert wal.frames[4].valid is False

    # Page history for page 2: two versions (frame 1 and frame 3)
    p2_hist = wal_page_history(wal, 2)
    assert len(p2_hist) == 2
    assert p2_hist[0].frame_index == 1 and p2_hist[0].committed is True
    assert p2_hist[1].frame_index == 3 and p2_hist[1].committed is False


def test_apply_wal_post_view_assembly():
    """Verify apply_wal applies only committed frames and updates header page count."""
    page_size = 4096
    main_db = bytearray(page_size * 2)
    main_hdr = _make_header(page_size=page_size, page_count=2)
    main_db[:100] = main_hdr
    main_image = SQLiteImage(bytes(main_db))

    salt1, salt2 = 0x12345678, 0x87654321
    wal_buf = bytearray(WAL_HEADER_SIZE)
    struct.pack_into(">I", wal_buf, 0, WAL_MAGIC_LE)
    struct.pack_into(">IIIII", wal_buf, 4, WAL_VERSION, page_size, 1, salt1, salt2)
    h_s1, h_s2 = wal_checksum(wal_buf[:24], 0, 0, is_big_endian=False)
    struct.pack_into(">II", wal_buf, 24, h_s1, h_s2)

    # Frame 1: modifies page 2, grows DB to 3 pages
    f1 = bytearray(24 + page_size)
    struct.pack_into(">IIII", f1, 0, 2, 3, salt1, salt2)
    f1[24:] = b"\x42" * page_size
    c1, c2 = wal_checksum(bytes(f1[:8]) + bytes(f1[24:]), h_s1, h_s2, is_big_endian=False)
    struct.pack_into(">II", f1, 16, c1, c2)
    wal_buf.extend(f1)

    wal = parse_wal(bytes(wal_buf), page_size_hint=page_size)
    post_view = apply_wal(main_image, wal)

    # Post-view must have grown to 3 pages
    assert len(post_view) == 3 * page_size
    post_image = SQLiteImage(post_view)
    assert post_image.page_count == 3
    # Page 2 content was updated
    assert post_image.get_page(2) == b"\x42" * page_size


# =====================================================================
# CREATE TABLE Column Parsing
# =====================================================================

def test_parse_create_table_columns_tokenizer():
    """Test column extraction without executing SQL across varied SQLite DDL."""
    sql = """
    CREATE TABLE IF NOT EXISTS [users] (
        _id INTEGER PRIMARY KEY AUTOINCREMENT,
        "name" TEXT NOT NULL,
        `phone_number` VARCHAR(32) DEFAULT '+1',
        [address] TEXT,
        data BLOB,
        CONSTRAINT fk_jid FOREIGN KEY (_id) REFERENCES jid(_id),
        UNIQUE (phone_number)
    );
    """
    cols = parse_create_table_columns(sql)
    assert cols == ["_id", "name", "phone_number", "address", "data"]
