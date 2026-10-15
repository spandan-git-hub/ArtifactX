"""
Integration tests for SQLite Forensics Toolkit on ground-truth fixtures (B8.6).

Verifies:
1. Freelist count matches PRAGMA freelist_count on DS-01 and DS-05.
2. B-tree leaf cell walker row counts match sqlite3 SELECT count(*) on all tables.
3. WAL post-view row set matches sqlite3 view with checkpointed WAL.
4. Recovery API endpoints via FastAPI TestClient.
"""

from pathlib import Path
import shutil
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.models.models import Case, Evidence
from forensic.common.sqlite_open import open_sqlite_ro
from forensic.sqlite.btree import (
    iter_btree_leaf_cells,
    schema_from_sqlite_master,
)
from forensic.sqlite.freelist import walk_freelist
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.wal import (
    apply_wal,
    parse_wal,
)


@pytest.fixture
def client():
    return TestClient(app)


# =====================================================================
# Fixture Validation: DS-01 WhatsApp
# =====================================================================

def test_ds01_whatsapp_freelist_count_matches_pragma():
    """Verify freelist count equals PRAGMA freelist_count on DS-01-dev."""
    db_path = Path("testdata/DS-01-dev/msgstore.db")
    if not db_path.exists():
        pytest.skip("DS-01-dev fixture not found")

    db_bytes = db_path.read_bytes()
    image = SQLiteImage(db_bytes)

    # In-memory freelist traversal
    free_pages = walk_freelist(image)

    # Compare with PRAGMA freelist_count via hardened read-only in-memory connection
    conn = open_sqlite_ro(db_bytes)
    pragma_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
    conn.close()

    assert len(free_pages) == pragma_count
    assert image.freelist_count == pragma_count


def test_ds01_whatsapp_btree_walker_matches_live_row_counts():
    """Verify B-tree leaf cell walker row counts equal SELECT count(*) on all DS-01 tables."""
    db_path = Path("testdata/DS-01-dev/msgstore.db")
    if not db_path.exists():
        pytest.skip("DS-01-dev fixture not found")

    db_bytes = db_path.read_bytes()
    image = SQLiteImage(db_bytes)
    schema = schema_from_sqlite_master(image)
    assert len(schema) > 0

    conn = open_sqlite_ro(db_bytes)

    for table_name, tbl_meta in schema.items():
        if table_name.startswith("sqlite_"):
            continue

        # Walker count
        walker_cells = list(iter_btree_leaf_cells(image, tbl_meta.root_page))
        walker_rowids = [c.rowid for c in walker_cells]

        # SQLite count
        sql_rows = conn.execute(f'SELECT rowid FROM "{table_name}" ORDER BY rowid').fetchall()
        sql_rowids = [r[0] for r in sql_rows]

        assert len(walker_cells) == len(sql_rows), f"Row count mismatch on table {table_name}"
        assert walker_rowids == sql_rowids, f"Row ID mismatch on table {table_name}"

    conn.close()


