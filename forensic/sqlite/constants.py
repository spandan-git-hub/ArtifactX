"""
SQLite File Format and WAL Constants.

All offsets and format constants are verified against:
- https://www.sqlite.org/fileformat2.html
- https://www.sqlite.org/wal.html
"""

# --- SQLite Database Header Offsets (fileformat2.html §1.2) ---
SQLITE_HEADER_STRING = b"SQLite format 3\x00"  # 16 bytes at offset 0
HEADER_OFFSET_MAGIC = 0
HEADER_OFFSET_PAGE_SIZE = 16          # 2 bytes big-endian: 512..32768, or 1 for 65536
HEADER_OFFSET_WRITE_VERSION = 18      # 1 byte: 1 for legacy, 2 for WAL
HEADER_OFFSET_READ_VERSION = 19       # 1 byte: 1 for legacy, 2 for WAL
HEADER_OFFSET_RESERVED = 20           # 1 byte: reserved bytes per page
HEADER_OFFSET_MAX_EMBEDDED = 21       # 1 byte: must be 64
HEADER_OFFSET_MIN_EMBEDDED = 22       # 1 byte: must be 32
HEADER_OFFSET_LEAF_FRACTION = 23      # 1 byte: must be 32
HEADER_OFFSET_CHANGE_COUNTER = 24     # 4 bytes big-endian
HEADER_OFFSET_PAGE_COUNT = 28         # 4 bytes big-endian
HEADER_OFFSET_FREELIST_TRUNK = 32     # 4 bytes big-endian: page number of first trunk
HEADER_OFFSET_FREELIST_COUNT = 36     # 4 bytes big-endian: total freelist page count
HEADER_OFFSET_SCHEMA_COOKIE = 40      # 4 bytes big-endian
HEADER_OFFSET_SCHEMA_FORMAT = 44      # 4 bytes big-endian: 1, 2, 3, or 4
HEADER_OFFSET_SUGGESTED_CACHE = 48    # 4 bytes big-endian
HEADER_OFFSET_LARGEST_ROOT = 52       # 4 bytes big-endian: auto-vacuum largest root
HEADER_OFFSET_TEXT_ENCODING = 56      # 4 bytes big-endian: 1=UTF-8, 2=UTF-16le, 3=UTF-16be
HEADER_OFFSET_USER_VERSION = 60       # 4 bytes big-endian
HEADER_OFFSET_INCR_VACUUM = 64        # 4 bytes big-endian: incremental vacuum flag
HEADER_OFFSET_APPLICATION_ID = 68     # 4 bytes big-endian
HEADER_OFFSET_VERSION_VALID = 92      # 4 bytes big-endian
HEADER_OFFSET_SQLITE_VERSION = 96     # 4 bytes big-endian
SQLITE_HEADER_SIZE = 100

# Text encodings (fileformat2.html §1.2 offset 56)
TEXT_ENCODING_UTF8 = 1
TEXT_ENCODING_UTF16LE = 2
TEXT_ENCODING_UTF16BE = 3

# --- B-tree Page Header Types (fileformat2.html §1.3) ---
BTREE_INTERIOR_INDEX = 0x02  # Interior index page (header length 12)
BTREE_INTERIOR_TABLE = 0x05  # Interior table page (header length 12)
BTREE_LEAF_INDEX = 0x0A      # Leaf index page (header length 8)
BTREE_LEAF_TABLE = 0x0D      # Leaf table page (header length 8)

PAGE_HEADER_SIZE_LEAF = 8
PAGE_HEADER_SIZE_INTERIOR = 12

# B-tree page header field relative offsets
PAGE_OFFSET_TYPE = 0
PAGE_OFFSET_FIRST_FREEBLOCK = 1       # 2 bytes big-endian
PAGE_OFFSET_CELL_COUNT = 3           # 2 bytes big-endian
PAGE_OFFSET_CONTENT_START = 5        # 2 bytes big-endian (0 means 65536)
PAGE_OFFSET_FRAG_BYTES = 7           # 1 byte
PAGE_OFFSET_RIGHT_CHILD = 8          # 4 bytes big-endian (interior pages only)

# --- WAL (Write-Ahead Log) Constants (wal.html §3, §4) ---
WAL_MAGIC_LE = 0x377F0682             # Little-endian checksums
WAL_MAGIC_BE = 0x377F0683             # Big-endian checksums
WAL_VERSION = 3007000
WAL_HEADER_SIZE = 32
WAL_FRAME_HEADER_SIZE = 24

# WAL header field relative offsets
WAL_HDR_MAGIC = 0                     # 4 bytes
WAL_HDR_VERSION = 4                   # 4 bytes big-endian
WAL_HDR_PAGE_SIZE = 8                 # 4 bytes big-endian
WAL_HDR_SEQ = 12                      # 4 bytes big-endian
WAL_HDR_SALT1 = 16                    # 4 bytes big-endian
WAL_HDR_SALT2 = 20                    # 4 bytes big-endian
WAL_HDR_CHECKSUM1 = 24                # 4 bytes
WAL_HDR_CHECKSUM2 = 28                # 4 bytes

# WAL frame header field relative offsets
WAL_FRAME_PAGE_NO = 0                 # 4 bytes big-endian
WAL_FRAME_COMMIT_SIZE = 4             # 4 bytes big-endian
WAL_FRAME_SALT1 = 8                   # 4 bytes big-endian
WAL_FRAME_SALT2 = 12                  # 4 bytes big-endian
WAL_FRAME_CHECKSUM1 = 16              # 4 bytes
WAL_FRAME_CHECKSUM2 = 20              # 4 bytes
