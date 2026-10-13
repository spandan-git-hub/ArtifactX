"""Explicit developer-only utility to initialize database schema directly without migrations."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, engine
import backend.models  # Registers models on Base.metadata


def init_db() -> None:
    """Create all database tables directly on the configured engine."""
    print("Initializing database tables via Base.metadata.create_all...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    init_db()
