"""
SQLite Write-Ahead Log (WAL) frame parser and historical page carver.
Non-destructively inspects WAL frames, exposes page revisions, and recovers pre-checkpoint states.
"""

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


WAL_MAGIC_LE = 0x377F0682
WAL_MAGIC_BE = 0x377F0683
WAL_HEADER_SIZE = 32
WAL_FRAME_HEADER_SIZE = 24


@dataclass(frozen=True)
class WalHeader:
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
    frame_index: int
    offset: int
    page_number: int
    commit_size: int
    salt1: int
    salt2: int
    checksum1: int
    checksum2: int
    data: bytes
    sha256: str


@dataclass
class WalPageImage:
    page_number: int
    frame_index: int
    frame_offset: int
    is_commit: bool
    data: bytes
    sha256: str


class WalCarver:
    """Carves historical and deleted pages from SQLite WAL (Write-Ahead Log) streams."""

    def __init__(self, wal_bytes: bytes, db_page_size: Optional[int] = None):
        self.wal_bytes = wal_bytes
        self.db_page_size = db_page_size
        self.header: Optional[WalHeader] = None
        self.frames: List[WalFrame] = []
        self.parse_errors: List[str] = []

    def parse(self) -> bool:
        """Parse WAL header and all valid frames."""
        if len(self.wal_bytes) < WAL_HEADER_SIZE:
            self.parse_errors.append(
                f"WAL data too short ({len(self.wal_bytes)} bytes < 32 bytes required)"
            )
            return False

        # Try big-endian then little-endian magic
        magic_val = struct.unpack(">I", self.wal_bytes[:4])[0]
        is_be = True
        if magic_val == WAL_MAGIC_BE:
            is_be = True
        elif magic_val == WAL_MAGIC_LE:
            is_be = False
        else:
            # Try little-endian unpack
            magic_le = struct.unpack("<I", self.wal_bytes[:4])[0]
            if magic_le == WAL_MAGIC_BE:
                is_be = True
                magic_val = magic_le
            elif magic_le == WAL_MAGIC_LE:
                is_be = False
                magic_val = magic_le
            else:
                self.parse_errors.append(f"Invalid WAL magic: 0x{magic_val:08x}")
                return False

        endian_fmt = ">" if is_be else "<"
        version, page_size, seq_number, salt1, salt2, c1, c2 = struct.unpack(
            f"{endian_fmt}IIIIIII", self.wal_bytes[4:WAL_HEADER_SIZE]
        )

        effective_page_size = page_size
        if effective_page_size < 512 or effective_page_size > 65536:
            if self.db_page_size and 512 <= self.db_page_size <= 65536:
                effective_page_size = self.db_page_size
            else:
                effective_page_size = 4096  # Default fallback

        self.header = WalHeader(
            magic=magic_val,
            version=version,
            page_size=effective_page_size,
            seq_number=seq_number,
            salt1=salt1,
            salt2=salt2,
            checksum1=c1,
            checksum2=c2,
            is_big_endian=is_be,
        )

        # Parse frames
        offset = WAL_HEADER_SIZE
        frame_size = WAL_FRAME_HEADER_SIZE + effective_page_size
        frame_idx = 1

        while offset + frame_size <= len(self.wal_bytes):
            f_hdr = self.wal_bytes[offset : offset + WAL_FRAME_HEADER_SIZE]
            page_num, commit_size, f_salt1, f_salt2, f_c1, f_c2 = struct.unpack(
                f"{endian_fmt}IIIIII", f_hdr
            )

            # Extract page data
            page_data = self.wal_bytes[
                offset + WAL_FRAME_HEADER_SIZE : offset + frame_size
            ]
            frame_sha = hashlib.sha256(page_data).hexdigest()

            frame = WalFrame(
                frame_index=frame_idx,
                offset=offset,
                page_number=page_num,
                commit_size=commit_size,
                salt1=f_salt1,
                salt2=f_salt2,
                checksum1=f_c1,
                checksum2=f_c2,
                data=page_data,
                sha256=frame_sha,
            )
            self.frames.append(frame)

            offset += frame_size
            frame_idx += 1

        return len(self.frames) > 0

    def get_historical_page_images(self) -> Dict[int, List[WalPageImage]]:
        """
        Group parsed frames by page number.
        Enables access to pre-checkpoint historical versions of pages.
        """
        reconstructions: Dict[int, List[WalPageImage]] = {}
        for f in self.frames:
            img = WalPageImage(
                page_number=f.page_number,
                frame_index=f.frame_index,
                frame_offset=f.offset,
                is_commit=f.commit_size > 0,
                data=f.data,
                sha256=f.sha256,
            )
            if f.page_number not in reconstructions:
                reconstructions[f.page_number] = []
            reconstructions[f.page_number].append(img)
        return reconstructions

    def get_superseded_pages(self) -> List[WalPageImage]:
        """
        Identify pages that were overwritten by later frames in the same WAL.
        These superseded pages are prime candidates for deleted records.
        """
        superseded = []
        page_map = self.get_historical_page_images()
        for page_num, images in page_map.items():
            if len(images) > 1:
                # All except the newest frame are superseded historical states
                superseded.extend(images[:-1])
        return superseded
