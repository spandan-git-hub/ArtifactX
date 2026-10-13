import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, pool

from alembic import context

# ---------------------------------------------------------------------------
# Project path setup and model discovery
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import Base
import backend.models  # Registers all SQLAlchemy models on Base.metadata

# Alembic Config object
config = context.config

# Interpret config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Retrieve database URL from configuration or environment.
    
    Prefers explicit alembic configuration, then TEST_DATABASE_URL, then DATABASE_URL.
    Guarantees isolation from Neon unless explicitly authorized via ALLOW_NEON_MIGRATION=1 (R13, R17).
    """
    allow_neon = os.environ.get("ALLOW_NEON_MIGRATION") == "1"
    if allow_neon:
        from backend.app.config import Settings
        return Settings().database_url

    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and "driver://user:pass" not in ini_url and "neon.tech" not in ini_url:
        return ini_url
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url and "neon.tech" not in url:
        return url
    return "sqlite+pysqlite:///test_alembic.db"


def assert_safe_url(url: str) -> None:
    """Ensure Alembic never touches the Neon production database without explicit authorization (R17, Q-004)."""
    parsed = urlparse(url)
    if parsed.hostname and "neon.tech" in parsed.hostname.lower():
        if os.environ.get("ALLOW_NEON_MIGRATION") != "1":
            raise RuntimeError(
                "R17 Violation: Alembic migrations cannot be run directly against Neon production DB without explicit authorization (ALLOW_NEON_MIGRATION=1). "
                "Refer to Q-004 in DECISIONS_AND_BLOCKERS.md."
            )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    assert_safe_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True if "sqlite" in url else False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    assert_safe_url(url)

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        poolclass = pool.StaticPool if ":memory:" in url else pool.NullPool
    else:
        poolclass = pool.NullPool

    connectable = create_engine(
        url,
        poolclass=poolclass,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True if "sqlite" in url else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
