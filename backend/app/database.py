"""Database configuration and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from backend.app.config import settings

# Serverless PostgreSQL configuration (Neon cloud DB) vs In-memory SQLite for tests
engine_kwargs = {
    "echo": settings.debug,
}

if settings.database_url.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
elif settings.database_url.startswith("postgresql"):
    # NullPool prevents stale pooled sockets when Neon serverless compute suspends/resumes
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {
        "sslmode": "require",
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
else:
    engine_kwargs["poolclass"] = NullPool


engine = create_engine(settings.database_url, **engine_kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session for dependency injection with automatic connection retry."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()