"""
Unit tests for MTProto TL Reader and constructor deserialization (B9.2).
"""

import struct
import pytest
from datetime import datetime, timezone
from telethon.tl import types as telethon_types

from forensic.telegram.tl.reader import (
    TLBoundsError,
    TLConstructorNotFoundError,
    TLError,
    TLReader,
    TLRecursionLimitError,
)
from forensic.telegram.tl.registry import (
    SUPPORTED_REGISTRY,
    deserialize_tl_blob,
)
from forensic.telegram.tl.types import (
    TgChat,
    TgMediaDocument,
    TgMediaGeo,
    TgMediaPhoto,
    TgMessage,
    TgPeer,
    TgUser,
)


def test_tl_reader_primitives():
    """Verify numeric primitives: int32, int64, double, date."""
    # Pack int32, int64, double, date
    buf = struct.pack("<iqdi", -42, 9876543210123, 3.141592653589793, 1726000000)
    reader = TLReader(buf)
    assert reader.read_int() == -42
    assert reader.read_long() == 9876543210123
    assert pytest.approx(reader.read_double(), rel=1e-9) == 3.141592653589793
    assert reader.read_date() == 1726000000
    assert reader.remaining() == 0


@pytest.mark.parametrize("length", [0, 1, 2, 3, 4, 10, 253, 254, 255, 300])
def test_tl_reader_bytes_padding_edge_cases(length: int):
    """Verify string/bytes length prefix and 4-byte padding alignment for lengths < 254 and >= 254."""
    data = b"X" * length
    # Encode per MTProto TL specification
    if length < 254:
        encoded = bytes([length]) + data
        padding = (length + 1) % 4
        if padding > 0:
            encoded += b"\x00" * (4 - padding)
    else:
        len_bytes = bytes([254, length & 0xFF, (length >> 8) & 0xFF, (length >> 16) & 0xFF])
        encoded = len_bytes + data
        padding = length % 4
        if padding > 0:
            encoded += b"\x00" * (4 - padding)

    assert len(encoded) % 4 == 0, "Encoded bytes must be 4-byte aligned"

    reader = TLReader(encoded)
    decoded = reader.read_bytes()
    assert decoded == data
    assert reader.remaining() == 0


def test_tl_reader_bounds_checks():
    """Verify safety bounds on EOF, negative offsets, and truncated payloads (R12)."""
    # Truncated int
    with pytest.raises(TLBoundsError):
        TLReader(b"\x01\x02").read_int()

    # Truncated long
    with pytest.raises(TLBoundsError):
        TLReader(b"\x01" * 7).read_long()

    # Truncated length prefix >= 254
    with pytest.raises(TLBoundsError):
        TLReader(b"\xfe\x01").read_bytes()

    # Claimed length larger than buffer
    bad_bytes = bytes([100]) + b"short"
    with pytest.raises(TLBoundsError):
        TLReader(bad_bytes).read_bytes()

    # Negative seek
    with pytest.raises(TLBoundsError):
        TLReader(b"1234").seek(-1)


def test_tl_reader_vector_bounds():
    """Verify vector bounds check against negative and hostile oversized counts (R12)."""
    # Negative vector count
    neg_vec = struct.pack("<Ii", 0x1CB5C415, -5)
    with pytest.raises(TLBoundsError):
        TLReader(neg_vec).read_object()

    # Excessively large vector count
    big_vec = struct.pack("<Ii", 0x1CB5C415, 200000)
    with pytest.raises(TLBoundsError):
        TLReader(big_vec).read_object()


def test_tl_reader_unknown_constructor():
    """Verify unknown constructor ID triggers TLConstructorNotFoundError (triggers UNPARSED_BLOB)."""
    buf = struct.pack("<I", 0xDEADBEEF) + (b"\xaa" * 16)
    with pytest.raises(TLConstructorNotFoundError) as exc_info:
        deserialize_tl_blob(buf)
    assert exc_info.value.constructor_id == 0xDEADBEEF


def test_roundtrip_telethon_user():
    """Verify round-trip parsing of authentic Telethon-serialized User object."""
    tl_u = telethon_types.User(
        id=1002,
        is_self=False,
        contact=True,
        first_name="Priya",
        last_name="Sharma",
        username="priya_s",
        phone="919876550002",
    )
    raw = bytes(tl_u)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgUser)
    assert parsed.id == 1002
    assert parsed.first_name == "Priya"
    assert parsed.last_name == "Sharma"
    assert parsed.username == "priya_s"
    assert parsed.phone == "919876550002"
    assert parsed.contact is True
    assert parsed.is_self is False
    assert parsed.trailing_bytes is None


def test_roundtrip_telethon_chat():
    """Verify round-trip parsing of authentic Telethon-serialized Chat object."""
    dt = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    tl_c = telethon_types.Chat(
        id=2001,
        title="ArtifactX TG Taskforce",
        photo=telethon_types.ChatPhotoEmpty(),
        participants_count=4,
        date=dt,
        version=1,
    )
    raw = bytes(tl_c)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgChat)
    assert parsed.id == 2001
    assert parsed.title == "ArtifactX TG Taskforce"
    assert parsed.participants_count == 4
    assert parsed.date == int(dt.timestamp())


