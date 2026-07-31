"""Middleware for logging unhandled exceptions."""

import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import structlog

logger = structlog.get_logger()


from fastapi.responses import JSONResponse

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that captures unhandled exceptions into the ErrorLog table."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "unhandled_exception",
                error_type=type(exc).__name__,
                message=str(exc),
                endpoint=str(request.url.path),
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
                        message=str(exc),
                        stack_trace=tb,
                        endpoint=str(request.url.path),
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
                content={"detail": str(exc) or "Internal Server Error", "error_type": type(exc).__name__}
            )

