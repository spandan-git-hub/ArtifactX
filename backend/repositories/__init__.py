"""Repository layer."""

from backend.repositories.whatsapp_repo import WhatsAppRepository
from backend.repositories.telegram_repo import TelegramRepository
from backend.repositories.timeline_repo import TimelineRepository
from backend.repositories.deleted_repo import DeletedRepository
from backend.repositories.media_repo import MediaRepository
from backend.repositories.correlation_repo import CorrelationRepository
from backend.repositories.search_repo import SearchRepository
from backend.repositories.dashboard_repo import DashboardRepository

__all__ = [
    "WhatsAppRepository",
    "TelegramRepository",
    "TimelineRepository",
    "DeletedRepository",
    "MediaRepository",
    "CorrelationRepository",
    "SearchRepository",
    "DashboardRepository",
]