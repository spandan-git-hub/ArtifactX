"""Unit tests for forensic format detection engine (B5.4, spec 03_INGEST_INTEGRITY_AUDIT.md)."""

from pathlib import Path
import pytest

from forensic.detectors.format_detector import detect_format, calculate_entropy


def test_detect_empty_file():
    det = detect_format(b"", "empty.db")
    assert det.format == "EMPTY_FILE"
    assert det.confidence_basis == "empty_buffer"

    det_crypt = detect_format(b"", "empty.crypt15")
    assert det_crypt.format == "EMPTY_FILE"
    assert len(det_crypt.conflicts) > 0


def test_detect_sqlite_plain_and_wal():
    # Generic SQLite
    header = b"SQLite format 3\x00" + b"\x00" * 84
    det = detect_format(header, "test.db")
    assert det.format == "SQLITE_PLAIN"

    # WAL header
    wal_header = b"\x37\x7f\x06\x83" + b"\x00" * 28
    det_wal = detect_format(wal_header, "msgstore.db-wal")
    assert det_wal.format == "SQLITE_WAL"


def test_detect_media_containers():
    assert detect_format(b"\xff\xd8\xff\xe0", "photo.jpg").format == "IMAGE_JPEG"
    assert detect_format(b"\x89PNG\r\n\x1a\n", "photo.png").format == "IMAGE_PNG"
    assert detect_format(b"GIF89a\x00\x00", "anim.gif").format == "IMAGE_GIF"
    assert detect_format(b"PK\x03\x04\x14\x00", "archive.zip").format == "ZIP"
    mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16
    assert detect_format(mp4_bytes, "video.mp4").format == "VIDEO_MP4"


def test_detect_positives_from_fixtures():
    # DS-01 plaintext WhatsApp
    ds01_path = Path("testdata/DS-01-dev/msgstore.db")
    if ds01_path.exists():
        data = ds01_path.read_bytes()
        det = detect_format(data, "msgstore.db")
        assert det.format == "WHATSAPP_MSGSTORE"
        assert det.confidence_basis == "sqlite_table_fingerprint"

    # DS-02 Crypt14
    ds02_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    if ds02_path.exists():
        data = ds02_path.read_bytes()
        det = detect_format(data, "msgstore.db.crypt14")
        assert det.format == "WHATSAPP_CRYPT14"
        assert det.confidence_basis == "protobuf_backup_prefix"

    # DS-03 Crypt15
    ds03_path = Path("testdata/DS-03-dev/msgstore.db.crypt15")
    if ds03_path.exists():
        data = ds03_path.read_bytes()
        det = detect_format(data, "msgstore.db.crypt15")
        assert det.format == "WHATSAPP_CRYPT15"
        assert det.confidence_basis == "protobuf_backup_prefix"

    # DS-05 Telegram cache4.db
    ds05_path = Path("testdata/DS-05-dev/cache4.db")
    if ds05_path.exists():
        data = ds05_path.read_bytes()
        det = detect_format(data, "cache4.db")
        assert det.format == "TELEGRAM_CACHE4"
        assert det.confidence_basis == "sqlite_table_fingerprint"


def test_detect_ds04_negatives_and_extension_lies():
    ds04_dir = Path("testdata/DS-04-dev")
    if not ds04_dir.exists():
        pytest.skip("DS-04 fixture directory not found")

    # 1. Plaintext masquerading as .crypt15
    plain_masq = (ds04_dir / "plaintext_sqlite.crypt15").read_bytes()
    det = detect_format(plain_masq, "plaintext_sqlite.crypt15")
    assert det.format == "WHATSAPP_MSGSTORE"
    assert any("unencrypted SQLite" in c for c in det.conflicts)

    # 2. Empty file named .crypt15
    empty_bytes = (ds04_dir / "empty.crypt15").read_bytes()
    det_empty = detect_format(empty_bytes, "empty.crypt15")
    assert det_empty.format == "EMPTY_FILE"
    assert any("empty" in c for c in det_empty.conflicts)

    # 3. 1 MiB Random file named .crypt15
    rand_bytes = (ds04_dir / "random_1mb.crypt15").read_bytes()
    det_rand = detect_format(rand_bytes, "random_1mb.crypt15")
    assert det_rand.format == "UNKNOWN_ENCRYPTED_KEY_REQUIRED"
    assert any("does not match WhatsApp" in c for c in det_rand.conflicts)

    # 4. Truncated header (12 bytes)
    trunc_hdr = (ds04_dir / "truncated_header.crypt15").read_bytes()
    det_trunc_hdr = detect_format(trunc_hdr, "truncated_header.crypt15")
    assert len(det_trunc_hdr.conflicts) > 0
    assert det_trunc_hdr.format in {"UNKNOWN", "UNKNOWN_ENCRYPTED_KEY_REQUIRED"}

    # 5. Truncated body (has valid crypt15 header prefix)
    trunc_body = (ds04_dir / "truncated_body.crypt15").read_bytes()
    det_trunc_body = detect_format(trunc_body, "truncated_body.crypt15")
    assert det_trunc_body.format == "WHATSAPP_CRYPT15"
    assert det_trunc_body.confidence_basis == "protobuf_backup_prefix"

    # 6. Truncated trailer (missing 16-byte MD5)
    trunc_trailer = (ds04_dir / "truncated_trailer.crypt15").read_bytes()
    det_trunc_trailer = detect_format(trunc_trailer, "truncated_trailer.crypt15")
    assert det_trunc_trailer.format == "WHATSAPP_CRYPT15"
    assert any("trailer" in c.lower() or "truncated" in c.lower() for c in det_trunc_trailer.conflicts)

    # 7. Bit-flipped valid crypt15
    bit_flipped = (ds04_dir / "bit_flipped.crypt15").read_bytes()
    det_flipped = detect_format(bit_flipped, "bit_flipped.crypt15")
    assert det_flipped.format == "WHATSAPP_CRYPT15"
