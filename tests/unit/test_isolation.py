"""Tests for database isolation and network blocking (R13)."""

import socket
import pytest
from tests.conftest import assert_test_db_isolation


@pytest.mark.unit
def test_network_blocked():
    """Socket connect attempts must raise RuntimeError (R13)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="Network access is blocked in tests"):
        s.connect(("8.8.8.8", 53))


@pytest.mark.unit
def test_db_isolation_assertion_blocks_neon():
    """assert_test_db_isolation must raise when given a neon.tech host."""
    with pytest.raises(RuntimeError, match="neon.tech"):
        assert_test_db_isolation(
            "postgresql://user:pass@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb",
            None,
        )


@pytest.mark.unit
def test_db_isolation_assertion_blocks_matching_prod():
    """assert_test_db_isolation must raise when test URL matches production env URL."""
    prod = "postgresql://user:pass@db.example.internal:5432/proddb"
    with pytest.raises(RuntimeError, match="matches production"):
        assert_test_db_isolation(prod, prod)


@pytest.mark.unit
def test_db_isolation_assertion_passes_for_memory_sqlite():
    """In-memory SQLite test DB passes isolation check."""
    assert_test_db_isolation(
        "sqlite+pysqlite:///:memory:",
        "postgresql://user:pass@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb",
    )


@pytest.mark.unit
def test_config_loads_test_db_url():
    """Importing backend.app.config must yield test database URL, not prod URL."""
    from backend.app.config import settings
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert "neon.tech" not in settings.database_url
