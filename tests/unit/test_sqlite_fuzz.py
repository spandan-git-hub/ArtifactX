"""
Hostile-input fuzz testing for SQLite forensics toolkit (B8.1, R12).

Performs 1000 seeded random byte mutations against database images and 500 mutations
against WAL streams. Asserts that the parser raises only typed SQLiteForensicsError
exceptions or returns safely with warnings, never crashing, leaking unhandled IndexErrors,
or hanging in infinite loops.
"""

import random
import struct
import pytest

from forensic.sqlite.btree import (
    iter_btree_leaf_cells,
    schema_from_sqlite_master,
)
from forensic.sqlite.constants import (
    BTREE_LEAF_TABLE,
    SQLITE_HEADER_STRING,
    WAL_HEADER_SIZE,
    WAL_MAGIC_LE,
    WAL_VERSION,
)
from forensic.sqlite.exceptions import (
    CorruptDatabase,
    CorruptPage,
    CorruptWalError,
    SQLiteForensicsError,
)
from forensic.sqlite.freelist import walk_freelist
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.record import (
    decode_record,
    decode_varint,
    encode_varint,
)
from forensic.sqlite.slack import walk_page_spans
from forensic.sqlite.wal import (
    apply_wal,
    parse_wal,
    wal_checksum,
)


