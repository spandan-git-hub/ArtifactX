"""Search service for business logic."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.repositories.search_repo import SearchRepository
from backend.schemas.search import (
    MessageSearchResponse,
    ContactSearchResponse,
    MediaSearchResponse,
    GlobalSearchResponse,
    SearchSummary,
)


class SearchService:
    """Service for search operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SearchRepository(db)

    def search_messages(
        self,
        case_id: int,
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        app: str = "all",
        page: int = 1,
        page_size: int = 50,
    ) -> MessageSearchResponse:
        """
        Search messages with pagination.

        Args:
            case_id: The case ID to search within
            query: Text search query
            date_from: Start date filter
            date_to: End date filter
            app: App filter ('whatsapp', 'telegram', 'all')
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            MessageSearchResponse with paginated results
        """
        results, total = self.repo.search_messages(
            case_id=case_id,
            query=query,
            date_from=date_from,
            date_to=date_to,
            app=app,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return MessageSearchResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def search_contacts(
        self,
        case_id: int,
        query: Optional[str] = None,
        app: str = "all",
        page: int = 1,
        page_size: int = 50,
    ) -> ContactSearchResponse:
        """
        Search contacts with pagination.

        Args:
            case_id: The case ID to search within
            query: Text search query
            app: App filter ('whatsapp', 'telegram', 'all')
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            ContactSearchResponse with paginated results
        """
        results, total = self.repo.search_contacts(
            case_id=case_id,
            query=query,
            app=app,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ContactSearchResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def search_media(
        self,
        case_id: int,
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        app: str = "all",
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MediaSearchResponse:
        """
        Search media with pagination.

        Args:
            case_id: The case ID to search within
            query: Text search query
            date_from: Start date filter
            date_to: End date filter
            app: App filter ('whatsapp', 'telegram', 'all')
            media_type: Media type filter ('image', 'video', 'audio', 'document')
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            MediaSearchResponse with paginated results
        """
        results, total = self.repo.search_media(
            case_id=case_id,
            query=query,
            date_from=date_from,
            date_to=date_to,
            app=app,
            media_type=media_type,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return MediaSearchResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def global_search(
        self,
        case_id: int,
        query: str,
        app: str = "all",
        limit: int = 20,
    ) -> GlobalSearchResponse:
        """
        Perform global search across all entity types.

        Args:
            case_id: The case ID to search within
            query: Text search query
            app: App filter ('whatsapp', 'telegram', 'all')
            limit: Maximum results per category

        Returns:
            GlobalSearchResponse with categorized results
        """
        data = self.repo.global_search(
            case_id=case_id,
            query=query,
            app=app,
            limit=limit,
        )

        return GlobalSearchResponse(
            query=data["query"],
            messages=data["messages"],
            contacts=data["contacts"],
            media=data["media"],
            total_results=data["total_results"],
        )

    def get_summary(self, case_id: int) -> SearchSummary:
        """
        Get search summary statistics for a case.

        Args:
            case_id: The case ID

        Returns:
            SearchSummary with counts and date ranges
        """
        data = self.repo.get_search_summary(case_id)

        return SearchSummary(
            total_messages=data["total_messages"],
            total_contacts=data["total_contacts"],
            total_media=data["total_media"],
            date_range_start=data.get("date_range_start"),
            date_range_end=data.get("date_range_end"),
            apps=data.get("apps", []),
        )


def get_search_service(db: Session) -> SearchService:
    """Factory function to create SearchService."""
    return SearchService(db)