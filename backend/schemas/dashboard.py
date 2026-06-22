"""Pydantic schemas for Dashboard."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class TimelineMiniEvent(BaseModel):
    """Mini timeline event for dashboard preview."""
    id: int
    event_type: str
    source_app: str
    normalized_timestamp: datetime
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class AppStats(BaseModel):
    """Statistics for a specific app (WhatsApp/Telegram)."""
    app: str
    message_count: int
    contact_count: int
    group_count: int
    media_count: int
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class CaseStats(BaseModel):
    """Case statistics."""
    total_messages: int
    total_contacts: int
    total_media: int
    total_deleted: int
    total_groups: int
    whatsapp: AppStats
    telegram: AppStats

    class Config:
        from_attributes = True


class CorrelationStats(BaseModel):
    """Correlation statistics."""
    total_edges: int
    message_contact_links: int
    message_media_links: int
    cross_app_links: int


class TimelineStats(BaseModel):
    """Timeline statistics."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_app: Dict[str, int]
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class CaseOverview(BaseModel):
    """Comprehensive case overview for dashboard."""
    case_id: int
    case_name: str
    case_status: str
    stats: CaseStats
    correlation_stats: CorrelationStats
    timeline_stats: TimelineStats
    recent_events: List[TimelineMiniEvent] = Field(default_factory=list)
    apps: List[str] = Field(default_factory=list)
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class ChartData(BaseModel):
    """Data structure for charts."""
    labels: List[str]
    values: List[int]
    title: str


class MessageActivityData(BaseModel):
    """Message activity over time for chart."""
    date: str
    whatsapp_count: int
    telegram_count: int


class MediaDistributionData(BaseModel):
    """Media type distribution for chart."""
    media_type: str
    count: int
    total_size: int


class TopContactsData(BaseModel):
    """Top contacts by message count."""
    contact_name: str
    message_count: int
    app: str