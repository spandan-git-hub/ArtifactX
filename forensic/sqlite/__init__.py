"""
ArtifactX Pure-Python SQLite Forensics Toolkit.

Read-only, zero-disk-write forensic toolkit for SQLite physical inspection,
B-tree leaf and interior page traversal, WAL multi-version parsing, freelist carving,
and intra-page slack extraction.
"""

from forensic.sqlite.btree import (
    Cell,
    TableSchema,
    iter_btree_leaf_cells,
    parse_create_table_columns,
    schema_from_sqlite_master,
)
from forensic.sqlite.constants import (
    BTREE_INTERIOR_INDEX,
    BTREE_INTERIOR_TABLE,
    BTREE_LEAF_INDEX,
    BTREE_LEAF_TABLE,
    SQLITE_HEADER_SIZE,
    SQLITE_HEADER_STRING,
    TEXT_ENCODING_UTF8,
    TEXT_ENCODING_UTF16BE,
    TEXT_ENCODING_UTF16LE,
    WAL_FRAME_HEADER_SIZE,
    WAL_HEADER_SIZE,
    WAL_MAGIC_BE,
    WAL_MAGIC_LE,
    WAL_VERSION,
)
from forensic.sqlite.exceptions import (
    CorruptDatabase,
    CorruptPage,
    CorruptWalError,
    SQLiteForensicsError,
)
from forensic.sqlite.freelist import (
    FreePage,
    classify_free_page,
    walk_freelist,
)
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.record import (
    DecodedRecord,
    compute_payload_spill,
    decode_record,
    decode_record_detailed,
    decode_varint,
    encode_varint,
)
from forensic.sqlite.slack import (
    Span,
    get_span_bytes,
    walk_page_spans,
)
from forensic.sqlite.wal import (
    PageVersion,
    WalFile,
    WalFrame,
    WalHeader,
    apply_wal,
    parse_wal,
    wal_checksum,
    wal_page_history,
)

__all__ = [
    # Image
    "SQLiteImage",
    # B-tree & Schema
    "Cell",
    "TableSchema",
    "iter_btree_leaf_cells",
    "schema_from_sqlite_master",
    "parse_create_table_columns",
    # Records & Varints
    "DecodedRecord",
    "decode_varint",
    "encode_varint",
    "decode_record",
    "decode_record_detailed",
    "compute_payload_spill",
    # WAL
    "WalHeader",
    "WalFrame",
    "WalFile",
    "PageVersion",
    "parse_wal",
    "apply_wal",
    "wal_page_history",
    "wal_checksum",
    # Freelist
    "FreePage",
    "walk_freelist",
    "classify_free_page",
    # Slack
    "Span",
    "walk_page_spans",
    "get_span_bytes",
    # Exceptions
    "SQLiteForensicsError",
    "CorruptDatabase",
    "CorruptPage",
    "CorruptWalError",
    # Constants
    "SQLITE_HEADER_STRING",
    "SQLITE_HEADER_SIZE",
    "BTREE_INTERIOR_INDEX",
    "BTREE_INTERIOR_TABLE",
    "BTREE_LEAF_INDEX",
    "BTREE_LEAF_TABLE",
    "WAL_MAGIC_LE",
    "WAL_MAGIC_BE",
    "WAL_VERSION",
    "WAL_HEADER_SIZE",
    "WAL_FRAME_HEADER_SIZE",
    "TEXT_ENCODING_UTF8",
    "TEXT_ENCODING_UTF16LE",
    "TEXT_ENCODING_UTF16BE",
]
