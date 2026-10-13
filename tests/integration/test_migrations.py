"""Integration tests for Alembic migrations (A1.2)."""

import pytest
from pathlib import Path
from alembic.config import Config
from alembic import command


@pytest.mark.integration
def test_alembic_upgrade_head_on_test_db(tmp_path):
    """Verify that alembic upgrade head runs cleanly on an empty database."""
    test_db_path = tmp_path / "test_migration.db"
    test_db_url = f"sqlite+pysqlite:///{test_db_path.as_posix()}"

    ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Run upgrade head
    command.upgrade(alembic_cfg, "head")

    # Verify database file was created and contains tables
    assert test_db_path.exists()
    import sqlite3
    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "alembic_version" in tables
    assert "cases" in tables
    assert "evidence" in tables
    assert "wa_messages" in tables
    assert "tg_messages" in tables
