"""Unit tests for no_disk_write guard-rail (R4, A1.3, A5.4)."""

import pytest
from tools.guards import no_disk_write


@pytest.mark.unit
def test_no_disk_write_guard_passes_on_repo():
    """Verify that no_disk_write guard passes cleanly with zero violations across backend/ and forensic/."""
    result = no_disk_write.run()
    assert result == 0, "no_disk_write guard found violations in the codebase!"


@pytest.mark.unit
def test_no_disk_write_guard_detects_violations(tmp_path):
    """Verify that no_disk_write visitor detects forbidden disk-write operations."""
    sample_file = tmp_path / "bad_code.py"
    sample_file.write_text(
        """
import os
import shutil
import tempfile
import sqlite3

def write_something():
    with open("evidence.bin", "wb") as f:
        f.write(b"data")
    shutil.rmtree("/tmp/something")
    os.makedirs("/tmp/dir", exist_ok=True)
    t = tempfile.NamedTemporaryFile()
    conn = sqlite3.connect("disk.db")
""",
        encoding="utf-8",
    )

    violations = no_disk_write.scan_file(sample_file)
    violation_texts = [v[1] for v in violations]

    assert any("open() called with write mode" in t for t in violation_texts)
    assert any("shutil.rmtree()" in t for t in violation_texts)
    assert any("os.makedirs()" in t for t in violation_texts)
    assert any("tempfile.NamedTemporaryFile()" in t or "NamedTemporaryFile() usage" in t for t in violation_texts)
    assert any("sqlite3.connect to disk file" in t for t in violation_texts)


@pytest.mark.unit
def test_no_disk_write_guard_honors_suppression(tmp_path):
    """Verify that lines with guard:allow-disk-write are suppressed."""
    sample_file = tmp_path / "allowed_code.py"
    sample_file.write_text(
        """
import os

def allowed_write():
    os.makedirs("/tmp/allowed", exist_ok=True)  # guard:allow-disk-write: justified
""",
        encoding="utf-8",
    )

    violations = no_disk_write.scan_file(sample_file)
    assert len(violations) == 0
