"""Middleware for logging unhandled exceptions while protecting cryptographic secrets."""

from __future__ import annotations

import traceback
from typing import Set

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()

# Endpoints that process raw cryptographic keys or secrets (master.md R5)
KEY_BEARING_ENDPOINTS: Set[str] = {
    "/decryption/run",
    "/pipeline/run",
}


def _is_key_bearing_endpoint(path: str) -> bool:
    """Check if the requested path corresponds to a key-bearing endpoint."""
    return any(path.endswith(ep) for ep in KEY_BEARING_ENDPOINTS)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures unhandled exceptions into the ErrorLog table.
    Enforces master.md R5: request bodies on key-bearing endpoints are strictly excluded.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            tb = traceback.format_exc()
            path_str = str(request.url.path)
            is_sensitive = _is_key_bearing_endpoint(path_str)

            # Never log body or sensitive arguments on key-bearing paths
            logger.error(
                "unhandled_exception",
                error_type=type(exc).__name__,
                message="[REDACTED ON SENSITIVE ENDPOINT]" if is_sensitive else str(exc),
                endpoint=path_str,
                method=request.method,
                client_ip=request.client.host if request.client else None,
            )

            # Persist to ErrorLog table
            try:
                from backend.app.database import SessionLocal
                from backend.repositories.log_repo import LogRepository

                db = SessionLocal()
                try:
                    repo = LogRepository(db)
                    repo.add_error_log(
                        error_type=type(exc).__name__,
                        message="Exception on key-bearing endpoint (details redacted per R5)" if is_sensitive else str(exc),
                        stack_trace=None if is_sensitive else tb,
                        endpoint=path_str,
                        method=request.method,
                        client_ip=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                    )
                finally:
                    db.close()
            except Exception:
                # If DB logging itself fails, don't mask the original error
                logger.warning("failed_to_persist_error_log", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error on decryption endpoint" if is_sensitive else (str(exc) or "Internal Server Error"),
                    "error_type": type(exc).__name__,
                },
            )
