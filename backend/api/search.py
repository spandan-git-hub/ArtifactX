"""Search API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.services.search_service import SearchService
from backend.schemas.search import (
    MessageSearchResponse,
    ContactSearchResponse,
    MediaSearchResponse,
    GlobalSearchResponse,
    SearchSummary,
    AppType,
    MediaType,
)

router = APIRouter()


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """Dependency to get search service."""
    return SearchService(db)


@router.get("/search", response_model=GlobalSearchResponse)
async def global_search(
    case_id: int = Query(..., description="Case ID to search within"),
    query: str = Query(..., min_length=1, description="Search query"),
    app: AppType = Query(default=AppType.ALL, description="Filter by app"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results per category"),
    service: SearchService = Depends(get_search_service),
) -> GlobalSearchResponse:
    """
    Global search across messages, contacts, and media.

    - Searches message bodies, contact names/numbers, media paths
    - Filters by app (WhatsApp/Telegram/All)
    - Returns categorized results
    """
    return service.global_search(
        case_id=case_id,
        query=query,
        app=app.value,
        limit=limit,
    )


@router.get("/search/messages", response_model=MessageSearchResponse)
async def search_messages(
    case_id: int = Query(..., description="Case ID to search within"),
    query: Optional[str] = Query(default=None, description="Search query"),
    date_from: Optional[datetime] = Query(default=None, description="Start date"),
    date_to: Optional[datetime] = Query(default=None, description="End date"),
    app: AppType = Query(default=AppType.ALL, description="Filter by app"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Results per page"),
    service: SearchService = Depends(get_search_service),
) -> MessageSearchResponse:
    """
    Search messages with filters.

    - Full-text search on message body
    - Date range filter (date_from, date_to)
    - App filter (whatsapp/telegram/all)
    - Pagination support
    """
    return service.search_messages(
        case_id=case_id,
        query=query,
        date_from=date_from,
        date_to=date_to,
        app=app.value,
        page=page,
        page_size=page_size,
    )


@router.get("/search/contacts", response_model=ContactSearchResponse)
async def search_contacts(
    case_id: int = Query(..., description="Case ID to search within"),
    query: Optional[str] = Query(default=None, description="Search query"),
    app: AppType = Query(default=AppType.ALL, description="Filter by app"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Results per page"),
    service: SearchService = Depends(get_search_service),
) -> ContactSearchResponse:
    """
    Search contacts with filters.

    - Full-text search on name, phone, username, JID
    - App filter (whatsapp/telegram/all)
    - Pagination support
    """
    return service.search_contacts(
        case_id=case_id,
        query=query,
        app=app.value,
        page=page,
        page_size=page_size,
    )


@router.get("/search/media", response_model=MediaSearchResponse)
async def search_media(
    case_id: int = Query(..., description="Case ID to search within"),
    query: Optional[str] = Query(default=None, description="Search query"),
    date_from: Optional[datetime] = Query(default=None, description="Start date"),
    date_to: Optional[datetime] = Query(default=None, description="End date"),
    app: AppType = Query(default=AppType.ALL, description="Filter by app"),
    media_type: Optional[MediaType] = Query(default=None, description="Filter by media type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Results per page"),
    service: SearchService = Depends(get_search_service),
) -> MediaSearchResponse:
    """
    Search media with filters.

    - Search on file path/name
    - Date range filter
    - App filter (whatsapp/telegram/all)
    - Media type filter (image/video/audio/document)
    - Pagination support
    """
    media_type_value = media_type.value if media_type else None
    return service.search_media(
        case_id=case_id,
        query=query,
        date_from=date_from,
        date_to=date_to,
        app=app.value,
        media_type=media_type_value,
        page=page,
        page_size=page_size,
    )


@router.get("/search/summary", response_model=SearchSummary)
async def get_search_summary(
    case_id: int = Query(..., description="Case ID"),
    service: SearchService = Depends(get_search_service),
) -> SearchSummary:
    """
    Get search summary statistics for a case.

    Returns counts of messages, contacts, and media,
    along with date ranges and available apps.
    """
    return service.get_summary(case_id)