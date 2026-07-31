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
from backend.api import cases, evidence, whatsapp, telegram, timeline, deleted, media, correlation, search, dashboard, reports, logs, demo, chats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    configure_logging(settings.log_level)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
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
app.include_router(timeline.router, prefix="/api/timeline", tags=["timeline"])
app.include_router(deleted.router, prefix="/api/deleted", tags=["deleted"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(correlation.router, prefix="/api/correlation", tags=["correlation"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])



@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "demo_mode": settings.demo_mode
    }
