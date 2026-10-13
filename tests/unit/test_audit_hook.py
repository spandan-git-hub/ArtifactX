"""Tests for runtime audit hook (A1.4, R4)."""

import pytest


@pytest.mark.unit
def test_audit_hook_allows_writes_in_tmp_path(tmp_path):
    """Writing inside tmp_path is allowed."""
    test_file = tmp_path / "allowed_write.txt"
    test_file.write_text("allowed data", encoding="utf-8")
    assert test_file.read_text(encoding="utf-8") == "allowed data"


@pytest.mark.unit
def test_audit_hook_blocks_unauthorized_write():
    """Writing outside allowed directories must be blocked by the audit hook."""
    target = "unauthorized_evidence_leak.bin"
    with pytest.raises(RuntimeError, match="R4 Violation: Disk write blocked by audit hook"):
        with open(target, "w", encoding="utf-8") as f:
            f.write("illegal write")
