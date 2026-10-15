"""FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.database import Base, engine
from backend.utils.logging_config import configure_logging
from backend.middleware import ErrorLoggingMiddleware
from backend.api import cases, evidence, whatsapp, telegram, timeline, deleted, media, correlation, search, dashboard, reports, logs, chats, recovery, decryption, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan managing logging and startup initialization."""
    configure_logging(settings.log_level)
    yield


from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors without echoing raw inputs.
    Strictly prevents leaking secret keys in 422 responses (master.md R5).
    """
    clean_errors = []
    for err in exc.errors():
        err_dict = dict(err)
        err_dict.pop("input", None)
        clean_errors.append(err_dict)
    return JSONResponse(
        status_code=422,
        content={"detail": clean_errors},
    )

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error logging middleware (added after CORS so it wraps all requests)
app.add_middleware(ErrorLoggingMiddleware)

# Routers
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(chats.router, prefix="/api/cases", tags=["chats"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(timeline.router, prefix="/api", tags=["timeline"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["timeline"])
app.include_router(deleted.router, prefix="/api/deleted", tags=["deleted"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(correlation.router, prefix="/api", tags=["correlation"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(recovery.router, prefix="/api", tags=["recovery"])
app.include_router(decryption.router, prefix="/api", tags=["decryption"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0"
    }
