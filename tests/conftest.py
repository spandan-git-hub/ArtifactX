"""Global pytest fixtures and test isolation configuration.

Follows master.md R4, R11, R13, and 15_TESTING_STANDARDS.md.
"""

import os
import socket
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pytest

# ---------------------------------------------------------------------------
# 1. Environment & Database Isolation (R13)
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

def _extract_env_db_url(env_path: Path) -> str | None:
    """Extract DATABASE_URL from .env file if it exists, without importing or logging."""
    if not env_path.is_file():
        return None
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL=") or line.startswith("DATABASE_URL ="):
                _, val = line.split("=", 1)
                return val.strip().strip("'\"")
    except Exception:
        pass
    return None


def assert_test_db_isolation(test_url: str, env_url: str | None) -> None:
    """Assert test database is strictly isolated from production / Neon database.
    
    Never prints or logs the URLs (R13, R14).
    """
    test_parsed = urlparse(test_url)
    if test_parsed.hostname and "neon.tech" in test_parsed.hostname.lower():
        raise RuntimeError("R13 Violation: Test database URL points to neon.tech host! Aborting.")

    if env_url:
        env_parsed = urlparse(env_url)
        if test_parsed.hostname and env_parsed.hostname:
            same_host = (test_parsed.hostname.lower() == env_parsed.hostname.lower())
            same_path = (test_parsed.path == env_parsed.path)
            # Fail if test points to the exact same host/path as .env (unless explicit localhost test)
            if same_host and same_path and env_parsed.hostname not in ("localhost", "127.0.0.1"):
                raise RuntimeError("R13 Violation: Test database URL matches production database host/database in .env! Aborting.")


# Read TEST_DATABASE_URL or default to in-memory SQLite
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
PROD_ENV_DB_URL = _extract_env_db_url(ENV_PATH)

# Verify isolation immediately upon conftest load
assert_test_db_isolation(TEST_DB_URL, PROD_ENV_DB_URL)

# Force DATABASE_URL override in os.environ BEFORE importing backend.app.config
os.environ["DATABASE_URL"] = TEST_DB_URL


# ---------------------------------------------------------------------------
# 2. Runtime Audit Hook for Zero-Disk-Write Enforcement (R4, A1.4)
# ---------------------------------------------------------------------------

AUDIT_HOOK_ENABLED = False

_ALLOWED_DIRS_LOWER = [
    os.path.normpath(tempfile.gettempdir()).lower(),
    os.path.normpath(str(ROOT_DIR / "testdata")).lower(),
    os.path.normpath(str(ROOT_DIR / ".pytest_cache")).lower(),
    os.path.normpath(str(ROOT_DIR / ".git")).lower(),
    "pytest-of-",
    "__pycache__",
    ".coverage",
    "coverage",
    "temp",
    "tmp",
    os.devnull.lower(),
    "nul",
]


def _audit_hook(event: str, args: tuple) -> None:
    """Audit hook that intercepts file open events in write modes."""
    if not AUDIT_HOOK_ENABLED or event != "open":
        return

    # args: (path, mode, flags)
    if not args:
        return

    path = args[0]
    mode = args[1] if len(args) > 1 else ""
    flags = args[2] if len(args) > 2 else 0

    # Ignore file descriptors
    if isinstance(path, int):
        return

    is_write = False
    if isinstance(mode, str) and any(c in mode for c in ("w", "a", "x", "+")):
        is_write = True
    elif isinstance(flags, int):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | getattr(os, "O_APPEND", 0)
        if flags & write_flags:
            is_write = True

    if not is_write:
        return

    path_str = str(path)
    norm_path = os.path.normpath(os.path.abspath(path_str)).lower()

    # Check if normalized path is within an allowed location
    for allowed in _ALLOWED_DIRS_LOWER:
        if allowed in norm_path:
            return

    raise RuntimeError(f"R4 Violation: Disk write blocked by audit hook: {path_str}")


# Register audit hook once at module load
try:
    sys.addaudithook(_audit_hook)
except (AttributeError, RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 3. Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def enforce_database_isolation():
    """Session fixture verifying test DB isolation (R13)."""
    assert_test_db_isolation(TEST_DB_URL, PROD_ENV_DB_URL)
    yield TEST_DB_URL


@pytest.fixture(scope="session", autouse=True)
def audit_hook_enforcement():
    """Session fixture enabling the write-mode audit hook during tests (A1.4)."""
    global AUDIT_HOOK_ENABLED
    AUDIT_HOOK_ENABLED = True
    yield
    AUDIT_HOOK_ENABLED = False


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    """Block network access during tests (R13). Allow loopback only when marked with 'pg' or internal socketpair."""
    orig_connect = socket.socket.connect
    is_pg = request.node.get_closest_marker("pg") is not None
    in_socketpair = False

    orig_socketpair = getattr(socket, "socketpair", None)
    if orig_socketpair:
        def guarded_socketpair(*args, **kwargs):
            nonlocal in_socketpair
            prev = in_socketpair
            in_socketpair = True
            try:
                return orig_socketpair(*args, **kwargs)
            finally:
                in_socketpair = prev
        monkeypatch.setattr(socket, "socketpair", guarded_socketpair)

    def guarded_connect(self, address):
        if in_socketpair:
            return orig_connect(self, address)
        if is_pg and isinstance(address, tuple) and len(address) >= 1:
            host = address[0]
            if host in ("127.0.0.1", "localhost", "::1"):
                return orig_connect(self, address)
        raise RuntimeError(
            f"Network access is blocked in tests (R13). Target: {address!r}, pg_marker={is_pg}"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture
def fixed_now():
    """Return a fixed UTC datetime for deterministic time testing (R11)."""
    return datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db_session():
    """Provide a database session with clean tables for tests."""
    import backend.models.models  # ensure all models are registered in Base.metadata
    from backend.app.database import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    except Exception:
        session.rollback()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

