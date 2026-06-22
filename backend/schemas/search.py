"""Pydantic schemas for Search & Filtering."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field


class AppType(str, Enum):
    """Source application type."""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    ALL = "all"


class MediaType(str, Enum):
    """Media type filter."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ALL = "all"


# Base Search Parameters
class SearchParams(BaseModel):
    """Common search parameters."""
    case_id: int
    query: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    app: AppType = AppType.ALL
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


# Message Search
class MessageSearchResult(BaseModel):
    """Single message search result."""
    id: int
    evidence_id: int
    app: str  # 'whatsapp' or 'telegram'
    message_id: Optional[str] = None
    chat_jid: Optional[str] = None
    sender: Optional[str] = None
    body: Optional[str] = None
    timestamp: datetime
    media_type: Optional[str] = None
    media_path: Optional[str] = None

    class Config:
        from_attributes = True


class MessageSearchResponse(BaseModel):
    """Paginated message search response."""
    results: List[MessageSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int


# Contact Search
class ContactSearchResult(BaseModel):
    """Single contact search result."""
    id: int
    evidence_id: int
    app: str  # 'whatsapp' or 'telegram'
    jid: Optional[str] = None
    display_name: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class ContactSearchResponse(BaseModel):
    """Paginated contact search response."""
    results: List[ContactSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int


# Media Search
class MediaSearchResult(BaseModel):
    """Single media search result."""
    id: int
    case_id: int
    evidence_id: int
    file_path: str
    sha256: str
    mime_type: Optional[str] = None
    media_type: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    is_orphan: bool = False
    linked_message_id: Optional[str] = None

    class Config:
        from_attributes = True


class MediaSearchResponse(BaseModel):
    """Paginated media search response."""
    results: List[MediaSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int


# Global Search
class GlobalSearchResult(BaseModel):
    """Single global search result."""
    type: str  # 'message', 'contact', or 'media'
    id: int
    app: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    details: dict = Field(default_factory=dict)


class GlobalSearchResponse(BaseModel):
    """Global search response with categorized results."""
    query: str
    messages: List[MessageSearchResult] = Field(default_factory=list)
    contacts: List[ContactSearchResult] = Field(default_factory=list)
    media: List[MediaSearchResult] = Field(default_factory=list)
    total_results: int


# Date Filter Request
class DateFilterRequest(BaseModel):
    """Request for date-filtered search."""
    case_id: int
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    app: AppType = AppType.ALL
    event_types: Optional[List[str]] = None  # 'message', 'contact', 'media'


# App Filter Request
class AppFilterRequest(BaseModel):
    """Request for app-filtered search."""
    case_id: int
    apps: List[AppType] = Field(default_factory=list)
    query: Optional[str] = None


# Search Summary (for dashboard)
class SearchSummary(BaseModel):
    """Summary statistics for search results."""
    total_messages: int
    total_contacts: int
    total_media: int
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    apps: List[str] = Field(default_factory=list)