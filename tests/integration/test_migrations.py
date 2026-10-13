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


@pytest.mark.integration
def test_alembic_integrity_state_data_migration(tmp_path):
    """Verify that migration da9ec651c70b adds integrity_state and migrates legacy rows."""
    test_db_path = tmp_path / "test_data_migration.db"
    test_db_url = f"sqlite+pysqlite:///{test_db_path.as_posix()}"

    ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # 1. Upgrade to baseline schema
    command.upgrade(alembic_cfg, "a77eef711395")

    # 2. Insert test case and legacy row (content_bytes NULL) + modern row
    import sqlite3
    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cases (id, name) VALUES (1, 'Test Case');")
    cursor.execute(
        "INSERT INTO evidence (id, case_id, original_filename, storage_path, sha256, content_bytes) "
        "VALUES (1, 1, 'legacy.db', 'uploads/legacy.db', '0'*64, NULL);"
    )
    cursor.execute(
        "INSERT INTO evidence (id, case_id, original_filename, storage_path, sha256, content_bytes) "
        "VALUES (2, 1, 'modern.db', 'db://evidence/modern.db', '1'*64, X'1234');"
    )
    conn.commit()
    conn.close()

    # 3. Upgrade to head (applies da9ec651c70b)
    command.upgrade(alembic_cfg, "head")

    # 4. Verify data migration results
    conn = sqlite3.connect(str(test_db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT id, integrity_state FROM evidence ORDER BY id ASC;")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == (1, "LEGACY_UNVERIFIABLE")
    assert rows[1] == (2, "OK")

    # 5. Verify downgrade and re-upgrade
    command.downgrade(alembic_cfg, "a77eef711395")
    command.upgrade(alembic_cfg, "head")