def test_roundtrip_telethon_message_text_and_entities():
    """Verify round-trip parsing of Message with text and formatted entities."""
    dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    tl_msg = telethon_types.Message(
        id=42,
        peer_id=telethon_types.PeerUser(user_id=1003),
        from_id=telethon_types.PeerUser(user_id=1001),
        date=dt,
        message="Important transaction: https://artifactx.org check it!",
        out=True,
        entities=[
            telethon_types.MessageEntityBold(offset=0, length=9),
            telethon_types.MessageEntityUrl(offset=23, length=21),
        ],
    )
    raw = bytes(tl_msg)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgMessage)
    assert parsed.id == 42
    assert parsed.peer == TgPeer("user", 1003)
    assert parsed.from_peer == TgPeer("user", 1001)
    assert parsed.out is True
    assert parsed.message == "Important transaction: https://artifactx.org check it!"
    assert parsed.entities is not None
    assert len(parsed.entities) == 2
    assert parsed.entities[0].entity_type == "bold"
    assert parsed.entities[0].offset == 0
    assert parsed.entities[0].length == 9
    assert parsed.entities[1].entity_type == "url"
    assert parsed.entities[1].offset == 23


def test_roundtrip_telethon_message_media_photo():
    """Verify round-trip parsing of Message with Photo attachment."""
    dt = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    photo = telethon_types.Photo(
        id=99001,
        access_hash=12345678,
        file_reference=b"sample_ref",
        date=dt,
        sizes=[telethon_types.PhotoSize(type="m", w=640, h=480, size=24500)],
        dc_id=2,
    )
    tl_msg = telethon_types.Message(
        id=43,
        peer_id=telethon_types.PeerUser(user_id=1002),
        date=dt,
        message="Look at this evidence photo",
        out=False,
        media=telethon_types.MessageMediaPhoto(photo=photo),
    )
    raw = bytes(tl_msg)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgMessage)
    assert parsed.id == 43
    assert isinstance(parsed.media, TgMediaPhoto)
    assert parsed.media.photo_id == 99001
    assert parsed.media.width == 640
    assert parsed.media.height == 480
    assert parsed.media.file_size == 24500


def test_roundtrip_telethon_message_media_geo():
    """Verify round-trip parsing of Message with GeoPoint."""
    dt = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    geo = telethon_types.GeoPoint(lat=18.922850, long=72.835250, access_hash=0)
    tl_msg = telethon_types.Message(
        id=44,
        peer_id=telethon_types.PeerChat(chat_id=2001),
        date=dt,
        message="Rendezvous coordinates",
        out=True,
        media=telethon_types.MessageMediaGeo(geo=geo),
    )
    raw = bytes(tl_msg)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgMessage)
    assert isinstance(parsed.media, TgMediaGeo)
    assert pytest.approx(parsed.media.latitude, rel=1e-5) == 18.922850
    assert pytest.approx(parsed.media.longitude, rel=1e-5) == 72.835250


def test_roundtrip_telethon_message_media_document_audio():
    """Verify round-trip parsing of Message with audio voice Document."""
    dt = datetime(2026, 9, 1, 13, 0, 0, tzinfo=timezone.utc)
    doc = telethon_types.Document(
        id=88001,
        access_hash=87654321,
        file_reference=b"voice_ref",
        date=dt,
        mime_type="audio/ogg",
        size=15400,
        dc_id=2,
        attributes=[telethon_types.DocumentAttributeAudio(voice=True, duration=35)],
    )
    tl_msg = telethon_types.Message(
        id=45,
        peer_id=telethon_types.PeerUser(user_id=1004),
        date=dt,
        message="Voice memo",
        out=True,
        media=telethon_types.MessageMediaDocument(document=doc),
    )
    raw = bytes(tl_msg)
    parsed = deserialize_tl_blob(raw)

    assert isinstance(parsed, TgMessage)
    assert isinstance(parsed.media, TgMediaDocument)
    assert parsed.media.doc_id == 88001
    assert parsed.media.mime_type == "audio/ogg"
    assert parsed.media.voice is True
    assert parsed.media.duration == 35


def test_trailing_bytes_captured_cleanly():
    """Verify valid TL object followed by extra bookkeeping bytes captures trailing_bytes without error (B9.2)."""
    tl_u = telethon_types.User(
        id=1005,
        first_name="Vikram",
        last_name="Singhania",
        username="vikram_s",
    )
    extra_bytes = b"\x00\x00\x00\x01\xaa\xbb\xcc\xdd"
    raw_with_trailing = bytes(tl_u) + extra_bytes

    parsed = deserialize_tl_blob(raw_with_trailing)
    assert isinstance(parsed, TgUser)
    assert parsed.id == 1005
    assert parsed.trailing_bytes == extra_bytes
