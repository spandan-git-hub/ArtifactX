"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import Base, engine
from backend.api import cases, evidence, whatsapp, telegram, timeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["timeline"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