def _create_base_fuzz_db() -> bytes:
    """Create a minimal valid 2-page SQLite database with 1 table on page 2."""
    page_size = 4096
    buf = bytearray(page_size * 2)

    # Header on page 1
    buf[:16] = SQLITE_HEADER_STRING
    struct.pack_into(">H", buf, 16, page_size)
    buf[18] = 1
    buf[19] = 1
    struct.pack_into(">I", buf, 24, 1)
    struct.pack_into(">I", buf, 28, 2)
    struct.pack_into(">I", buf, 44, 4)
    struct.pack_into(">I", buf, 56, 1)
    struct.pack_into(">I", buf, 92, 1)

    # Page 1: Leaf table with sqlite_master entry for table 't' on page 2
    b1_off = 100
    buf[b1_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", buf, b1_off + 3, 1)

    # Master entry: type='table', name='t', tbl_name='t', rootpage=2, sql='CREATE TABLE t (id INT, val TEXT)'
    serial_types = encode_varint(6) + bytes([
        len("table") * 2 + 13,
        len("t") * 2 + 13,
        len("t") * 2 + 13,
        1,  # rootpage=2 in 1 byte
        len("CREATE TABLE t (id INT, val TEXT)") * 2 + 13,
    ])
    payload = (
        encode_varint(len(serial_types))
        + serial_types
        + b"table"
        + b"t"
        + b"t"
        + b"\x02"
        + b"CREATE TABLE t (id INT, val TEXT)"
    )
    cell = encode_varint(len(payload)) + encode_varint(1) + payload
    cell_off = page_size - len(cell)
    buf[cell_off : cell_off + len(cell)] = cell
    struct.pack_into(">H", buf, b1_off + 8, cell_off)
    struct.pack_into(">H", buf, b1_off + 5, cell_off)

    # Page 2: Leaf table for table 't' with 2 rows
    p2_off = page_size
    buf[p2_off] = BTREE_LEAF_TABLE
    struct.pack_into(">H", buf, p2_off + 3, 2)

    row1_payload = b"\x03\x01\x15\x05Sample"
    c1 = encode_varint(len(row1_payload)) + encode_varint(1) + row1_payload
    c1_off = page_size - len(c1)
    buf[p2_off + c1_off : p2_off + c1_off + len(c1)] = c1

    row2_payload = b"\x03\x01\x15\x06Second"
    c2 = encode_varint(len(row2_payload)) + encode_varint(2) + row2_payload
    c2_off = c1_off - len(c2)
    buf[p2_off + c2_off : p2_off + c2_off + len(c2)] = c2

    struct.pack_into(">H", buf, p2_off + 8, c1_off)
    struct.pack_into(">H", buf, p2_off + 10, c2_off)
    struct.pack_into(">H", buf, p2_off + 5, c2_off)

    return bytes(buf)


def _create_base_fuzz_wal() -> bytes:
    """Create a minimal valid WAL stream with 2 frames."""
    page_size = 4096
    salt1, salt2 = 0x11223344, 0x55667788
    buf = bytearray(WAL_HEADER_SIZE)
    struct.pack_into(">I", buf, 0, WAL_MAGIC_LE)
    struct.pack_into(">IIIII", buf, 4, WAL_VERSION, page_size, 1, salt1, salt2)
    h1, h2 = wal_checksum(buf[:24], 0, 0, is_big_endian=False)
    struct.pack_into(">II", buf, 24, h1, h2)

    frame_size = 24 + page_size
    # Frame 1: page 2, commit_size=2
    f1 = bytearray(frame_size)
    struct.pack_into(">IIII", f1, 0, 2, 2, salt1, salt2)
    f1[24:] = b"\xAA" * page_size
    c1, c2 = wal_checksum(bytes(f1[:8]) + bytes(f1[24:]), h1, h2, is_big_endian=False)
    struct.pack_into(">II", f1, 16, c1, c2)
    buf.extend(f1)

    return bytes(buf)


def test_sqlite_fuzz_1000_database_mutations():
    """Run 1000 seeded random mutations and assert clean exception handling."""
    base_db = _create_base_fuzz_db()
    rng = random.Random(1337)

    for i in range(1000):
        mutated = bytearray(base_db)
        mutation_kind = rng.choice(["flip", "delete", "insert", "chunk_scramble", "truncate"])

        if mutation_kind == "flip":
            pos = rng.randint(0, len(mutated) - 1)
            mutated[pos] ^= rng.randint(1, 255)
        elif mutation_kind == "delete":
            pos = rng.randint(0, len(mutated) - 10)
            del mutated[pos : pos + rng.randint(1, 64)]
        elif mutation_kind == "insert":
            pos = rng.randint(0, len(mutated) - 1)
            mutated[pos:pos] = bytes([rng.randint(0, 255) for _ in range(rng.randint(1, 64))])
        elif mutation_kind == "chunk_scramble":
            pos = rng.randint(0, len(mutated) - 16)
            for j in range(pos, pos + 16):
                mutated[j] = rng.randint(0, 255)
        elif mutation_kind == "truncate":
            cut = rng.randint(1, len(mutated) - 1)
            mutated = mutated[:cut]

        try:
            image = SQLiteImage(bytes(mutated))
            # Test schema parsing
            schemas = schema_from_sqlite_master(image)
            # Test freelist walking
            walk_freelist(image)
            # Test slack spans on page 1
            walk_page_spans(image, 1)

            for table_name, tbl_meta in schemas.items():
                if 1 <= tbl_meta.root_page <= image.page_count:
                    # Iterate cells up to a limit
                    cell_count = 0
                    for cell in iter_btree_leaf_cells(image, tbl_meta.root_page, max_pages=100):
                        cell_count += 1
                        if cell_count > 50:
                            break
                        decode_record(cell.payload_bytes)

        except SQLiteForensicsError:
            # Expected typed error
            pass
        except Exception as exc:
            pytest.fail(f"Fuzz iteration {i} leaked untyped exception {type(exc).__name__}: {exc}")


def test_wal_fuzz_500_mutations():
    """Run 500 seeded random mutations against WAL parser and assert clean typed handling."""
    base_wal = _create_base_fuzz_wal()
    rng = random.Random(2026)

    for i in range(500):
        mutated = bytearray(base_wal)
        mutation_kind = rng.choice(["flip", "delete", "insert", "chunk_scramble", "truncate"])

        if mutation_kind == "flip":
            pos = rng.randint(0, len(mutated) - 1)
            mutated[pos] ^= rng.randint(1, 255)
        elif mutation_kind == "delete":
            pos = rng.randint(0, len(mutated) - 10)
            del mutated[pos : pos + rng.randint(1, 32)]
        elif mutation_kind == "insert":
            pos = rng.randint(0, len(mutated) - 1)
            mutated[pos:pos] = bytes([rng.randint(0, 255) for _ in range(rng.randint(1, 32))])
        elif mutation_kind == "chunk_scramble":
            pos = rng.randint(0, len(mutated) - 16)
            for j in range(pos, pos + 16):
                mutated[j] = rng.randint(0, 255)
        elif mutation_kind == "truncate":
            cut = rng.randint(1, len(mutated) - 1)
            mutated = mutated[:cut]

        try:
            wal = parse_wal(bytes(mutated), page_size_hint=4096)
            assert isinstance(wal.frames, list)
        except CorruptWalError:
            pass
        except Exception as exc:
            pytest.fail(f"WAL fuzz iteration {i} leaked untyped exception {type(exc).__name__}: {exc}")
