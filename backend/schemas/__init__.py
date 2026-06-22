"""Pydantic schemas."""

from backend.schemas.case import CaseCreate, CaseRead
from backend.schemas.evidence import EvidenceCreate, EvidenceRead
from backend.schemas.message import MessageCreate, MessageRead
from backend.schemas.contact import ContactCreate, ContactRead
from backend.schemas.telegram_message import TelegramMessageCreate, TelegramMessageRead
from backend.schemas.telegram_contact import TelegramContactCreate, TelegramContactRead
from backend.schemas.telegram_group import TelegramGroupCreate, TelegramGroupRead
from backend.schemas.group import GroupCreate, GroupRead
from backend.schemas.timeline import TimelineEventCreate, TimelineEventRead
from backend.schemas.deleted import DeletedMessageCreate, DeletedMessageRead
from backend.schemas.search import (
    AppType, MediaType, SearchParams,
    MessageSearchResult, MessageSearchResponse,
    ContactSearchResult, ContactSearchResponse,
    MediaSearchResult, MediaSearchResponse,
    GlobalSearchResult, GlobalSearchResponse,
    DateFilterRequest, AppFilterRequest, SearchSummary,
)
from backend.schemas.dashboard import (
    TimelineMiniEvent, AppStats, CaseStats, CorrelationStats,
    TimelineStats, CaseOverview, ChartData,
    MessageActivityData, MediaDistributionData, TopContactsData,
)
from backend.schemas.report import (
    ReportType, ReportFormat, ReportStatus,
    EvidenceSummary, EvidenceReportData,
    TimelineSummary, TimelineReportData,
    DeletedMessageSummary, DeletedMessageReportData,
    FullReportData, ReportGenerateRequest, ReportGenerateResponse,
    ReportInfo, ReportDownloadResponse,
)
from backend.schemas.log import (
    AnalysisLogEntry,
    ErrorLogEntry,
    ActivityLogEntry,
    LogFilter,
    LogSummary,
)

__all__ = [
    "CaseCreate", "CaseRead",
    "EvidenceCreate", "EvidenceRead",
    "MessageCreate", "MessageRead",
    "ContactCreate", "ContactRead",
    "TelegramMessageCreate", "TelegramMessageRead",
    "TelegramContactCreate", "TelegramContactRead",
    "TelegramGroupCreate", "TelegramGroupRead",
    "GroupCreate", "GroupRead",
    "TimelineEventCreate", "TimelineEventRead",
    "DeletedMessageCreate", "DeletedMessageRead",
    "AppType", "MediaType", "SearchParams",
    "MessageSearchResult", "MessageSearchResponse",
    "ContactSearchResult", "ContactSearchResponse",
    "MediaSearchResult", "MediaSearchResponse",
    "GlobalSearchResult", "GlobalSearchResponse",
    "DateFilterRequest", "AppFilterRequest", "SearchSummary",
    "TimelineMiniEvent", "AppStats", "CaseStats", "CorrelationStats",
    "TimelineStats", "CaseOverview", "ChartData",
    "MessageActivityData", "MediaDistributionData", "TopContactsData",
    "ReportType", "ReportFormat", "ReportStatus",
    "EvidenceSummary", "EvidenceReportData",
    "TimelineSummary", "TimelineReportData",
    "DeletedMessageSummary", "DeletedMessageReportData",
    "FullReportData", "ReportGenerateRequest", "ReportGenerateResponse",
    "ReportInfo", "ReportDownloadResponse",
    "AnalysisLogEntry", "ErrorLogEntry", "ActivityLogEntry",
    "LogFilter", "LogSummary",
]