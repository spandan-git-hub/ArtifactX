"""
SQLite Write-Ahead Log (WAL) Parser and View Generator.

Implements byte-accurate WAL header and frame parsing, cumulative checksum validation,
stale generation tracking, multi-version page history, and post-WAL view assembly
per https://www.sqlite.org/wal.html and Rules R4, R8, R11, and R12.
"""

from dataclasses import dataclass, field
import hashlib
import struct
from typing import Dict, List, Optional, Tuple, Union

from forensic.sqlite.constants import (
    HEADER_OFFSET_PAGE_COUNT,
    SQLITE_HEADER_SIZE,
    WAL_FRAME_HEADER_SIZE,
    WAL_HEADER_SIZE,
    WAL_MAGIC_BE,
    WAL_MAGIC_LE,
    WAL_VERSION,
)
from forensic.sqlite.exceptions import CorruptWalError
from forensic.sqlite.image import SQLiteImage


def wal_checksum(data: Union[bytes, memoryview], s1: int, s2: int, is_big_endian: bool) -> Tuple[int, int]:
    """
    Compute SQLite WAL checksum over an 8-byte aligned buffer.

    Per sqlite.org/wal.html §4.1:
    - If is_big_endian is True (magic 0x377F0683): unpacks 32-bit words with '>II'.
    - If is_big_endian is False (magic 0x377F0682): unpacks 32-bit words with '<II'.
    - s1 = (s1 + v0 + s2) & 0xFFFFFFFF
    - s2 = (s2 + v1 + s1) & 0xFFFFFFFF
    """
    fmt = ">II" if is_big_endian else "<II"
    n_pairs = len(data) // 8
    for i in range(0, n_pairs * 8, 8):
        v0, v1 = struct.unpack_from(fmt, data, i)
        s1 = (s1 + v0 + s2) & 0xFFFFFFFF
        s2 = (s2 + v1 + s1) & 0xFFFFFFFF
    return s1, s2


@dataclass(frozen=True)
class WalHeader:
    """Parsed SQLite WAL file header (32 bytes)."""
    magic: int
    version: int
    page_size: int
    seq_number: int
    salt1: int
    salt2: int
    checksum1: int
    checksum2: int
    is_big_endian: bool


@dataclass(frozen=True)
class WalFrame:
    """Parsed SQLite WAL frame header and payload."""
    index: int
    offset: int
    page_no: int
    commit_size: int
    salt1: int
    salt2: int
    checksum1: int
    checksum2: int
    valid: bool
    committed: bool
    stale_generation: bool
    data: bytes
    sha256: str


@dataclass(frozen=True)
class PageVersion:
    """Historical version of a page extracted from WAL frames."""
    page_no: int
    frame_index: int
    frame_offset: int
    is_commit: bool
    valid: bool
    committed: bool
    stale_generation: bool
    data: bytes
    sha256: str


@dataclass
class WalFile:
    """Full representation of a parsed Write-Ahead Log stream."""
    header: WalHeader
    frames: List[WalFrame] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    max_committed_frame: Optional[int] = None


