"""
Typed exceptions for SQLite forensics toolkit.
Guarantees structured error reporting and prevents unhandled IndexError leaks (Rule R12).
"""

from typing import Optional


class SQLiteForensicsError(Exception):
    """Base exception for all SQLite low-level forensic parsing errors."""
    pass


class CorruptDatabase(SQLiteForensicsError):
    """Raised when an SQLite database structure violates the file format specification."""

    def __init__(self, message: str, page_number: Optional[int] = None, offset: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.page_number = page_number
        self.offset = offset

    def __str__(self) -> str:
        ctx = []
        if self.page_number is not None:
            ctx.append(f"page={self.page_number}")
        if self.offset is not None:
            ctx.append(f"offset={self.offset}")
        if ctx:
            return f"{self.message} ({', '.join(ctx)})"
        return self.message


class CorruptPage(CorruptDatabase):
    """Raised when a specific B-tree page or pointer array is internally inconsistent."""
    pass


class CorruptWalError(SQLiteForensicsError):
    """Raised when a Write-Ahead Log header or frame structure is fundamentally corrupt."""

    def __init__(self, message: str, frame_index: Optional[int] = None, offset: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.frame_index = frame_index
        self.offset = offset

    def __str__(self) -> str:
        ctx = []
        if self.frame_index is not None:
            ctx.append(f"frame={self.frame_index}")
        if self.offset is not None:
            ctx.append(f"offset={self.offset}")
        if ctx:
            return f"{self.message} ({', '.join(ctx)})"
        return self.message
