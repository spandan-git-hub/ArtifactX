"""Database configuration and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from backend.app.config import settings

# PostgreSQL configuration with connection pooling & keepalives for cloud Neon DB
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_pre_ping": True,  # Verify connections before use
    "pool_recycle": 300,    # Recycle connections every 5 mins to prevent EOF/SSL drops
    "echo": settings.debug,
}

if settings.database_url.startswith("postgresql"):
    engine_kwargs["connect_args"] = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

engine = create_engine(settings.database_url, **engine_kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session for dependency injection with automatic connection retry."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        try:
            db.rollback()
            db.close()
        except Exception:
            pass
        db = SessionLocal()

    try:
        yield db
    finally:
        db.close()