def parse_wal(data: Union[bytes, bytearray, memoryview], page_size_hint: Optional[int] = None) -> WalFile:
    """
    Parse an SQLite WAL buffer into a WalFile structure.

    Validates header, verifies cumulative frame checksums, identifies commit boundaries,
    and flags stale-generation or uncommitted frames.

    Args:
        data: Raw WAL file bytes.
        page_size_hint: Optional expected page size from the main database image.

    Returns:
        WalFile containing header, frames, warnings, and commit index.
    """
    mv = memoryview(data)
    if len(mv) < WAL_HEADER_SIZE:
        raise CorruptWalError(f"WAL data too short ({len(mv)} < 32 bytes)", offset=0)

    # Magic at offset 0
    raw_magic = struct.unpack_from(">I", mv, 0)[0]
    if raw_magic == WAL_MAGIC_BE:
        is_be = True
        magic = WAL_MAGIC_BE
    elif raw_magic == WAL_MAGIC_LE:
        is_be = False
        magic = WAL_MAGIC_LE
    else:
        raise CorruptWalError(f"Invalid WAL magic: 0x{raw_magic:08x}", offset=0)

    # Big-endian integer fields in header: version, page_size, seq, salt1, salt2
    version, page_size, seq_num, salt1, salt2 = struct.unpack_from(">IIIII", mv, 4)

    # Stored checksums
    c1, c2 = struct.unpack_from(">II", mv, 24)

    effective_page_size = page_size
    if effective_page_size < 512 or effective_page_size > 65536 or (effective_page_size & (effective_page_size - 1)) != 0:
        if page_size_hint and 512 <= page_size_hint <= 65536:
            effective_page_size = page_size_hint
        else:
            effective_page_size = 4096

    header = WalHeader(
        magic=magic,
        version=version,
        page_size=effective_page_size,
        seq_number=seq_num,
        salt1=salt1,
        salt2=salt2,
        checksum1=c1,
        checksum2=c2,
        is_big_endian=is_be,
    )

    warnings: List[str] = []

    # Verify header checksum (computed over first 24 bytes with s1=0, s2=0)
    exp_s1, exp_s2 = wal_checksum(mv[:24], 0, 0, is_be)
    if exp_s1 != c1 or exp_s2 != c2:
        warnings.append(
            f"WAL header checksum mismatch: expected ({hex(exp_s1)}, {hex(exp_s2)}), got ({hex(c1)}, {hex(c2)})"
        )

    # Parse frames
    frames: List[WalFrame] = []
    frame_size = WAL_FRAME_HEADER_SIZE + effective_page_size
    num_frames = (len(mv) - WAL_HEADER_SIZE) // frame_size

    running_s1, running_s2 = exp_s1, exp_s2
    last_commit_idx: Optional[int] = None
    checksum_intact = True

    for i in range(num_frames):
        f_off = WAL_HEADER_SIZE + i * frame_size
        f_hdr = mv[f_off : f_off + WAL_FRAME_HEADER_SIZE]

        page_no, commit_size, fs1, fs2 = struct.unpack_from(">IIII", f_hdr, 0)
        fc1, fc2 = struct.unpack_from(">II", f_hdr, 16)

        page_data = bytes(mv[f_off + WAL_FRAME_HEADER_SIZE : f_off + frame_size])
        page_sha = hashlib.sha256(page_data).hexdigest()

        # Check salts
        salts_match = (fs1 == salt1 and fs2 == salt2)
        stale_gen = not salts_match

        # Check cumulative checksum
        is_valid = False
        if checksum_intact and not stale_gen:
            ck_chunk = bytes(f_hdr[:8]) + page_data
            calc_s1, calc_s2 = wal_checksum(ck_chunk, running_s1, running_s2, is_be)
            if calc_s1 == fc1 and calc_s2 == fc2:
                is_valid = True
                running_s1, running_s2 = calc_s1, calc_s2
            else:
                checksum_intact = False
                warnings.append(f"Frame {i + 1} cumulative checksum mismatch")
        elif stale_gen:
            warnings.append(f"Frame {i + 1} salt mismatch (stale generation)")

        if is_valid and commit_size > 0:
            last_commit_idx = i + 1

        frame = WalFrame(
            index=i + 1,
            offset=f_off,
            page_no=page_no,
            commit_size=commit_size,
            salt1=fs1,
            salt2=fs2,
            checksum1=fc1,
            checksum2=fc2,
            valid=is_valid,
            committed=False,  # Assigned in second pass below
            stale_generation=stale_gen,
            data=page_data,
            sha256=page_sha,
        )
        frames.append(frame)

    # Mark committed frames (valid frames up to last_commit_idx)
    committed_frames: List[WalFrame] = []
    for f in frames:
        is_committed = (last_commit_idx is not None and f.index <= last_commit_idx and f.valid)
        committed_frames.append(
            WalFrame(
                index=f.index,
                offset=f.offset,
                page_no=f.page_no,
                commit_size=f.commit_size,
                salt1=f.salt1,
                salt2=f.salt2,
                checksum1=f.checksum1,
                checksum2=f.checksum2,
                valid=f.valid,
                committed=is_committed,
                stale_generation=f.stale_generation,
                data=f.data,
                sha256=f.sha256,
            )
        )

    return WalFile(
        header=header,
        frames=committed_frames,
        warnings=warnings,
        max_committed_frame=last_commit_idx,
    )


def wal_page_history(wal: WalFile, page_no: int) -> List[PageVersion]:
    """
    Return all versions of page_no across all frames in chronological order.
    Input to Tier 2 temporal deletion recovery.
    """
    history: List[PageVersion] = []
    for f in wal.frames:
        if f.page_no == page_no:
            history.append(
                PageVersion(
                    page_no=page_no,
                    frame_index=f.index,
                    frame_offset=f.offset,
                    is_commit=(f.commit_size > 0),
                    valid=f.valid,
                    committed=f.committed,
                    stale_generation=f.stale_generation,
                    data=f.data,
                    sha256=f.sha256,
                )
            )
    return history


def apply_wal(
    main: SQLiteImage,
    wal: WalFile,
    upto_commit: Optional[int] = None,
) -> bytes:
    """
    Assemble the 'post-WAL view' by applying committed WAL frames onto the main database image.

    Guarantees:
    - Pure in-memory transformation; zero disk writes (R4).
    - Preserves uncommitted and stale-generation frames from polluting the clean post-WAL view.
    - Extends the page buffer if the WAL commit grew the database.
    - Updates SQLite header page count at offset 28..32.
    """
    page_size = main.page_size
    buf = bytearray(main.data)

    target_commit = upto_commit if upto_commit is not None else wal.max_committed_frame

    # Collect frames to apply
    frames_to_apply: List[WalFrame] = []
    new_db_page_count = main.page_count

    for f in wal.frames:
        if target_commit is not None and f.index > target_commit:
            continue
        if not f.valid:
            continue
        # Only committed frames are applied
        if not f.committed and upto_commit is None:
            continue

        frames_to_apply.append(f)
        if f.commit_size > 0 and f.commit_size > new_db_page_count:
            new_db_page_count = f.commit_size

    # Ensure buffer is large enough for all referenced pages or commit size
    max_ref_page = max([f.page_no for f in frames_to_apply], default=new_db_page_count)
    final_page_count = max(new_db_page_count, max_ref_page)

    required_bytes = final_page_count * page_size
    if len(buf) < required_bytes:
        buf.extend(b"\x00" * (required_bytes - len(buf)))

    # Apply frames sequentially
    for f in frames_to_apply:
        start = (f.page_no - 1) * page_size
        end = start + page_size
        buf[start:end] = f.data

    # Update database size in pages at offset 28..32 in the SQLite header
    if len(buf) >= SQLITE_HEADER_SIZE:
        struct.pack_into(">I", buf, HEADER_OFFSET_PAGE_COUNT, final_page_count)

    return bytes(buf)
