"""Unit tests for ZIP safety limits and Zip Slip prevention (B5.1, R12)."""

import io
import zipfile
import pytest

from backend.utils.zip_safety import (
    ZipLimitExceeded,
    extract_zip_safe_in_memory,
    normalize_zip_member_path,
)


def _build_zip(members: dict[str, bytes], compression=zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_safe_zip_extraction():
    data = _build_zip({
        "folder/file1.txt": b"Hello world",
        "file2.json": b'{"a": 1}',
    })
    extracted = extract_zip_safe_in_memory(data)
    assert len(extracted) == 2
    paths = {m.normalized_path for m in extracted}
    assert paths == {"folder/file1.txt", "file2.json"}
    for m in extracted:
        assert m.sha256 is not None
        assert m.sha512 is not None


def test_zip_slip_traversal_rejected():
    with pytest.raises(ZipLimitExceeded, match="traversal"):
        normalize_zip_member_path("folder/../../etc/passwd")

    with pytest.raises(ZipLimitExceeded, match="traversal"):
        data = _build_zip({"../evil.sh": b"rm -rf /"})
        extract_zip_safe_in_memory(data)


def test_zip_drive_letter_rejected():
    with pytest.raises(ZipLimitExceeded, match="drive letter"):
        normalize_zip_member_path("C:/Windows/System32/cmd.exe")


def test_zip_absolute_path_rejected():
    with pytest.raises(ZipLimitExceeded, match="absolute path"):
        normalize_zip_member_path("/var/log/syslog")


def test_zip_nul_byte_rejected():
    with pytest.raises(ZipLimitExceeded, match="NUL"):
        normalize_zip_member_path("file\x00.txt")


def test_zip_member_count_limit():
    members = {f"file_{i}.txt": b"x" for i in range(15)}
    data = _build_zip(members)
    with pytest.raises(ZipLimitExceeded, match="member count"):
        extract_zip_safe_in_memory(data, max_members=10)


def test_zip_bomb_expansion_factor_rejected():
    # Large zeros compressible to small zip
    big_data = b"\x00" * 200_000
    zip_bytes = _build_zip({"bomb.bin": big_data}, compression=zipfile.ZIP_DEFLATED)
    # High compression ratio
    with pytest.raises(ZipLimitExceeded, match="compression ratio|expansion|ceiling"):
        extract_zip_safe_in_memory(
            zip_bytes,
            max_member_ratio=50,
            max_uncompressed_factor=10,
        )


def test_nested_zip_depth_limit():
    inner_zip = _build_zip({"inner.txt": b"innermost content"})
    mid_zip = _build_zip({"nested.zip": inner_zip})
    outer_zip = _build_zip({"mid.zip": mid_zip})

    extracted = extract_zip_safe_in_memory(outer_zip, max_depth=2)
    # Should extract up to depth 2, not infinite recursion
    assert any("mid.zip" in m.normalized_path for m in extracted)