def test_ds01_whatsapp_wal_post_view_matches_sqlite3(tmp_path):
    """Verify post-WAL view row set equals sqlite3 view of main + WAL."""
    db_path = Path("testdata/DS-01-dev/msgstore.db")
    wal_path = Path("testdata/DS-01-dev/msgstore.db-wal")
    if not db_path.exists() or not wal_path.exists():
        pytest.skip("DS-01-dev main or WAL fixture not found")

    main_bytes = db_path.read_bytes()
    wal_bytes = wal_path.read_bytes()

    # Build post-WAL view purely in-memory
    image = SQLiteImage(main_bytes)
    wal = parse_wal(wal_bytes, page_size_hint=image.page_size)
    post_view_bytes = apply_wal(image, wal)

    # Open post-WAL view in memory
    conn_mem = open_sqlite_ro(post_view_bytes)

    # Open in tmp_path via sqlite3 for reference
    tmp_db = tmp_path / "msgstore.db"
    tmp_wal = tmp_path / "msgstore.db-wal"
    shutil.copyfile(db_path, tmp_db)
    shutil.copyfile(wal_path, tmp_wal)
    conn_file = sqlite3.connect(str(tmp_db))

    # Compare row counts across all tables
    tables = [r[0] for r in conn_file.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    assert len(tables) > 0

    for tbl in tables:
        file_count = conn_file.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
        mem_count = conn_mem.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
        assert mem_count == file_count, f"Post-WAL row count mismatch on table {tbl}"

        file_rowids = [r[0] for r in conn_file.execute(f'SELECT rowid FROM "{tbl}" ORDER BY rowid').fetchall()]
        mem_rowids = [r[0] for r in conn_mem.execute(f'SELECT rowid FROM "{tbl}" ORDER BY rowid').fetchall()]
        assert mem_rowids == file_rowids, f"Post-WAL rowid mismatch on table {tbl}"

    conn_file.close()
    conn_mem.close()


# =====================================================================
# Fixture Validation: DS-05 Telegram
# =====================================================================

def test_ds05_telegram_freelist_count_matches_pragma():
    """Verify freelist count equals PRAGMA freelist_count on DS-05-dev."""
    db_path = Path("testdata/DS-05-dev/cache4.db")
    if not db_path.exists():
        pytest.skip("DS-05-dev fixture not found")

    db_bytes = db_path.read_bytes()
    image = SQLiteImage(db_bytes)
    free_pages = walk_freelist(image)

    conn = open_sqlite_ro(db_bytes)
    pragma_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
    conn.close()

    assert len(free_pages) == pragma_count
    assert image.freelist_count == pragma_count


def test_ds05_telegram_btree_walker_matches_live_row_counts():
    """Verify B-tree leaf cell walker row counts equal SELECT count(*) on all DS-05 tables."""
    db_path = Path("testdata/DS-05-dev/cache4.db")
    if not db_path.exists():
        pytest.skip("DS-05-dev fixture not found")

    db_bytes = db_path.read_bytes()
    image = SQLiteImage(db_bytes)
    schema = schema_from_sqlite_master(image)
    assert len(schema) > 0

    conn = open_sqlite_ro(db_bytes)

    for table_name, tbl_meta in schema.items():
        if table_name.startswith("sqlite_"):
            continue

        walker_cells = list(iter_btree_leaf_cells(image, tbl_meta.root_page))
        walker_rowids = [c.rowid for c in walker_cells]

        sql_rows = conn.execute(f'SELECT rowid FROM "{table_name}" ORDER BY rowid').fetchall()
        sql_rowids = [r[0] for r in sql_rows]

        assert len(walker_cells) == len(sql_rows), f"Row count mismatch on table {table_name}"
        assert walker_rowids == sql_rowids, f"Row ID mismatch on table {table_name}"

    conn.close()


def test_ds05_telegram_wal_post_view_matches_sqlite3(tmp_path):
    """Verify Telegram post-WAL view row set equals sqlite3 view of main + WAL."""
    db_path = Path("testdata/DS-05-holdout/cache4.db")
    wal_path = Path("testdata/DS-05-holdout/cache4.db-wal")
    if not db_path.exists() or not wal_path.exists() or wal_path.stat().st_size < 32:
        pytest.skip("DS-05-holdout main or WAL fixture not found")

    main_bytes = db_path.read_bytes()
    wal_bytes = wal_path.read_bytes()

    image = SQLiteImage(main_bytes)
    wal = parse_wal(wal_bytes, page_size_hint=image.page_size)
    post_view_bytes = apply_wal(image, wal)

    conn_mem = open_sqlite_ro(post_view_bytes)

    tmp_db = tmp_path / "cache4.db"
    tmp_wal = tmp_path / "cache4.db-wal"
    shutil.copyfile(db_path, tmp_db)
    shutil.copyfile(wal_path, tmp_wal)
    conn_file = sqlite3.connect(str(tmp_db))

    tables = [r[0] for r in conn_file.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    assert len(tables) > 0

    for tbl in tables:
        file_count = conn_file.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
        mem_count = conn_mem.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
        assert mem_count == file_count, f"Telegram post-WAL row count mismatch on table {tbl}"

        file_rowids = [r[0] for r in conn_file.execute(f'SELECT rowid FROM "{tbl}" ORDER BY rowid').fetchall()]
        mem_rowids = [r[0] for r in conn_mem.execute(f'SELECT rowid FROM "{tbl}" ORDER BY rowid').fetchall()]
        assert mem_rowids == file_rowids, f"Telegram post-WAL rowid mismatch on table {tbl}"

    conn_file.close()
    conn_mem.close()


# =====================================================================
# Recovery API & Service Integration Tests (B8.5)
# =====================================================================

def test_recovery_api_run_and_inspect_endpoints(client, db_session):
    """Test physical recovery API endpoints: run, list runs, and list findings."""
    # Create test case
    case = Case(name="SQLite Recovery Test Case")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Ingest DS-01 msgstore.db as evidence
    db_path = Path("testdata/DS-01-dev/msgstore.db")
    if not db_path.exists():
        pytest.skip("DS-01-dev fixture not found")

    import hashlib
    content = db_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    ev = Evidence(
        case_id=case.id,
        original_filename="msgstore.db",
        storage_path="testdata/DS-01-dev/msgstore.db",
        sha256=sha256,
        content_bytes=content,
        integrity_state="OK",
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    # Trigger recovery run via API
    resp = client.post(
        f"/api/cases/{case.id}/recovery/run",
        json={"evidence_id": ev.id, "source_app_hint": "whatsapp"},
    )
    assert resp.status_code == 200, resp.text
    run_data = resp.json()
    assert run_data["status"] == "SUCCEEDED"
    assert run_data["case_id"] == case.id

    # List runs
    runs_resp = client.get(f"/api/cases/{case.id}/recovery/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) >= 1
    assert runs[0]["id"] == run_data["id"]

    # List findings
    findings_resp = client.get(f"/api/cases/{case.id}/recovery/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert isinstance(findings, list)

    # Check finding detail if any found
    if findings:
        f_id = findings[0]["id"]
        detail_resp = client.get(f"/api/cases/{case.id}/recovery/findings/{f_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == f_id
